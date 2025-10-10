from __future__ import annotations

from datetime import datetime

import pytest

from custom_components.al_layer_manager.bridge import LayerCommand
from custom_components.al_layer_manager.engine import LayerManagerEngine
from custom_components.al_layer_manager.environment import SensorReading
from custom_components.al_layer_manager.models import ModeProfile


@pytest.mark.asyncio
async def test_engine_dispatch_and_snapshot(sample_zone) -> None:
    commands: list[LayerCommand] = []

    async def executor(command: LayerCommand) -> None:
        commands.append(command)

    engine = LayerManagerEngine({sample_zone.zone_id: sample_zone})
    engine.set_command_executor(executor)

    now = datetime.fromisoformat("2024-02-01T06:30:00")
    engine.start_manual_override(sample_zone.zone_id, 0.7, 3300, "test", now, duration=10)
    await engine.async_dispatch_zone(sample_zone.zone_id, now)

    assert commands, "Expected commands dispatched"
    snapshot = engine.snapshot_layers()
    assert sample_zone.zone_id in {key[0] for key in snapshot.keys()}

    engine.update_environment([SensorReading("foggy", 1.0, now)], now)
    await engine.async_dispatch_zone(sample_zone.zone_id, now)
    engine.clear_manual_override(sample_zone.zone_id)
    await engine.async_dispatch_zone(sample_zone.zone_id, now)
    cleared_snapshot = engine.bridge.snapshot()
    assert all("manual" not in key[1] for key in cleared_snapshot)

    engine.apply_mode(sample_zone.zone_id, "focus", ModeProfile(brightness_multiplier=1.1))
    await engine.async_dispatch_zone(sample_zone.zone_id, now)
    engine.clear_mode(sample_zone.zone_id, "focus")
    await engine.async_dispatch_zone(sample_zone.zone_id, now)
