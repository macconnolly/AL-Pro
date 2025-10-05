"""Metrics helpers for Adaptive Lighting Pro."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class ExponentialMovingAverage:
    """Maintain an exponential moving average."""

    alpha: float
    value: float | None = None

    def update(self, sample: float) -> float:
        """Update the EMA with a new sample and return the value."""
        if self.value is None:
            self.value = sample
        else:
            self.value = self.alpha * sample + (1 - self.alpha) * self.value
        return self.value

    def as_int(self) -> int:
        """Return the value rounded to integer."""
        return int(round(self.value if self.value is not None else 0))


class MetricsRegistry:
    """Registry storing metrics values."""

    def __init__(self) -> None:
        self._ema = ExponentialMovingAverage(alpha=0.4)
        self._sync_count = 0
        self._failures = 0
        self._last_duration_ms = 0

    def record_sync(self, duration_ms: int, failed: bool = False) -> None:
        """Record sync duration and failure state."""
        self._last_duration_ms = duration_ms
        self._ema.update(duration_ms)
        self._sync_count += 1
        if failed:
            self._failures += 1

    @property
    def average_duration_ms(self) -> int:
        """Return EMA average sync duration in milliseconds."""
        return self._ema.as_int()

    @property
    def last_duration_ms(self) -> int:
        return self._last_duration_ms

    def as_dict(self) -> Dict[str, int]:
        """Expose metrics as dictionary."""
        return {
            "sync_count": self._sync_count,
            "failures": self._failures,
            "avg_sync_ms": self.average_duration_ms,
            "last_sync_ms": self._last_duration_ms,
        }
