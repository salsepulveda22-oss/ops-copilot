"""The agent: routes a question to the right tool, then composes a grounded, cited answer.

Tools:
  - runbook search (RAG)            -> "how do I...", "what is the rollback for..."
  - dependency graph (knowledge graph) -> "what breaks if...", "what does X depend on"
  - change-risk-assessment Skill    -> "draft a change ticket for..."

Guardrails (these are the acceptance criteria in docs/requirements.md):
  - Every answer cites its sources.
  - Unknown systems and weak retrieval produce "I don't know", never a guess.
  - Change tickets are drafts only; the agent cannot submit anything.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import llm
from .graph import DependencyGraph
from .retriever import BM25Retriever, Chunk, load_chunks

ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = ROOT / "skills" / "change-risk-assessment" / "SKILL.md"

# Below this BM25 score the best runbook match is too weak to answer from. Tuned on the eval set.
MIN_RETRIEVAL_SCORE = 4.0

HOSTLIKE = re.compile(r"\b[a-z]+(?:-[a-z0-9]+)*-\d+\b")
TICKET_WORDS = ("change ticket", "draft a change", "draft change", "change request", "assess the risk", "risk of patching")
IMPACT_WORDS = ("what breaks", "impact", "affected", "downstream", "goes down", "depends on", "who uses", "what uses")
DEPS_WORDS = ("depend on", "dependencies of", "need to run", "needs to run", "upstream")


@dataclass
class Answer:
    intent: str
    text: str
    citations: list[str] = field(default_factory=list)
    refused: bool = False
    entities: list[str] = field(default_factory=list)
    impacted: list[str] = field(default_factory=list)
    risk: str | None = None
    retrieved: list[Chunk] = field(default_factory=list)


class OpsCopilot:
    def __init__(self, data_dir: Path = ROOT / "data", use_llm: bool | None = None):
        self.chunks = load_chunks(data_dir / "runbooks")
        self.retriever = BM25Retriever(self.chunks)
        self.graph = DependencyGraph(data_dir / "graph.json")
        self.use_llm = llm.available() if use_llm is None else use_llm

    # ---------- routing ----------
    def find_entities(self, question: str) -> tuple[list[str], list[str]]:
        q = question.lower()
        known = sorted((n for n in self.graph.nodes if re.search(rf"\b{re.escape(n)}\b", q)), key=len, reverse=True)
        unknown = [h for h in HOSTLIKE.findall(q) if h not in self.graph]
        return known, unknown

    def classify(self, question: str) -> str:
        q = question.lower()
        if any(w in q for w in TICKET_WORDS):
            return "change_ticket"
        if any(w in q for w in DEPS_WORDS) and not q.startswith(("what depends", "who depends")):
            return "dependencies"
        if any(w in q for w in IMPACT_WORDS):
            return "impact"
        return "runbook"

    def ask(self, question: str, window: str | None = None) -> Answer:
        intent = self.classify(question)
        known, unknown = self.find_entities(question)
        if unknown and not known:
            return Answer(intent, f"I don't know: {', '.join(unknown)} is not in the dependency graph or any runbook. "
                                  "Check the name or ask the system owner. I won't guess its dependencies.",
                          refused=True, entities=unknown)
        if intent == "change_ticket":
            return self.change_ticket(question, known, window)
        if intent in ("impact", "dependencies"):
            if not known:
                return Answer(intent, "I don't know which system you mean. Name a server or application from the CMDB.",
                              refused=True)
            return self.graph_answer(intent, known[0])
        return self.runbook_answer(question, known)

    # ---------- tools ----------
    def search(self, question: str, entities: list[str], k: int = 3) -> list[Chunk]:
        hits = self.retriever.search(question, k=10)
        wanted = _wanted_section(question)
        for h in hits:
            if any(e in h.systems or e in h.text for e in entities):
                h.score = round(h.score + 2.0, 3)  # runbook covers the system named in the question
            if wanted and h.section == wanted:
                h.score = round(h.score + 3.0, 3)  # section matches what was asked (rollback, steps...)
        hits.sort(key=lambda c: c.score, reverse=True)
        return hits[:k]

    def runbook_answer(self, question: str, entities: list[str]) -> Answer:
        hits = self.search(question, entities)
        if not hits or max(h.raw for h in hits) < MIN_RETRIEVAL_SCORE:
            return Answer("runbook", "I don't know. No runbook covers this closely enough to answer safely.",
                          refused=True, retrieved=hits, entities=entities)
        citations = [h.citation for h in hits]
        if self.use_llm:
            context = "\n\n".join(f"[{h.citation}]\n{h.title} > {h.section}\n{h.text}" for h in hits)
            text = llm.complete(
                system=("You answer infrastructure questions using ONLY the runbook excerpts provided. "
                        "Cite the bracketed source after every claim. If the excerpts do not answer the "
                        "question, reply exactly: I don't know."),
                user=f"Runbook excerpts:\n{context}\n\nQuestion: {question}")
            refused = text.strip().lower().startswith("i don't know")
            return Answer("runbook", text, citations, refused, entities, retrieved=hits)
        top = hits[0]
        text = f"From {top.title} > {top.section}:\n{top.text}\n\n[source: {top.citation}]"
        return Answer("runbook", text, citations, False, entities, retrieved=hits)

    def graph_answer(self, intent: str, entity: str) -> Answer:
        if intent == "impact":
            nodes = sorted(self.graph.impacted_by(entity), key=lambda n: (self.graph.tier(n), n))
            head = f"If {entity} goes down, these are impacted:"
        else:
            nodes = sorted(self.graph.dependencies_of(entity), key=lambda n: (self.graph.tier(n), n))
            head = f"{entity} depends on:"
        if not nodes:
            body = "- nothing in the dependency graph"
        else:
            body = "\n".join(f"- {n} (Tier {self.graph.tier(n)}, {self.graph.type(n).replace('_', ' ')})" for n in nodes)
        return Answer(intent, f"{head}\n{body}\n\n[source: data/graph.json (CMDB extract)]",
                      ["data/graph.json"], False, [entity], impacted=nodes)

    def change_ticket(self, question: str, entities: list[str], window: str | None) -> Answer:
        if not entities:
            return Answer("change_ticket", "I don't know which system this change is for. Name a server or "
                                           "application from the CMDB.", refused=True)
        target = entities[0]
        impacted = sorted(self.graph.impacted_by(target), key=lambda n: (self.graph.tier(n), n))
        related = {target, *impacted, *self.graph.dependencies_of(target)}
        runbooks = {c.source for c in self.chunks if target in c.systems}
        if not runbooks:  # an application: use the runbooks for the servers it runs on
            runbooks = {c.source for c in self.chunks if set(c.systems) & self.graph.dependencies_of(target)}
        prechecks = [c for c in self.chunks if c.source in runbooks and c.section == "Pre-checks"]
        rollbacks = [c for c in self.chunks if c.source in runbooks and c.section == "Rollback"]

        # Blackout rules are written in runbooks as "between HH:MM and HH:MM CT".
        window = window or _find_time(question)
        blackout = None
        full_text = {}
        for c in self.chunks:
            full_text[c.source] = full_text.get(c.source, "") + f" {c.title.lower()} {' '.join(c.systems)} {c.text}"
        for c in self.chunks:
            m = re.search(r"between (\d\d:\d\d) and (\d\d:\d\d) CT", c.text)
            # The rule applies if its runbook mentions the target or anything it touches.
            if m and any(n in full_text[c.source] or n.replace("-", " ") in full_text[c.source] for n in related):
                if window and _in_range(window, m.group(1), m.group(2)):
                    blackout = (f"CONFLICT: window {window} falls in the {m.group(1)}-{m.group(2)} CT blackout",
                                c.citation)

        # Apply the Skill's risk rules (skills/change-risk-assessment/SKILL.md).
        reasons = []
        biz = [n for n in impacted if self.graph.type(n) == "business_service"]
        if any(self.graph.tier(n) == 1 for n in biz):
            reasons.append("Tier 1 business service impacted: " + ", ".join(n for n in biz if self.graph.tier(n) == 1))
        if blackout:
            reasons.append("Planned window conflicts with a blackout rule")
        if not rollbacks:
            reasons.append("No documented rollback")
        if reasons:
            risk = "High"
        elif impacted and min(self.graph.tier(n) for n in impacted) == 2:
            risk, reasons = "Medium", ["Highest impacted tier is 2"]
        else:
            risk, reasons = "Low", ["Only Tier 3 systems impacted"]

        citations = [c.citation for c in prechecks + rollbacks] + ["data/graph.json"]
        if blackout:
            citations.append(blackout[1])
        facts = {
            "target": target, "window": window or "not provided", "risk": risk, "why": reasons,
            "impacted": [f"{n} (Tier {self.graph.tier(n)}, {self.graph.type(n).replace('_', ' ')})" for n in impacted],
            "prechecks": [f"{c.text} [source: {c.citation}]" for c in prechecks],
            "rollback": [f"{c.text} [source: {c.citation}]" for c in rollbacks],
            "blackout": f"{blackout[0]} [source: {blackout[1]}]" if blackout else "OK",
        }
        if self.use_llm:
            text = llm.complete(system=SKILL_PATH.read_text(encoding="utf-8"),
                                user=f"Draft the change ticket from these facts only:\n{facts}")
        else:
            text = _render_ticket(facts)
        return Answer("change_ticket", text, citations, False, [target], impacted=impacted, risk=risk)


SECTION_CUES = [  # checked in order; first match wins
    ("Rollback", ("rollback", "roll back", "revert", "undo", "back out")),
    ("Pre-checks", ("before", "pre-check", "precheck", "prerequisite")),
    ("Validation", ("verify", "validate", "validation", "confirm it worked", "how do i know")),
    ("Expected duration", ("how long", "duration", "downtime")),
    ("Procedure", ("how do i", "how to", "steps", "procedure")),
]


def _wanted_section(question: str) -> str | None:
    q = question.lower()
    for section, cues in SECTION_CUES:
        if any(c in q for c in cues):
            return section
    return None


def _find_time(text: str) -> str | None:
    m = re.search(r"\b(\d{1,2}):(\d\d)\b", text)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


def _in_range(t: str, start: str, end: str) -> bool:
    return start <= t[-5:] < end


def _render_ticket(f: dict) -> str:
    lines = ["CHANGE TICKET (DRAFT - requires human approval)",
             f"Target: {f['target']}", f"Planned window: {f['window']}", f"Risk rating: {f['risk']}",
             "Why: " + "; ".join(f["why"]), "", "Impacted services:"]
    lines += [f"- {i}" for i in f["impacted"]] or ["- none"]
    lines += ["", "Pre-checks:"] + ([f"- {p}" for p in f["prechecks"]] or ["- none documented"])
    lines += ["", "Rollback plan:"] + ([f"- {r}" for r in f["rollback"]] or ["- NONE DOCUMENTED"])
    lines += ["", f"Blackout check: {f['blackout']}"]
    return "\n".join(lines)
