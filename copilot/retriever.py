"""RAG retrieval layer: chunk runbooks by section and rank chunks with BM25.

Pure standard library so the POC runs anywhere. In production this module is the
seam where a vector database (pgvector, OpenSearch, Bedrock Knowledge Bases) and an
embedding model would plug in; the interface (`search(query, k) -> list[Chunk]`) stays the same.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

STOPWORDS = set(
    "a an the and or of to in on for is are was be by with at from as it this that what how do does i we "
    "if can should when which who our my you your me there their then than into before after".split()
)


# Ops vocabulary: what engineers type -> what runbooks say. Cheap stand-in for embeddings.
SYNONYMS = {
    "postgres": ["postgresql", "database"], "postgresql": ["postgres"], "db": ["database"],
    "cert": ["certificate"], "certs": ["certificate"], "tls": ["certificate"], "ssl": ["certificate", "tls"],
    "revert": ["rollback"], "undo": ["rollback"], "back out": ["rollback"],
    "settlement": ["batch"], "uat": ["test"], "reboot": ["patch", "restart"],
}


def stem(word: str) -> str:
    """Very light suffix stripping so 'refreshing' matches 'refresh' and 'brokers' matches 'broker'."""
    if "-" in word or word.isdigit():
        return word
    for suffix in ("ing", "es", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokenize(text: str, expand: bool = False) -> list[str]:
    """Lowercase, stemmed tokens. Hostnames like pg-prod-01 are kept whole AND split into parts.
    With expand=True (queries only), ops synonyms are added."""
    text = text.lower()
    tokens: list[str] = []
    for word in re.findall(r"[a-z0-9][a-z0-9\-_.]*[a-z0-9]|[a-z0-9]", text):
        if word in STOPWORDS:
            continue
        tokens.append(stem(word))
        if "-" in word:
            tokens.extend(stem(p) for p in word.split("-") if p and p not in STOPWORDS)
        if expand:
            tokens.extend(stem(s) for s in SYNONYMS.get(word, []))
    return tokens


@dataclass
class Chunk:
    source: str      # runbook file name
    title: str       # runbook title
    section: str     # section heading
    text: str        # section body
    systems: list[str]
    score: float = 0.0   # final ranking score (after agent boosts)
    raw: float = 0.0     # pure BM25 relevance, used for the 'I don't know' threshold

    @property
    def citation(self) -> str:
        return f"{self.source}#{self.section.lower().replace(' ', '-')}"


def load_chunks(runbook_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(runbook_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        title_match = re.search(r"^# (.+)$", raw, re.M)
        title = title_match.group(1).replace("Runbook: ", "") if title_match else path.stem
        systems_match = re.search(r"^Systems: (.+)$", raw, re.M)
        systems = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", systems_match.group(1)) if systems_match else []
        parts = re.split(r"^## (.+)$", raw, flags=re.M)
        # parts = [preamble, heading1, body1, heading2, body2, ...]
        for i in range(1, len(parts), 2):
            chunks.append(Chunk(path.name, title, parts[i].strip(), parts[i + 1].strip(), systems))
    return chunks


class BM25Retriever:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        # Index the title and section heading with the body so "failover rollback" finds the right section.
        self.docs = [tokenize(f"{c.title} {c.title} {c.section} {c.text}") for c in chunks]
        self.avgdl = sum(len(d) for d in self.docs) / max(len(self.docs), 1)
        df: Counter = Counter()
        for d in self.docs:
            df.update(set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tfs = [Counter(d) for d in self.docs]

    def search(self, query: str, k: int = 3) -> list[Chunk]:
        q = tokenize(query, expand=True)
        results: list[Chunk] = []
        for chunk, tf, doc in zip(self.chunks, self.tfs, self.docs):
            score = 0.0
            for term in q:
                if term not in tf:
                    continue
                f = tf[term]
                score += self.idf[term] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(doc) / self.avgdl))
            if score > 0:
                results.append(Chunk(chunk.source, chunk.title, chunk.section, chunk.text, chunk.systems,
                                     round(score, 3), round(score, 3)))
        results.sort(key=lambda c: c.score, reverse=True)
        return results[:k]
