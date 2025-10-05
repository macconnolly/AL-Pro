"""Health monitoring utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..utils.metrics import MetricsRegistry
from ..utils.statistics import DailyCounters


@dataclass
class HealthSnapshot:
    score: int
    summary: Dict[str, int]


class HealthMonitor:
    """Compute health score and analytics summary."""

    def __init__(self, metrics: MetricsRegistry, counters: DailyCounters) -> None:
        self._metrics = metrics
        self._counters = counters
        self._mode = "adaptive"
        self._scene = "default"
        self._system_state = "idle"
        self._rate_window_load = 0.0

    def set_mode(self, mode: str) -> None:
        self._mode = mode

    def set_scene(self, scene: str) -> None:
        self._scene = scene

    def set_system_state(self, state: str) -> None:
        self._system_state = state

    def set_rate_load(self, load: float) -> None:
        self._rate_window_load = load

    def snapshot(self) -> HealthSnapshot:
        failures = self._metrics.as_dict()["failures"]
        penalties = failures * 10 + int(self._counters.rate_limited * 5)
        score = max(0, 100 - penalties)
        summary = {
            **self._metrics.as_dict(),
            **self._counters.as_dict(),
            "mode": self._mode,
            "scene": self._scene,
            "system_state": self._system_state,
            "rate_window_load": round(self._rate_window_load, 2),
        }
        return HealthSnapshot(score=score, summary=summary)
