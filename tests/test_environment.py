from __future__ import annotations

from datetime import datetime, timedelta

from custom_components.al_layer_manager.environment import EnvironmentManager, SensorReading
from custom_components.al_layer_manager.models import EnvironmentProfile


def test_environment_boost_cap() -> None:
    manager = EnvironmentManager()
    now = datetime.fromisoformat("2024-02-01T07:30:00")
    profile = EnvironmentProfile(boost_cap=0.4)
    manager.update_sensor(SensorReading(name="foggy", value=1, last_updated=now))
    manager.update_sensor(SensorReading(name="cloudy", value=1, last_updated=now))
    manager.update_sensor(SensorReading(name="sad", value=1, last_updated=now))
    state = manager.compute_state("office", profile, now)
    assert state.brightness_offset == profile.boost_cap
    assert "foggy" in state.active_profiles


def test_environment_unavailable_when_stale() -> None:
    manager = EnvironmentManager()
    now = datetime.fromisoformat("2024-02-01T10:00:00")
    manager.update_sensor(
        SensorReading(
            name="foggy",
            value=1,
            last_updated=now - timedelta(hours=1),
        )
    )
    state = manager.compute_state("office", EnvironmentProfile(), now)
    assert not state.available
