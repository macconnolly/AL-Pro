"""Number entities for Adaptive Lighting Pro."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import (
    DOMAIN,
    BRIGHTNESS_ADJUSTMENT_MIN,
    BRIGHTNESS_ADJUSTMENT_MAX,
    BRIGHTNESS_ADJUSTMENT_STEP,
    WARMTH_ADJUSTMENT_MIN,
    WARMTH_ADJUSTMENT_MAX,
    WARMTH_ADJUSTMENT_STEP,
    BRIGHTNESS_INCREMENT_MIN,
    BRIGHTNESS_INCREMENT_MAX,
    BRIGHTNESS_INCREMENT_STEP,
    COLOR_TEMP_INCREMENT_MIN,
    COLOR_TEMP_INCREMENT_MAX,
    COLOR_TEMP_INCREMENT_STEP,
    MANUAL_TIMEOUT_MIN,
    MANUAL_TIMEOUT_MAX,
    MANUAL_TIMEOUT_STEP,
)
from .entity import ALPEntity

if TYPE_CHECKING:
    from .coordinator import ALPDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Lighting Pro number entities."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: ALPDataUpdateCoordinator = (
        entry_data.get("coordinator") if isinstance(entry_data, dict) else entry_data
    )

    entities = [
        ALPBrightnessAdjustmentNumber(coordinator, config_entry),
        ALPWarmthAdjustmentNumber(coordinator, config_entry),
        ALPBrightnessIncrementNumber(coordinator, config_entry),
        ALPColorTempIncrementNumber(coordinator, config_entry),
        ALPManualTimeoutNumber(coordinator, config_entry),
    ]

    async_add_entities(entities)


class ALPBrightnessAdjustmentNumber(ALPEntity, NumberEntity):
    """Number entity for brightness adjustment."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = BRIGHTNESS_ADJUSTMENT_MIN
    _attr_native_max_value = BRIGHTNESS_ADJUSTMENT_MAX
    _attr_native_step = BRIGHTNESS_ADJUSTMENT_STEP
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:brightness-6"
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: ALPDataUpdateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the brightness adjustment number entity."""
        super().__init__(
            coordinator,
            config_entry,
            "number",
            "brightness_adjustment",
            "Brightness Adjustment",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current brightness adjustment value."""
        try:
            return self.coordinator.get_brightness_adjustment()
        except (AttributeError, KeyError) as err:
            _LOGGER.error("Error getting brightness adjustment value: %s", err)
            return 0.0

    async def async_set_native_value(self, value: float) -> None:
        """Update the brightness adjustment value."""
        try:
            # Sliders are persistent preferences - do NOT start timers
            await self.coordinator.set_brightness_adjustment(int(value), start_timers=False)
            _LOGGER.debug("Brightness adjustment set to %s%%", value)
        except Exception as err:
            _LOGGER.error("Error setting brightness adjustment: %s", err)
            raise


class ALPWarmthAdjustmentNumber(ALPEntity, NumberEntity):
    """Number entity for warmth adjustment."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = WARMTH_ADJUSTMENT_MIN
    _attr_native_max_value = WARMTH_ADJUSTMENT_MAX
    _attr_native_step = WARMTH_ADJUSTMENT_STEP
    _attr_native_unit_of_measurement = "K"
    _attr_icon = "mdi:thermometer"
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: ALPDataUpdateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the warmth adjustment number entity."""
        super().__init__(
            coordinator,
            config_entry,
            "number",
            "warmth_adjustment",
            "Warmth Adjustment",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current warmth adjustment value."""
        try:
            return self.coordinator.get_warmth_adjustment()
        except (AttributeError, KeyError) as err:
            _LOGGER.error("Error getting warmth adjustment value: %s", err)
            return 0.0

    async def async_set_native_value(self, value: float) -> None:
        """Update the warmth adjustment value."""
        try:
            # Sliders are persistent preferences - do NOT start timers
            await self.coordinator.set_warmth_adjustment(int(value), start_timers=False)
            _LOGGER.debug("Warmth adjustment set to %sK", value)
        except Exception as err:
            _LOGGER.error("Error setting warmth adjustment: %s", err)
            raise


class ALPBrightnessIncrementNumber(ALPEntity, NumberEntity):
    """Number entity for brightness increment."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = BRIGHTNESS_INCREMENT_MIN
    _attr_native_max_value = BRIGHTNESS_INCREMENT_MAX
    _attr_native_step = BRIGHTNESS_INCREMENT_STEP
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:format-line-spacing"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ALPDataUpdateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the brightness increment number entity."""
        super().__init__(
            coordinator,
            config_entry,
            "number",
            "brightness_increment",
            "Brightness Increment",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current brightness increment value."""
        try:
            return float(self.coordinator.get_brightness_increment())
        except (AttributeError, KeyError) as err:
            _LOGGER.error("Error getting brightness increment value: %s", err)
            return 10.0

    async def async_set_native_value(self, value: float) -> None:
        """Update the brightness increment value."""
        try:
            await self.coordinator.set_brightness_increment(int(value))
            _LOGGER.debug("Brightness increment set to %s%%", value)
        except Exception as err:
            _LOGGER.error("Error setting brightness increment: %s", err)
            raise


class ALPColorTempIncrementNumber(ALPEntity, NumberEntity):
    """Number entity for color temperature increment."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = COLOR_TEMP_INCREMENT_MIN
    _attr_native_max_value = COLOR_TEMP_INCREMENT_MAX
    _attr_native_step = COLOR_TEMP_INCREMENT_STEP
    _attr_native_unit_of_measurement = "K"
    _attr_icon = "mdi:format-line-spacing"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ALPDataUpdateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the color temperature increment number entity."""
        super().__init__(
            coordinator,
            config_entry,
            "number",
            "color_temp_increment",
            "Color Temperature Increment",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current color temperature increment value."""
        try:
            return float(self.coordinator.get_color_temp_increment())
        except (AttributeError, KeyError) as err:
            _LOGGER.error("Error getting color temperature increment value: %s", err)
            return 500.0

    async def async_set_native_value(self, value: float) -> None:
        """Update the color temperature increment value."""
        try:
            await self.coordinator.set_color_temp_increment(int(value))
            _LOGGER.debug("Color temperature increment set to %sK", value)
        except Exception as err:
            _LOGGER.error("Error setting color temperature increment: %s", err)
            raise


class ALPManualTimeoutNumber(ALPEntity, NumberEntity):
    """Number entity for manual control timeout."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = MANUAL_TIMEOUT_MIN
    _attr_native_max_value = MANUAL_TIMEOUT_MAX
    _attr_native_step = MANUAL_TIMEOUT_STEP
    _attr_native_unit_of_measurement = "s"
    _attr_icon = "mdi:timer-outline"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ALPDataUpdateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the manual timeout number entity."""
        super().__init__(
            coordinator,
            config_entry,
            "number",
            "manual_timeout",
            "Manual Control Timeout",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current manual timeout value."""
        try:
            return float(self.coordinator.get_manual_control_timeout())
        except (AttributeError, KeyError) as err:
            _LOGGER.error("Error getting manual timeout value: %s", err)
            return 3600.0

    async def async_set_native_value(self, value: float) -> None:
        """Update the manual timeout value."""
        try:
            await self.coordinator.set_manual_control_timeout(int(value))
            _LOGGER.debug("Manual timeout set to %ss", value)
        except Exception as err:
            _LOGGER.error("Error setting manual timeout: %s", err)
            raise
