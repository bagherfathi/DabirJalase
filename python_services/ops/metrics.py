"""Simple metrics placeholders."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class Counter:
    name: str
    value: int = 0

    def inc(self, amount: int = 1) -> None:
        self.value += amount


class MetricsRegistry:
    def __init__(self) -> None:
        self.counters: Dict[str, Counter] = {}

    def counter(self, name: str) -> Counter:
        if name not in self.counters:
            self.counters[name] = Counter(name=name)
        return self.counters[name]

    def snapshot(self) -> Dict[str, int]:
        """Return the current counter values as a plain dictionary."""

        return {name: counter.value for name, counter in sorted(self.counters.items())}
