from __future__ import annotations

import types

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.al_layer_manager import async_setup, async_setup_entry, async_unload_entry
from custom_components.al_layer_manager.storage import serialize_zone
from custom_components.al_layer_manager.const import DOMAIN


class FakeConfigEntry:
    def __init__(self, zone_payload):
        self.entry_id = "test-entry"
        self.options = {"zones": [zone_payload]}
        self.data = {}
        self._unload_callbacks = []
        self._update_listeners = []

    def add_update_listener(self, listener):
        self._update_listeners.append(listener)

        async def _remove():
            self._update_listeners.remove(listener)

        return _remove

    def async_on_unload(self, callback) -> None:
        self._unload_callbacks.append(callback)


@pytest.mark.asyncio
async def test_async_setup_entry_registers_services(sample_zone) -> None:
    hass = HomeAssistant()
    await async_setup(hass, {})

    zone_payload = serialize_zone(sample_zone)
    entry = FakeConfigEntry(zone_payload)

    await async_setup_entry(hass, entry)
    assert DOMAIN in hass.data
    assert hass.services.registered  # services registered

    # Trigger reload listener to exercise update path
    assert entry._update_listeners
    await entry._update_listeners[0](hass, entry)

    await async_unload_entry(hass, entry)
    assert entry.entry_id not in hass.data[DOMAIN]["runtime"]


@pytest.mark.asyncio
async def test_service_handlers_drive_runtime(sample_zone) -> None:
    hass = HomeAssistant()
    await async_setup(hass, {})

    zone_payload = serialize_zone(sample_zone)
    entry = FakeConfigEntry(zone_payload)
    await async_setup_entry(hass, entry)

    runtime = hass.data[DOMAIN]["runtime"][entry.entry_id]
    handlers = {
        name: handler
        for (domain, name, handler) in hass.services.registered
        if domain == DOMAIN
    }

    start_call = types.SimpleNamespace(
        data={
            "zone_id": sample_zone.zone_id,
            "brightness": 0.6,
            "kelvin": 3300,
            "reason": "test",
            "duration": "15",
        }
    )
    await handlers["start_manual_override"](start_call)
    override = runtime.engine.manual.snapshot()[sample_zone.zone_id]

    extend_call = types.SimpleNamespace(
        data={"zone_id": sample_zone.zone_id, "minutes": "10"}
    )
    previous_expiry = override.expires_at
    await handlers["extend_manual_override"](extend_call)
    updated_override = runtime.engine.manual.snapshot()[sample_zone.zone_id]
    assert updated_override.expires_at > previous_expiry

    await handlers["sync_zone"](types.SimpleNamespace(data={"zone_id": sample_zone.zone_id}))

    set_mode_call = types.SimpleNamespace(
        data={
            "zone_id": sample_zone.zone_id,
            "mode": "relax",
            "brightness_multiplier": 0.7,
            "kelvin_adjustment": -400,
            "transition_seconds": 6,
        }
    )
    await handlers["set_mode"](set_mode_call)
    stored_mode = runtime.engine.zones[sample_zone.zone_id].modes["relax"]
    assert stored_mode.transition_seconds == 6

    await handlers["clear_mode"](
        types.SimpleNamespace(data={"zone_id": sample_zone.zone_id, "mode": "relax"})
    )

    await handlers["clear_manual_override"](
        types.SimpleNamespace(data={"zone_id": sample_zone.zone_id})
    )
    assert sample_zone.zone_id not in runtime.engine.manual.snapshot()

    with pytest.raises(HomeAssistantError):
        await handlers["start_manual_override"](
            types.SimpleNamespace(
                data={"zone_id": "missing", "brightness": 0.5, "kelvin": 3200}
            )
        )
