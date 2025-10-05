"""Rate limiter for Adaptive Lighting Pro."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque


@dataclass
class RateLimitConfig:
    max_events: int
    window_sec: int


class RateLimiter:
    """Simple moving window rate limiter."""

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._events: Deque[float] = deque()

    def allow(self) -> bool:
        """Return True if event is allowed."""
        now = time.monotonic()
        window_start = now - self._config.window_sec
        while self._events and self._events[0] < window_start:
            self._events.popleft()
        if len(self._events) >= self._config.max_events:
            return False
        self._events.append(now)
        return True

    @property
    def load(self) -> float:
        """Return utilization ratio 0..1."""
        return min(1.0, len(self._events) / max(1, self._config.max_events))
