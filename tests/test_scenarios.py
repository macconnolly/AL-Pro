from datetime import datetime

import pytest

from custom_components.al_layer_manager.environment import SensorReading
from custom_components.al_layer_manager.models import ModeProfile


@pytest.mark.scenario("morning")
def test_foggy_winter_morning_should_boost_brightness(integration, sample_zone) -> None:
    now = datetime.fromisoformat("2024-02-01T06:30:00")
    integration.environment.update_sensor(SensorReading("foggy", 1, now))
    integration.environment.update_sensor(SensorReading("cloudy", 1, now))
    integration.environment.compute_state(sample_zone.zone_id, sample_zone.environment, now)
    computation, commands = integration.compute_zone(sample_zone.zone_id, now)
    assert computation.brightness > sample_zone.default_brightness + 0.2
    assert any(cmd.data["id"].endswith("environment") for cmd in commands)


@pytest.mark.scenario("evening")
def test_evening_relax_mode_respects_manual_override(integration, sample_zone) -> None:
    now = datetime.fromisoformat("2024-02-01T19:00:00")
    integration.mode.set_mode(sample_zone.zone_id, "relax", sample_zone.modes["relax"])
    integration.manual.start_override(
        zone_id=sample_zone.zone_id,
        profile=sample_zone.manual,
        brightness=0.5,
        kelvin=3200,
        reason="voice",
        now=now,
        duration=30,
    )
    computation, commands = integration.compute_zone(sample_zone.zone_id, now)
    assert computation.source.startswith("manual")
    assert any(cmd.data["id"].endswith("manual") for cmd in commands)
    assert computation.brightness >= 0.5


@pytest.mark.scenario("night")
def test_nightlight_mode_limits_brightness(integration, sample_zone) -> None:
    now = datetime.fromisoformat("2024-02-02T01:15:00")
    night_profile = ModeProfile(brightness_multiplier=0.2, kelvin_adjustment=-1000, transition_seconds=5)
    integration.apply_mode(sample_zone.zone_id, "late_night", night_profile)
    computation, commands = integration.compute_zone(sample_zone.zone_id, now)
    assert computation.brightness <= sample_zone.default_brightness * 0.3
    assert any(cmd.data["id"].endswith("mode") for cmd in commands)
    assert computation.transition == night_profile.transition_seconds
