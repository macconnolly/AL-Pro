"""Nightly and startup routines."""
from __future__ import annotations

from datetime import datetime
from typing import Dict

from .analytics import AnalyticsSuite
from .manual import ManualIntentManager
from .models import ZoneModel


class MaintenanceManager:
    """Coordinates nightly cleanup and startup reconciliation."""

    def __init__(self, manual: ManualIntentManager, analytics: AnalyticsSuite) -> None:
        self.manual = manual
        self.analytics = analytics
        self.notifications: list[str] = []

    def startup(self, zones: Dict[str, ZoneModel], now: datetime) -> None:
        for zone_id in zones:
            override = self.manual.get_override(zone_id, now)
            if override:
                self.notifications.append(f"Override active for {zone_id} at startup")
        self.analytics.increment("startup_checks")

    def nightly(self, now: datetime) -> None:
        for zone_id, override in list(self.manual.snapshot().items()):
            if override.expires_at < now:
                self.manual.clear_override(zone_id)
        for counter in list(self.analytics.counters.values()):
            if counter.name.startswith("sync_"):
                continue
            counter.reset()
        self.analytics.increment("nightly_run")
