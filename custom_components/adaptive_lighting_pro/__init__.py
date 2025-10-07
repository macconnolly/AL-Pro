"""Adaptive Lighting Pro integration setup."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_CONTROLLERS,
    CONF_LUX_SENSOR,
    CONF_SENSORS,
    CONF_SONOS_SENSOR,
    CONF_WEATHER_ENTITY,
    CONF_ZEN32_DEVICE,
    CONF_ZONES,
    DOMAIN,
    PLATFORMS,
)
from .core.runtime import AdaptiveLightingProRuntime


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


ZONE_YAML_SCHEMA = vol.Schema(
    {
        vol.Required("zone_id"): cv.slug,
        vol.Required("al_switch"): cv.entity_id,
        vol.Required("lights"): vol.Any(
            cv.entity_ids, vol.All(cv.ensure_list, [cv.entity_id]), cv.entity_id
        ),
        vol.Optional("enabled", default=True): cv.boolean,
        vol.Optional("zone_multiplier", default=1.0): vol.Coerce(float),
        vol.Optional("sunrise_offset_min", default=0): vol.Coerce(int),
        vol.Optional("environmental_boost_enabled", default=True): cv.boolean,
        vol.Optional("sunset_boost_enabled", default=True): cv.boolean,
    },
    extra=vol.ALLOW_EXTRA,
)


YAML_ENTRY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONES): vol.All(cv.ensure_list, [ZONE_YAML_SCHEMA]),
        vol.Optional(CONF_SENSORS): dict,
        vol.Optional(CONF_CONTROLLERS): dict,
        vol.Optional(CONF_LUX_SENSOR): cv.entity_id,
        vol.Optional(CONF_WEATHER_ENTITY): cv.entity_id,
        vol.Optional(CONF_SONOS_SENSOR): cv.entity_id,
        vol.Optional(CONF_ZEN32_DEVICE): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(DOMAIN): vol.All(_ensure_list, [YAML_ENTRY_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)


def _prepare_import_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    prepared: Dict[str, Any] = dict(entry)
    zones: Iterable[Dict[str, Any]] = prepared.get(CONF_ZONES, [])
    normalized_zones: List[Dict[str, Any]] = []
    for zone in zones:
        zone_data = dict(zone)
        lights = zone_data.get("lights", [])
        zone_data["lights"] = _ensure_list(lights)
        normalized_zones.append(zone_data)
    prepared[CONF_ZONES] = normalized_zones

    sensors: Dict[str, Any] = dict(prepared.pop(CONF_SENSORS, {}))
    for key in (CONF_LUX_SENSOR, CONF_WEATHER_ENTITY, CONF_SONOS_SENSOR):
        if key not in prepared and key in sensors:
            prepared[key] = sensors[key]

    controllers: Dict[str, Any] = dict(prepared.pop(CONF_CONTROLLERS, {}))
    if CONF_ZEN32_DEVICE not in prepared and CONF_ZEN32_DEVICE in controllers:
        prepared[CONF_ZEN32_DEVICE] = controllers[CONF_ZEN32_DEVICE]

    prepared.pop("installation_id", None)
    return prepared


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    yaml_config = config.get(DOMAIN)
    if yaml_config:
        entries = _ensure_list(yaml_config)
        for entry in entries:
            prepared = _prepare_import_entry(entry)
            await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=prepared,
            )
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
