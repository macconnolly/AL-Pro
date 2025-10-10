from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from custom_components.al_layer_manager.manual import ManualIntentManager
from custom_components.al_layer_manager.models import ManualBehaviorProfile


@pytest.fixture
def manual_manager() -> ManualIntentManager:
    return ManualIntentManager()


def test_manual_override_lifecycle(manual_manager: ManualIntentManager) -> None:
    profile = ManualBehaviorProfile(default_duration=20, min_brightness=0.1, max_brightness=0.9)
    now = datetime.fromisoformat("2024-02-01T06:00:00")
    state = manual_manager.start_override("office", profile, 1.2, 3200, "voice", now)
    assert 0.1 <= state.brightness <= 0.9
    assert manual_manager.metrics.overrides_started == 1

    manual_manager.extend_override("office", 10)
    extended = manual_manager.get_override("office", now + timedelta(minutes=5))
    assert extended is not None
    assert manual_manager.metrics.overrides_extended == 1

    manual_manager.clear_override("office")
    assert manual_manager.get_override("office", now) is None
    assert manual_manager.metrics.overrides_cleared == 1


def test_manual_override_expiration_and_decay(manual_manager: ManualIntentManager) -> None:
    profile = ManualBehaviorProfile(default_duration=5, decay_rate=0.2)
    now = datetime.fromisoformat("2024-02-01T06:00:00")
    manual_manager.start_override("office", profile, 0.8, 3200, "wall", now, duration=20)

    expired = manual_manager.get_override("office", now + timedelta(minutes=25))
    assert expired is None

    manual_manager.start_override("office", profile, 0.8, 3200, "wall", now, duration=30)
    decayed = manual_manager.decay_brightness("office", now + timedelta(minutes=10), 0.3)
    assert decayed is not None
    assert decayed.brightness >= 0.3

    manual_manager.metrics.overrides_cleared = 0
    manual_manager.clear_override("office")
    assert manual_manager.metrics.overrides_cleared == 1
