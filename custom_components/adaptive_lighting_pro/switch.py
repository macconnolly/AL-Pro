"""Switch platform for Adaptive Lighting Pro."""
from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_LAST_ERROR, ATTR_LAST_SYNC_MS, ATTR_MANUAL_ACTIVE, ATTR_SUNRISE_OFFSET, DOMAIN
from .entity import AdaptiveLightingProEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    entities = [
        AdaptiveLightingProGlobalPauseSwitch(runtime),
        AdaptiveLightingProZoneSwitch(runtime, zone_id)
        for zone_id in runtime.zone_states().keys()
    ]
    async_add_entities(entities)


class AdaptiveLightingProGlobalPauseSwitch(AdaptiveLightingProEntity, SwitchEntity):
    """Global pause switch mirroring legacy control."""

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Global Pause", "alp_global_pause_switch")

    @property
    def is_on(self) -> bool:
        return self._runtime.globally_paused()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._runtime.set_global_pause(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._runtime.set_global_pause(False)


class AdaptiveLightingProZoneSwitch(AdaptiveLightingProEntity, SwitchEntity):
    """Switch to enable or disable zone orchestration."""

    def __init__(self, runtime, zone_id: str) -> None:
        super().__init__(runtime, f"ALP Zone {zone_id}", f"alp_zone_switch_{zone_id}")
        self._zone_id = zone_id

    @property
    def is_on(self) -> bool:
        return self._runtime.zone_states()[self._zone_id]["enabled"]

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        state = self._runtime.zone_states()[self._zone_id]
        return {
            ATTR_MANUAL_ACTIVE: state.get("manual_active"),
            ATTR_LAST_SYNC_MS: state.get("last_sync_ms"),
            ATTR_LAST_ERROR: state.get("last_error"),
            ATTR_SUNRISE_OFFSET: state.get("sunrise_offset_min"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._runtime.enable_zone(self._zone_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._runtime.disable_zone(self._zone_id)
