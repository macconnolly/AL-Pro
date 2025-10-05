from __future__ import annotations

from datetime import datetime, timedelta

from custom_components.al_layer_manager.manual import ManualIntentManager
from custom_components.al_layer_manager.models import ManualBehaviorProfile


def test_manual_override_round_trip() -> None:
    profile = ManualBehaviorProfile(default_duration=20, min_brightness=0.1, max_brightness=0.9)
    manager = ManualIntentManager()
    now = datetime.now()
    override = manager.start_override(
        zone_id="office",
        profile=profile,
        brightness=1.2,
        kelvin=4000,
        reason="wall_switch",
        now=now,
    )
    assert override.brightness == 0.9
    assert manager.get_override("office", now + timedelta(minutes=10)) is not None
    manager.clear_override("office")
    assert manager.get_override("office", now + timedelta(minutes=10)) is None
