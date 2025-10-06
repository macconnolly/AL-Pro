"""Home Assistant entrypoint for AL Layer Manager."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

from .const import DOMAIN
from .engine import LayerManagerEngine as LayerManagerIntegration
from .models import ZoneModel
from .services import validate_manual_service, validate_mode_service
from .storage import deserialize_zone, read_storage
if TYPE_CHECKING:  # pragma: no cover - typing helpers only
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType


RUNTIME_DATA = "runtime"
ZONE_INDEX = "zone_index"
SERVICES_REGISTERED = "services_registered"


async def async_setup(hass: "HomeAssistant", config: "ConfigType") -> bool:
    hass.data.setdefault(DOMAIN, {ZONE_INDEX: defaultdict(list)})
    return True


async def async_setup_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> bool:
    from .runtime import LayerManagerRuntime

    runtime = LayerManagerRuntime(
        hass,
        _load_zones_from_entry(entry),
        layer_domain=entry.options.get("layer_domain", "layer_manager"),
        coordinator=_get_layer_manager_coordinator(hass, entry.options.get("layer_manager_entry_id")),
    )
    await runtime.async_start()

    hass.data[DOMAIN].setdefault(RUNTIME_DATA, {})[entry.entry_id] = runtime
    _index_zones(hass, runtime, entry.entry_id)
    await _ensure_services_registered(hass)

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> bool:
    runtime = hass.data[DOMAIN][RUNTIME_DATA].pop(entry.entry_id)
    await runtime.async_stop()
    _remove_zone_index(hass, entry.entry_id)
    return True


async def _async_reload_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> None:
    runtime = hass.data[DOMAIN][RUNTIME_DATA][entry.entry_id]
    await runtime.async_reload_zones(_load_zones_from_entry(entry))
    _remove_zone_index(hass, entry.entry_id)
    _index_zones(hass, runtime, entry.entry_id)


def _load_zones_from_entry(entry: "ConfigEntry") -> Dict[str, ZoneModel]:
    from homeassistant.exceptions import HomeAssistantError

    payload = entry.options.get("zones") or entry.data.get("zones")
    zones: Dict[str, ZoneModel] = {}
    if isinstance(payload, list):
        for record in payload:
            zone = deserialize_zone(record)
            zones[zone.zone_id] = zone
    elif path := entry.options.get("zones_storage_path"):
        zones_list = read_storage(Path(path))
        zones = {zone.zone_id: zone for zone in zones_list}
    else:
        raise HomeAssistantError("AL Layer Manager requires zone definitions in config entry options")
    return zones


def _index_zones(hass: "HomeAssistant", runtime, entry_id: str) -> None:
    zone_index = hass.data[DOMAIN].setdefault(ZONE_INDEX, defaultdict(list))
    for zone_id in runtime.zones.keys():
        zone_index[zone_id].append(entry_id)


def _remove_zone_index(hass: "HomeAssistant", entry_id: str) -> None:
    zone_index = hass.data[DOMAIN].setdefault(ZONE_INDEX, defaultdict(list))
    for zone_id in list(zone_index.keys()):
        zone_index[zone_id] = [value for value in zone_index[zone_id] if value != entry_id]
        if not zone_index[zone_id]:
            zone_index.pop(zone_id)


def _get_layer_manager_coordinator(hass: "HomeAssistant", entry_id: Optional[str]) -> Optional[object]:
    if not entry_id:
        return None
    layer_data = hass.data.get("layer_manager")
    if not layer_data:
        return None
    return layer_data.get(entry_id)


async def _ensure_services_registered(hass: "HomeAssistant") -> None:
    from homeassistant.exceptions import HomeAssistantError
    from .runtime import LayerManagerRuntime

    registry = hass.data[DOMAIN]
    if registry.get(SERVICES_REGISTERED):
        return

    async def _resolve_runtime(zone_id: str) -> LayerManagerRuntime:
        zone_index = hass.data[DOMAIN].get(ZONE_INDEX, {})
        entry_ids = zone_index.get(zone_id, [])
        if not entry_ids:
            raise HomeAssistantError(f"No AL Layer Manager zone configured for {zone_id}")
        runtime = hass.data[DOMAIN][RUNTIME_DATA][entry_ids[0]]
        return runtime

    async def handle_start_manual(call) -> None:
        payload = dict(call.data)
        validate_manual_service(payload)
        runtime = await _resolve_runtime(payload["zone_id"])
        duration = payload.get("duration")
        duration_value = int(duration) if duration is not None else None
        await runtime.async_start_manual(
            payload["zone_id"],
            float(payload["brightness"]),
            int(payload["kelvin"]),
            payload.get("reason", "service"),
            duration_value,
        )

    async def handle_extend_manual(call) -> None:
        payload = dict(call.data)
        zone_id = payload["zone_id"]
        runtime = await _resolve_runtime(zone_id)
        minutes = int(payload.get("minutes", 5))
        await runtime.async_extend_manual(zone_id, minutes)

    async def handle_clear_manual(call) -> None:
        zone_id = call.data["zone_id"]
        runtime = await _resolve_runtime(zone_id)
        await runtime.async_clear_manual(zone_id)

    async def handle_sync_zone(call) -> None:
        zone_id = call.data["zone_id"]
        runtime = await _resolve_runtime(zone_id)
        timestamp = call.data.get("timestamp")
        moment = datetime.fromisoformat(timestamp) if timestamp else None
        await runtime.async_sync_zone(zone_id, moment)

    async def handle_set_mode(call) -> None:
        payload = dict(call.data)
        validate_mode_service(payload)
        zone_id = payload["zone_id"]
        runtime = await _resolve_runtime(zone_id)
        profile = runtime.engine.zones[zone_id].modes.get(payload["mode"])
        if not profile:
            raise HomeAssistantError(f"Mode {payload['mode']} not defined for zone {zone_id}")
        await runtime.async_set_mode(payload["mode"], profile, zone_id)

    async def handle_clear_mode(call) -> None:
        zone_id = call.data["zone_id"]
        runtime = await _resolve_runtime(zone_id)
        await runtime.async_clear_mode(call.data["mode"], zone_id)

    hass.services.async_register(DOMAIN, "start_manual_override", handle_start_manual)
    hass.services.async_register(DOMAIN, "extend_manual_override", handle_extend_manual)
    hass.services.async_register(DOMAIN, "clear_manual_override", handle_clear_manual)
    hass.services.async_register(DOMAIN, "sync_zone", handle_sync_zone)
    hass.services.async_register(DOMAIN, "set_mode", handle_set_mode)
    hass.services.async_register(DOMAIN, "clear_mode", handle_clear_mode)

    registry[SERVICES_REGISTERED] = True


__all__ = ["LayerManagerIntegration"]
