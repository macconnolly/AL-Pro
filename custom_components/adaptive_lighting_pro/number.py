"""Number entities for Adaptive Lighting Pro."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import AdaptiveLightingProEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    entities: list[AdaptiveLightingProEntity] = [
        AdaptiveLightingProBrightnessStepNumber(runtime),
        AdaptiveLightingProColorTempStepNumber(runtime),
        AdaptiveLightingProSceneBrightnessOffsetNumber(runtime),
        AdaptiveLightingProSceneWarmthOffsetNumber(runtime),
    ]
    for zone_id in runtime.zone_states().keys():
        entities.append(AdaptiveLightingProSunriseOffsetNumber(runtime, zone_id))
        entities.append(AdaptiveLightingProZoneMultiplierNumber(runtime, zone_id))
    async_add_entities(entities)


class AdaptiveLightingProBrightnessStepNumber(AdaptiveLightingProEntity, NumberEntity):
    """Number entity for brightness adjustment steps."""

    _attr_native_min_value = 1
    _attr_native_max_value = 50
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Brightness Step", "alp_brightness_step")

    @property
    def native_value(self) -> float:
        return float(self._runtime.adjust_brightness_step())

    async def async_set_native_value(self, value: float) -> None:
        self._runtime.set_adjust_brightness_step(value)


class AdaptiveLightingProColorTempStepNumber(AdaptiveLightingProEntity, NumberEntity):
    """Number entity for color temperature adjustment steps."""

    _attr_native_min_value = 50
    _attr_native_max_value = 1000
    _attr_native_step = 50
    _attr_native_unit_of_measurement = "K"

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Color Temp Step", "alp_color_temp_step")

    @property
    def native_value(self) -> float:
        return float(self._runtime.adjust_color_temp_step())

    async def async_set_native_value(self, value: float) -> None:
        self._runtime.set_adjust_color_temp_step(value)


class AdaptiveLightingProSceneBrightnessOffsetNumber(
    AdaptiveLightingProEntity, NumberEntity
):
    """Number entity for scene brightness offsets."""

    _attr_native_min_value = -80
    _attr_native_max_value = 20
    _attr_native_step = 5
    _attr_native_unit_of_measurement = "%"

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Scene Brightness Offset", "alp_scene_brightness_offset")

    @property
    def native_value(self) -> float:
        return float(self._runtime.scene_brightness_offset())

    async def async_set_native_value(self, value: float) -> None:
        self._runtime.set_scene_brightness_offset(value)


class AdaptiveLightingProSceneWarmthOffsetNumber(
    AdaptiveLightingProEntity, NumberEntity
):
    """Number entity for scene warmth offsets."""

    _attr_native_min_value = -1000
    _attr_native_max_value = 500
    _attr_native_step = 100
    _attr_native_unit_of_measurement = "K"

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Scene Warmth Offset", "alp_scene_warmth_offset")

    @property
    def native_value(self) -> float:
        return float(self._runtime.scene_warmth_offset())

    async def async_set_native_value(self, value: float) -> None:
        self._runtime.set_scene_warmth_offset(value)


class AdaptiveLightingProSunriseOffsetNumber(AdaptiveLightingProEntity, NumberEntity):
    """Number for per-zone sunrise offsets."""

    _attr_native_unit_of_measurement = "min"
    _attr_native_step = 1
    _attr_native_min_value = -120
    _attr_native_max_value = 120

    def __init__(self, runtime, zone_id: str) -> None:
        super().__init__(runtime, f"ALP Sunrise Offset {zone_id}", f"alp_sunrise_offset_{zone_id}")
        self._zone_id = zone_id

    @property
    def native_value(self) -> float:
        return float(self._runtime.zone_sunrise_offset(self._zone_id))

    async def async_set_native_value(self, value: float) -> None:
        self._runtime.set_zone_sunrise_offset(self._zone_id, value)


class AdaptiveLightingProZoneMultiplierNumber(AdaptiveLightingProEntity, NumberEntity):
    """Number to adjust zone multiplier."""

    _attr_native_step = 0.1
    _attr_native_min_value = 0.1
    _attr_native_max_value = 5.0

    def __init__(self, runtime, zone_id: str) -> None:
        super().__init__(runtime, f"ALP Zone Multiplier {zone_id}", f"alp_zone_multiplier_{zone_id}")
        self._zone_id = zone_id

    @property
    def native_value(self) -> float:
        return float(self._runtime.zone_multiplier(self._zone_id))

    async def async_set_native_value(self, value: float) -> None:
        self._runtime.set_zone_multiplier(self._zone_id, value)
