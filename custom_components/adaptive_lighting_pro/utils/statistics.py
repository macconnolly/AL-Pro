"""Statistics helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DailyCounters:
    """Track counters that reset nightly."""

    sync_requests: int = 0
    manual_detects: int = 0
    rate_limited: int = 0
    watchdog_resets: int = 0
    details: Dict[str, int] = field(default_factory=dict)

    def increment(self, name: str) -> None:
        self.details[name] = self.details.get(name, 0) + 1
        if name == "sync_requests":
            self.sync_requests += 1
        elif name == "manual_detects":
            self.manual_detects += 1
        elif name == "rate_limited":
            self.rate_limited += 1
        elif name == "watchdog_resets":
            self.watchdog_resets += 1

    def reset(self) -> None:
        self.sync_requests = 0
        self.manual_detects = 0
        self.rate_limited = 0
        self.watchdog_resets = 0
        self.details.clear()

    def as_dict(self) -> Dict[str, int]:
        return {
            "sync_requests": self.sync_requests,
            "manual_detects": self.manual_detects,
            "rate_limited": self.rate_limited,
            "watchdog_resets": self.watchdog_resets,
            **self.details,
        }
