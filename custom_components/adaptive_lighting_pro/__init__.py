"""Adaptive Lighting Pro integration setup."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .core.runtime import AdaptiveLightingProRuntime


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = AdaptiveLightingProRuntime(hass, entry)
    await runtime.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(runtime.async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime: AdaptiveLightingProRuntime = hass.data[DOMAIN].pop(entry.entry_id)
    await runtime.async_unload()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok
