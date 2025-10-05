"""Analytics counters and health scoring."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass(slots=True)
class Counter:
    name: str
    value: float = 0.0

    def increment(self, amount: float = 1.0) -> None:
        self.value += amount

    def reset(self) -> None:
        self.value = 0.0


@dataclass(slots=True)
class AnalyticsSuite:
    counters: Dict[str, Counter] = field(default_factory=dict)

    def increment(self, name: str, amount: float = 1.0) -> None:
        if name not in self.counters:
            self.counters[name] = Counter(name=name)
        self.counters[name].increment(amount)

    def get(self, name: str) -> float:
        return self.counters.get(name, Counter(name=name)).value

    def snapshot(self) -> Dict[str, float]:
        return {name: counter.value for name, counter in self.counters.items()}


def compute_health_score(
    missed_syncs: int,
    stale_sensors: int,
    stuck_overrides: int,
    baseline: int = 100,
) -> int:
    penalty = missed_syncs * 5 + stale_sensors * 7 + stuck_overrides * 10
    return max(0, baseline - penalty)
