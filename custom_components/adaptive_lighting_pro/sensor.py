"""Sensor platform for Adaptive Lighting Pro."""
from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ANALYTICS_SENSOR_ID,
    DOMAIN,
    HEALTH_SENSOR_ID,
    TELEMETRY_SENSOR_ID,
)
from .entity import AdaptiveLightingProEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    entities = [
        AdaptiveLightingProHealthSensor(runtime),
        AdaptiveLightingProAnalyticsSensor(runtime),
        AdaptiveLightingProTelemetrySensor(runtime),
    ]
    async_add_entities(entities)


class AdaptiveLightingProHealthSensor(AdaptiveLightingProEntity, SensorEntity):
    """Expose health score."""

    _attr_native_unit_of_measurement = "score"
    _attr_entity_id = HEALTH_SENSOR_ID

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Health Score", HEALTH_SENSOR_ID)

    @property
    def native_value(self) -> int:
        return self._runtime.health_score()

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._runtime.analytics_summary()


class AdaptiveLightingProAnalyticsSensor(AdaptiveLightingProEntity, SensorEntity):
    """Expose analytics summary counters."""

    _attr_entity_id = ANALYTICS_SENSOR_ID

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Analytics Summary", ANALYTICS_SENSOR_ID)

    @property
    def native_value(self) -> int:
        summary = self._runtime.analytics_summary()
        return int(summary.get("sync_count", 0))

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._runtime.analytics_summary()


class AdaptiveLightingProTelemetrySensor(AdaptiveLightingProEntity, SensorEntity):
    """Aggregated telemetry mirroring legacy dashboard sensors."""

    _attr_entity_id = TELEMETRY_SENSOR_ID

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP System Snapshot", TELEMETRY_SENSOR_ID)

    @property
    def native_value(self) -> str:
        return str(self._runtime.telemetry_snapshot().get("state", "unknown"))

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        snapshot = self._runtime.telemetry_snapshot().copy()
        snapshot.pop("state", None)
        return snapshot
