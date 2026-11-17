"""Eval harness: score the copilot on the golden set and enforce the POC exit gates.

    python evals/run_evals.py            # prints the scorecard, writes evals/report.md
    exit code 0 = all gates pass, 1 = a gate failed (so CI blocks the release)

Runs in offline mode so results are deterministic and cost nothing. The gates are the
POC exit criteria from docs/requirements.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from copilot import OpsCopilot  # noqa: E402

GATES = {  # metric: minimum to pass the POC gate
    "Runbook source found in top 3 (recall@3)": 0.80,
    "Runbook section correct (top 1)": 0.80,
    "Dependency recall": 0.90,
    "Dependency precision": 0.90,
    "Change ticket risk rating correct": 0.80,
    "Blackout conflicts detected correctly": 1.00,
    "Refuses when it should ('I don't know')": 0.90,
    "Answers when it should (no false refusals)": 0.90,
    "Answers that carry a citation": 1.00,
}


def main() -> int:
    bot = OpsCopilot(use_llm=False)
    cases = [json.loads(line) for line in (ROOT / "evals" / "golden_set.jsonl").read_text().splitlines() if line.strip()]
    rows, counts = [], {k: [0, 0] for k in GATES}  # [passed, total]

    def score(metric: str, ok: bool | float, weight: int = 1):
        counts[metric][0] += ok if isinstance(ok, float) else int(ok)
        counts[metric][1] += weight

    for c in cases:
        a = bot.ask(c["question"])
        should_refuse = c["type"] == "refusal"
        if should_refuse:
            score("Refuses when it should ('I don't know')", a.refused)
            ok = a.refused
        else:
            score("Answers when it should (no false refusals)", not a.refused)
            score("Answers that carry a citation", bool(a.citations) and not a.refused)
            ok = not a.refused

        if c["type"] == "runbook":
            sources = [h.source for h in a.retrieved]
            hit = c["expect_source"] in sources and not a.refused
            top = bool(a.retrieved) and a.retrieved[0].source == c["expect_source"] \
                and a.retrieved[0].section == c["expect_section"] and not a.refused
            score("Runbook source found in top 3 (recall@3)", hit)
            score("Runbook section correct (top 1)", top)
            ok = ok and top
        elif c["type"] in ("impact", "dependencies"):
            got, want = set(a.impacted), set(c["expect"])
            recall = len(got & want) / len(want)
            precision = len(got & want) / len(got) if got else 0.0
            score("Dependency recall", recall)
            score("Dependency precision", precision)
            ok = ok and recall == 1.0 and precision == 1.0
        elif c["type"] == "change_ticket":
            risk_ok = a.risk == c["expect_risk"]
            blackout_ok = ("CONFLICT" in a.text) == c["expect_blackout"]
            score("Change ticket risk rating correct", risk_ok)
            score("Blackout conflicts detected correctly", blackout_ok)
            ok = ok and risk_ok and blackout_ok
        rows.append((c["id"], c["type"], c["question"], "PASS" if ok else "FAIL"))

    results = []
    for metric, minimum in GATES.items():
        passed, total = counts[metric]
        value = passed / total if total else 0.0
        results.append((metric, value, minimum, value >= minimum))
    all_pass = all(r[3] for r in results)

    lines = ["# Eval report: POC gate", "",
             f"**Gate result: {'PASS' if all_pass else 'FAIL'}** "
             f"({sum(r[3] == 'PASS' for r in rows)}/{len(rows)} cases passed, offline mode)", "",
             "| Metric | Score | POC gate | Result |", "|---|---|---|---|"]
    lines += [f"| {m} | {v:.0%} | >= {g:.0%} | {'PASS' if p else 'FAIL'} |" for m, v, g, p in results]
    lines += ["", "## Cases", "", "| ID | Type | Question | Result |", "|---|---|---|---|"]
    lines += [f"| {i} | {t} | {q} | {r} |" for i, t, q, r in rows]
    report = "\n".join(lines) + "\n"
    (ROOT / "evals" / "report.md").write_text(report)
    print(report)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
