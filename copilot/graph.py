"""Knowledge graph layer: which servers, apps and business services depend on what.

Loaded from a JSON extract of the CMDB. In production this would be Neo4j or Amazon
Neptune; the two questions the copilot asks of it stay the same.
"""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path


class DependencyGraph:
    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.nodes: dict[str, dict] = data["nodes"]
        self.depends_on: dict[str, set[str]] = {n: set() for n in self.nodes}
        self.dependents: dict[str, set[str]] = {n: set() for n in self.nodes}
        for src, dst in data["edges"]:
            self.depends_on[src].add(dst)
            self.dependents[dst].add(src)

    def __contains__(self, name: str) -> bool:
        return name in self.nodes

    def _walk(self, start: str, adjacency: dict[str, set[str]]) -> set[str]:
        seen: set[str] = set()
        queue = deque([start])
        while queue:
            for nxt in adjacency[queue.popleft()]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    def impacted_by(self, name: str) -> set[str]:
        """Everything that breaks (directly or transitively) if `name` goes down."""
        return self._walk(name, self.dependents)

    def dependencies_of(self, name: str) -> set[str]:
        """Everything `name` needs in order to run."""
        return self._walk(name, self.depends_on)

    def tier(self, name: str) -> int:
        return self.nodes[name]["tier"]

    def type(self, name: str) -> str:
        return self.nodes[name]["type"]
