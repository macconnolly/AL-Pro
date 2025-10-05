"""Binary sensor platform for Adaptive Lighting Pro."""
from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RATE_LIMIT_ENTITY_ID, SONOS_SKIP_ENTITY_ID
from .entity import AdaptiveLightingProEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    entities = [
        AdaptiveLightingProRateLimitBinarySensor(runtime),
        AdaptiveLightingProSonosSkipBinarySensor(runtime),
    ]
    for action, name in MANUAL_ACTION_SENSORS.items():
        entities.append(AdaptiveLightingProManualActionBinarySensor(runtime, action, name))
    for zone_id in runtime.zone_states().keys():
        entities.append(AdaptiveLightingProManualBinarySensor(runtime, zone_id))
    async_add_entities(entities)


MANUAL_ACTION_SENSORS = {
    "brighter": "ALP Brighter Active",
    "dimmer": "ALP Dimmer Active",
    "warmer": "ALP Warmer Active",
    "cooler": "ALP Cooler Active",
}


class AdaptiveLightingProRateLimitBinarySensor(
    AdaptiveLightingProEntity, BinarySensorEntity
):
    """Binary sensor tracking rate limit events."""

    _attr_entity_id = RATE_LIMIT_ENTITY_ID

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Rate Limit", RATE_LIMIT_ENTITY_ID)

    @property
    def is_on(self) -> bool:
        return self._runtime.rate_limit_reached()

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "rate_window_load": self._runtime.analytics_summary().get(
                "rate_window_load", 0
            )
        }


class AdaptiveLightingProManualBinarySensor(
    AdaptiveLightingProEntity, BinarySensorEntity
):
    """Per-zone manual control sensor."""

    def __init__(self, runtime, zone_id: str) -> None:
        super().__init__(runtime, f"ALP Manual {zone_id}", f"alp_manual_{zone_id}")
        self._zone_id = zone_id

    @property
    def is_on(self) -> bool:
        return bool(self._runtime.zone_states()[self._zone_id]["manual_active"])

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        state = self._runtime.zone_states()[self._zone_id]
        return {"duration": state.get("manual_duration")}


class AdaptiveLightingProManualActionBinarySensor(
    AdaptiveLightingProEntity, BinarySensorEntity
):
    """Binary sensor mirroring manual adjustment scripts."""

    def __init__(self, runtime, action: str, name: str) -> None:
        super().__init__(runtime, name, f"alp_{action}_active")
        self._action = action

    @property
    def is_on(self) -> bool:
        return bool(self._runtime.manual_action_flags().get(self._action))


class AdaptiveLightingProSonosSkipBinarySensor(
    AdaptiveLightingProEntity, BinarySensorEntity
):
    """Binary sensor tracking pending Sonos skip requests."""

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Sonos Skip Pending", SONOS_SKIP_ENTITY_ID)

    @property
    def is_on(self) -> bool:
        return self._runtime.sonos_skip_next()
