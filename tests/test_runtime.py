from __future__ import annotations

from datetime import datetime
import types

import pytest

from homeassistant.core import HomeAssistant, State

from custom_components.al_layer_manager.runtime import LayerManagerRuntime


class StubCoordinator:
    def __init__(self) -> None:
        self.payloads = []

    def register_external_summary(self, namespace: str, payload):
        self.payloads.append((namespace, payload))


@pytest.mark.asyncio
async def test_runtime_dispatches_commands(sample_zone) -> None:
    hass = HomeAssistant()
    coordinator = StubCoordinator()
    runtime = LayerManagerRuntime(hass, {sample_zone.zone_id: sample_zone}, coordinator=coordinator)

    now = datetime.fromisoformat("2024-02-01T07:15:00")
    await runtime.async_start_manual(sample_zone.zone_id, 0.6, 3300, "test", duration=10)
    await runtime.async_sync_zone(sample_zone.zone_id, now)

    assert hass.services.calls, "Expected layer_manager commands to be dispatched"
    domains = {call["domain"] for call in hass.services.calls}
    assert "layer_manager" in domains
    assert coordinator.payloads, "Telemetry should be sent to the coordinator"


@pytest.mark.asyncio
async def test_environment_listener_updates_state(sample_zone) -> None:
    zone = sample_zone
    zone.helpers["environment_foggy"] = "sensor.foggy_switch"
    hass = HomeAssistant()
    runtime = LayerManagerRuntime(hass, {zone.zone_id: zone})
    await runtime.async_start()

    # Simulate environment event
    assert hass._listeners
    _, callback = hass._listeners[0]
    state = State("sensor.foggy_switch", "on")
    event = types.SimpleNamespace(data={"entity_id": "sensor.foggy_switch", "new_state": state})
    callback(event)

    env_state = runtime.engine.environment.get_state(zone.zone_id)
    assert env_state is not None
    assert env_state.active_profiles

