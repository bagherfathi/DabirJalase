"""Stub for metrics and health reporting."""

from typing import Dict


class Metrics:
    def __init__(self) -> None:
        self.counters: Dict[str, int] = {}

    def increment(self, name: str) -> None:
        self.counters[name] = self.counters.get(name, 0) + 1

    def snapshot(self) -> Dict[str, int]:
        return dict(self.counters)
