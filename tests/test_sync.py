from __future__ import annotations

from datetime import datetime

from custom_components.al_layer_manager import LayerManagerIntegration
from custom_components.al_layer_manager.environment import SensorReading


def test_sync_blends_manual_and_environment(sample_zone) -> None:
    integration = LayerManagerIntegration(zones={sample_zone.zone_id: sample_zone})
    now = datetime.fromisoformat("2024-02-01T06:45:00")
    integration.environment.update_sensor(SensorReading(name="foggy", value=1, last_updated=now))
    integration.environment.compute_state(sample_zone.zone_id, sample_zone.environment, now)
    integration.manual.start_override(
        zone_id=sample_zone.zone_id,
        profile=sample_zone.manual,
        brightness=0.9,
        kelvin=3500,
        reason="wall_switch",
        now=now,
    )
    computation, commands = integration.compute_zone(sample_zone.zone_id, now)
    assert computation.source.startswith("manual")
    assert computation.brightness >= 0.75
    assert computation.kelvin == 3500
    assert commands
    manual_command = [c for c in commands if c.data["id"].endswith("manual")][0]
    assert manual_command.service == "layer_manager.insert_state"
    assert manual_command.data["attributes"]["al_reason"] == "wall_switch"


def test_sync_respects_mode(sample_zone) -> None:
    integration = LayerManagerIntegration(zones={sample_zone.zone_id: sample_zone})
    now = datetime.fromisoformat("2024-02-01T20:00:00")
    integration.mode.set_mode("relax", sample_zone.modes["relax"])
    computation, commands = integration.compute_zone(sample_zone.zone_id, now)
    assert computation.brightness < sample_zone.default_brightness
    assert any(cmd.data["id"].endswith("mode") for cmd in commands)
    assert computation.transition == sample_zone.modes["relax"].transition_seconds
