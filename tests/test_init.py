from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

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
