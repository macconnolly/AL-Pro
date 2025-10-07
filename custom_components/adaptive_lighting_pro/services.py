"""Service handlers for Adaptive Lighting Pro.

This module implements the service call handlers for all ALP services.
Services interact with the coordinator to modify state and trigger updates.

Service Responsibilities:
- Validate service call parameters
- Extract coordinator from hass.data
- Call coordinator methods with validated parameters
- Handle errors gracefully with user-friendly messages
- Log all service calls at info level
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    SERVICE_ADJUST_BRIGHTNESS,
    SERVICE_ADJUST_COLOR_TEMP,
    SERVICE_APPLY_SCENE,
    SERVICE_CLEAR_MANUAL_CONTROL,
    SERVICE_RESET_ALL,
    SERVICE_RESET_MANUAL_ADJUSTMENTS,
    SERVICE_SET_MODE,
    SERVICE_SET_WAKE_ALARM,
    SERVICE_CLEAR_WAKE_ALARM,
    Scene,
)

SERVICE_CYCLE_SCENE = "cycle_scene"

if TYPE_CHECKING:
    from .coordinator import ALPDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service parameter schemas
ADJUST_BRIGHTNESS_SCHEMA = vol.Schema({
    vol.Required("value"): vol.All(vol.Coerce(int), vol.Range(min=-100, max=100)),
    vol.Optional("temporary", default=True): cv.boolean,
})

ADJUST_COLOR_TEMP_SCHEMA = vol.Schema({
    vol.Required("value"): vol.All(vol.Coerce(int), vol.Range(min=-2500, max=2500)),
    vol.Optional("temporary", default=True): cv.boolean,
})

APPLY_SCENE_SCHEMA = vol.Schema({
    vol.Required("scene"): vol.In([s.value for s in Scene]),
})

CLEAR_MANUAL_CONTROL_SCHEMA = vol.Schema({
    vol.Optional("zone_id"): cv.string,
})

SET_WAKE_ALARM_SCHEMA = vol.Schema({
    vol.Required("alarm_time"): cv.datetime,
})

CLEAR_WAKE_ALARM_SCHEMA = vol.Schema({})


def _get_coordinator(hass: HomeAssistant) -> ALPDataUpdateCoordinator | None:
    """Get the coordinator from hass.data.

    Returns first coordinator found (supports single instance).
    Handles both dict-based storage ({"coordinator": ...}) and direct coordinator storage.

    Returns:
        Coordinator instance or None if not found
    """
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data:
        _LOGGER.error("No ALP coordinators found in hass.data")
        return None

    # Get first entry (single instance support)
    entry_data = next(iter(domain_data.values()), None)
    if not entry_data:
        _LOGGER.error("No ALP entry data found")
        return None

    # Handle both dict-based storage and direct coordinator storage
    if isinstance(entry_data, dict):
        return entry_data.get("coordinator")
    else:
        # Legacy direct coordinator storage
        return entry_data


def async_register_services(hass: HomeAssistant) -> None:
    """Register all ALP services with Home Assistant.

    Services are registered once globally and interact with the coordinator
    stored in hass.data. Each service handler validates parameters, retrieves
    the coordinator, calls appropriate coordinator methods, and handles errors.

    Args:
        hass: Home Assistant instance
    """
    _LOGGER.info("Registering Adaptive Lighting Pro services")

    async def handle_adjust_brightness(call: ServiceCall) -> None:
        """Handle adaptive_lighting_pro.adjust_brightness service call.

        Adjusts global brightness offset using asymmetric boundary logic.
        Positive values raise minimum brightness, negative lower maximum.

        Parameters:
            value: Brightness adjustment (-100 to +100 percent)
            temporary: If True, start timers (default True for backward compatibility)
        """
        coordinator = _get_coordinator(hass)
        if not coordinator:
            _LOGGER.error("Cannot adjust brightness: coordinator not found")
            return

        try:
            value = call.data["value"]
            temporary = call.data.get("temporary", True)
            _LOGGER.info("Adjusting brightness by %+d%% (temporary=%s)", value, temporary)

            # Start timers based on temporary flag
            await coordinator.set_brightness_adjustment(value, start_timers=temporary)

            _LOGGER.info("Brightness adjustment complete: %+d%%", value)
        except Exception as err:
            _LOGGER.error("Failed to adjust brightness: %s", err, exc_info=True)

    async def handle_adjust_color_temp(call: ServiceCall) -> None:
        """Handle adaptive_lighting_pro.adjust_color_temp service call.

        Adjusts global warmth offset using asymmetric boundary logic.
        Positive values make cooler (higher K), negative warmer (lower K).

        Parameters:
            value: Color temp adjustment (-2500 to +2500 Kelvin)
        """
        coordinator = _get_coordinator(hass)
        if not coordinator:
            _LOGGER.error("Cannot adjust color temp: coordinator not found")
            return

        try:
            value = call.data["value"]
            temporary = call.data.get("temporary", True)
            _LOGGER.info("Adjusting color temp by %+dK (temporary=%s)", value, temporary)

            # Start timers based on temporary flag
            await coordinator.set_warmth_adjustment(value, start_timers=temporary)

            _LOGGER.info("Color temp adjustment complete: %+dK", value)
        except Exception as err:
            _LOGGER.error("Failed to adjust color temp: %s", err, exc_info=True)

    async def handle_reset_manual_adjustments(call: ServiceCall) -> None:
        """Handle adaptive_lighting_pro.reset_manual_adjustments service call.

        Resets global brightness and warmth adjustments to zero AND clears scene offsets.
        Also cancels all manual control timers and restores adaptive lighting.
        """
        coordinator = _get_coordinator(hass)
        if not coordinator:
            _LOGGER.error("Cannot reset adjustments: coordinator not found")
            return

        try:
            _LOGGER.info("Resetting manual adjustments, scene offsets, and manual control timers")

            # Clear manual adjustments
            await coordinator.set_brightness_adjustment(0)
            await coordinator.set_warmth_adjustment(0)

            # Clear scene offsets via coordinator API (proper encapsulation)
            await coordinator.clear_scene_offsets()

            # Cancel all manual control timers and restore adaptive lighting
            cancelled_count = await coordinator.cancel_all_timers()

            _LOGGER.info(
                "Reset complete: adjustments cleared, scenes cleared, %d timers cancelled",
                cancelled_count
            )
        except Exception as err:
            _LOGGER.error("Failed to reset adjustments: %s", err, exc_info=True)

    async def handle_reset_all(call: ServiceCall) -> None:
        """Handle adaptive_lighting_pro.reset_all service call (nuclear reset).

        Performs complete reset:
        - Resets brightness and warmth adjustments to zero
        - Clears scene offsets
        - Cancels all manual control timers
        - Restores adaptive lighting to all zones
        """
        coordinator = _get_coordinator(hass)
        if not coordinator:
            _LOGGER.error("Cannot perform nuclear reset: coordinator not found")
            return

        try:
            _LOGGER.info("Performing nuclear reset (all adjustments + scenes + timers)")

            # Reset manual adjustments
            await coordinator.set_brightness_adjustment(0)
            await coordinator.set_warmth_adjustment(0)

            # Clear scene offsets via coordinator API
            await coordinator.clear_scene_offsets()

            # Cancel all timers
            cancelled_count = await coordinator.cancel_all_timers()

            _LOGGER.info(
                "Nuclear reset complete: adjustments reset, scenes cleared, %d timers cancelled",
                cancelled_count
            )
        except Exception as err:
            _LOGGER.error("Failed to perform nuclear reset: %s", err, exc_info=True)

    async def handle_clear_manual_control(call: ServiceCall) -> None:
        """Handle adaptive_lighting_pro.clear_manual_control service call.

        Clears manual control for specified zone or all zones.
        Cancels timers and restores adaptive lighting.

        Parameters:
            zone_id (optional): Specific zone to clear, or all if omitted
        """
        coordinator = _get_coordinator(hass)
        if not coordinator:
            _LOGGER.error("Cannot clear manual control: coordinator not found")
            return

        try:
            zone_id = call.data.get("zone_id")

            if zone_id:
                _LOGGER.info("Clearing manual control for zone: %s", zone_id)
                success = await coordinator.cancel_manual_timer(zone_id)
                if success:
                    _LOGGER.info("Manual control cleared for zone: %s", zone_id)
                else:
                    _LOGGER.warning("Failed to clear manual control for zone: %s", zone_id)
            else:
                _LOGGER.info("Clearing manual control for all zones")
                cancelled_count = await coordinator.cancel_all_timers()
                _LOGGER.info("Manual control cleared for %d zones", cancelled_count)

        except Exception as err:
            _LOGGER.error("Failed to clear manual control: %s", err, exc_info=True)

    async def handle_set_mode(call: ServiceCall) -> None:
        """Handle adaptive_lighting_pro.set_mode service call.

        Note: Mode system removed in simplified architecture.
        This service is deprecated - use scenes instead.
        """
        _LOGGER.warning(
            "set_mode service is deprecated (mode system removed). Use apply_scene instead."
        )

    async def handle_apply_scene(call: ServiceCall) -> None:
        """Handle adaptive_lighting_pro.apply_scene service call.

        Applies a predefined scene with actions and offset adjustments.
        Starts manual timers for all zones.

        Parameters:
            scene: Scene name (default, all_lights, no_spotlights, evening_comfort, ultra_dim)
        """
        coordinator = _get_coordinator(hass)
        if not coordinator:
            _LOGGER.error("Cannot apply scene: coordinator not found")
            return

        try:
            scene_str = call.data["scene"]
            scene = Scene(scene_str)

            _LOGGER.info("Applying scene: %s", scene_str)

            success = await coordinator.apply_scene(scene)

            if success:
                _LOGGER.info("Scene applied successfully: %s", scene_str)
            else:
                _LOGGER.error("Failed to apply scene: %s", scene_str)

        except ValueError as err:
            _LOGGER.error("Invalid scene: %s", call.data.get("scene"))
        except Exception as err:
            _LOGGER.error("Failed to apply scene: %s", err, exc_info=True)

    async def handle_cycle_scene(call: ServiceCall) -> None:
        """Handle adaptive_lighting_pro.cycle_scene service call.

        Cycles to the next scene in the sequence.
        """
        coordinator = _get_coordinator(hass)
        if not coordinator:
            _LOGGER.error("Cannot cycle scene: coordinator not found")
            return

        try:
            scene = await coordinator.cycle_scene()
            _LOGGER.info("Cycled to scene: %s", scene.value if hasattr(scene, 'value') else scene)
        except Exception as err:
            _LOGGER.error("Failed to cycle scene: %s", err, exc_info=True)

    async def handle_set_wake_alarm(call: ServiceCall) -> None:
        """Handle adaptive_lighting_pro.set_wake_alarm service call.

        Manually set wake alarm time to trigger wake sequence.
        Useful for testing or integrating with non-Sonos alarm systems.

        Parameters:
            alarm_time: Datetime when alarm will fire (wake sequence starts 15min before)
        """
        coordinator = _get_coordinator(hass)
        if not coordinator:
            _LOGGER.error("Cannot set wake alarm: coordinator not found")
            return

        try:
            alarm_time = call.data["alarm_time"]

            _LOGGER.info("Setting wake alarm for %s", alarm_time.isoformat())

            # Use coordinator method (handles timezone conversion, validation, refresh)
            await coordinator.set_wake_alarm(alarm_time)

            wake_start = coordinator.get_wake_start_time()
            if wake_start:
                _LOGGER.info("Wake alarm set successfully. Wake sequence will start at %s",
                            wake_start.isoformat())
            else:
                _LOGGER.info("Wake alarm set successfully")
        except ValueError as err:
            # Coordinator raises ValueError for past alarms
            _LOGGER.error("Invalid wake alarm: %s", err)
        except Exception as err:
            _LOGGER.error("Failed to set wake alarm: %s", err, exc_info=True)

    async def handle_clear_wake_alarm(call: ServiceCall) -> None:
        """Handle adaptive_lighting_pro.clear_wake_alarm service call.

        Clear wake alarm and cancel active wake sequence.
        """
        coordinator = _get_coordinator(hass)
        if not coordinator:
            _LOGGER.error("Cannot clear wake alarm: coordinator not found")
            return

        try:
            _LOGGER.info("Clearing wake alarm and wake sequence")

            # Use coordinator method (handles clearing, logging, refresh)
            await coordinator.clear_wake_alarm()

            _LOGGER.info("Wake alarm cleared successfully")
        except Exception as err:
            _LOGGER.error("Failed to clear wake alarm: %s", err, exc_info=True)

    # Register all services with Home Assistant
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADJUST_BRIGHTNESS,
        handle_adjust_brightness,
        schema=ADJUST_BRIGHTNESS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADJUST_COLOR_TEMP,
        handle_adjust_color_temp,
        schema=ADJUST_COLOR_TEMP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_MANUAL_ADJUSTMENTS,
        handle_reset_manual_adjustments,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_ALL,
        handle_reset_all,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_MANUAL_CONTROL,
        handle_clear_manual_control,
        schema=CLEAR_MANUAL_CONTROL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MODE,
        handle_set_mode,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_APPLY_SCENE,
        handle_apply_scene,
        schema=APPLY_SCENE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CYCLE_SCENE,
        handle_cycle_scene,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_WAKE_ALARM,
        handle_set_wake_alarm,
        schema=SET_WAKE_ALARM_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_WAKE_ALARM,
        handle_clear_wake_alarm,
        schema=CLEAR_WAKE_ALARM_SCHEMA,
    )

    _LOGGER.info("All ALP services registered successfully")


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister all ALP services.

    Called when the integration is unloaded.

    Args:
        hass: Home Assistant instance
    """
    _LOGGER.info("Unregistering Adaptive Lighting Pro services")

    hass.services.async_remove(DOMAIN, SERVICE_ADJUST_BRIGHTNESS)
    hass.services.async_remove(DOMAIN, SERVICE_ADJUST_COLOR_TEMP)
    hass.services.async_remove(DOMAIN, SERVICE_RESET_MANUAL_ADJUSTMENTS)
    hass.services.async_remove(DOMAIN, SERVICE_RESET_ALL)
    hass.services.async_remove(DOMAIN, SERVICE_CLEAR_MANUAL_CONTROL)
    hass.services.async_remove(DOMAIN, SERVICE_SET_MODE)
    hass.services.async_remove(DOMAIN, SERVICE_APPLY_SCENE)
    hass.services.async_remove(DOMAIN, SERVICE_CYCLE_SCENE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_WAKE_ALARM)
    hass.services.async_remove(DOMAIN, SERVICE_CLEAR_WAKE_ALARM)

    _LOGGER.info("All ALP services unregistered successfully")
