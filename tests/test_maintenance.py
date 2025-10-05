from __future__ import annotations

from datetime import datetime, timedelta

from custom_components.al_layer_manager.analytics import AnalyticsSuite
from custom_components.al_layer_manager.maintenance import MaintenanceManager
from custom_components.al_layer_manager.manual import ManualIntentManager


def test_nightly_clears_expired_overrides(sample_zone) -> None:
    manual = ManualIntentManager()
    analytics = AnalyticsSuite()
    manager = MaintenanceManager(manual, analytics)
    now = datetime.fromisoformat("2024-02-01T22:00:00")
    manual.start_override(
        zone_id=sample_zone.zone_id,
        profile=sample_zone.manual,
        brightness=0.6,
        kelvin=3300,
        reason="test",
        now=now - timedelta(hours=1),
        duration=30,
    )
    manager.nightly(now)
    assert manual.get_override(sample_zone.zone_id, now) is None
    assert analytics.get("nightly_run") == 1
