"""Config flow for Adaptive Lighting Pro integration.

This module implements the UI-based configuration flow for setting up
Adaptive Lighting Pro zones, profiles, and integration settings.

Flow Steps:
1. User step: Initial setup with integration name
2. Zone definition loop (1-5 zones):
   - Zone ID, name, lights, and AL switch selection
   - Brightness and color temperature profile
3. Global settings: Increments and timeouts
4. Environmental settings: Lux sensor, weather, boost config
5. Integrations: Sonos and Zen32 optional features

The flow validates:
- Adaptive Lighting integration presence
- Entity existence (lights, switches, sensors)
- Valid brightness/color temp ranges
- Unique zone IDs
"""
from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er, selector

from .const import (
    ADAPTIVE_LIGHTING_DOMAIN,
    BRIGHTNESS_INCREMENT_MAX,
    BRIGHTNESS_INCREMENT_MIN,
    BRIGHTNESS_INCREMENT_STEP,
    COLOR_TEMP_INCREMENT_MAX,
    COLOR_TEMP_INCREMENT_MIN,
    COLOR_TEMP_INCREMENT_STEP,
    CONF_ADAPT_DELAY,
    CONF_ADAPTIVE_LIGHTING_SWITCH,
    CONF_BRIGHTNESS_INCREMENT,
    CONF_BRIGHTNESS_MAX,
    CONF_BRIGHTNESS_MIN,
    CONF_COLOR_TEMP_INCREMENT,
    CONF_COLOR_TEMP_MAX,
    CONF_COLOR_TEMP_MIN,
    CONF_ENVIRONMENTAL_ENABLED,
    CONF_GENERAL_TRANSITION_SPEED,
    CONF_INTERVAL,
    CONF_LUX_SENSOR,
    CONF_MANUAL_CONTROL_TIMEOUT,
    CONF_MANUAL_TIMER_DURATION,
    CONF_MAX_BOOST,
    CONF_SLEEP_BRIGHTNESS,
    CONF_SLEEP_COLOR_TEMP,
    CONF_SONOS_ALARM_SENSOR,
    CONF_SONOS_BEDROOM_OFFSET,
    CONF_SONOS_ENABLED,
    CONF_SONOS_KITCHEN_OFFSET,
    CONF_WAKE_SEQUENCE_ENABLED,
    CONF_WAKE_SEQUENCE_TARGET_ZONE,
    CONF_WAKE_SEQUENCE_DURATION,
    CONF_WAKE_SEQUENCE_MAX_BOOST,
    CONF_SUNSET_FADE_ENABLED,
    CONF_WEATHER_ENTITY,
    CONF_ZEN32_DEBOUNCE,
    CONF_ZEN32_ENABLED,
    CONF_ZEN32_EVENT_ENTITY,
    CONF_ZONE_ID,
    CONF_ZONE_LIGHTS,
    CONF_ZONE_NAME,
    CONF_ZONES,
    DEFAULT_BRIGHTNESS_INCREMENT,
    DEFAULT_COLOR_TEMP_INCREMENT,
    DEFAULT_MANUAL_TIMEOUT_SECONDS,
    DEFAULT_TRANSITION_SPEED,
    DOMAIN,
    MAX_ENVIRONMENTAL_BOOST,
    ZEN32_DEBOUNCE_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

# Maximum number of zones allowed (Phase 1)
MAX_ZONES = 5
MIN_ZONES = 1

# Regex pattern for valid zone IDs (slug format)
ZONE_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


def validate_zone_id(zone_id: str) -> bool:
    """Validate that zone_id is a valid slug.

    Args:
        zone_id: The zone ID to validate

    Returns:
        True if valid, False otherwise
    """
    return bool(ZONE_ID_PATTERN.match(zone_id))


async def validate_adaptive_lighting(hass: HomeAssistant) -> bool:
    """Verify that Adaptive Lighting integration is installed and loaded.

    Args:
        hass: Home Assistant instance

    Returns:
        True if AL is available, False otherwise
    """
    return ADAPTIVE_LIGHTING_DOMAIN in hass.data


async def validate_entity_exists(
    hass: HomeAssistant, entity_id: str
) -> bool:
    """Verify that an entity exists in Home Assistant.

    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to verify

    Returns:
        True if entity exists, False otherwise
    """
    entity_registry = er.async_get(hass)
    return entity_registry.async_get(entity_id) is not None


async def validate_entities_exist(
    hass: HomeAssistant, entity_ids: list[str]
) -> tuple[bool, str | None]:
    """Verify that multiple entities exist.

    Args:
        hass: Home Assistant instance
        entity_ids: List of entity IDs to verify

    Returns:
        Tuple of (all_valid, first_missing_entity_id)
    """
    for entity_id in entity_ids:
        if not await validate_entity_exists(hass, entity_id):
            return False, entity_id
    return True, None


class AdaptiveLightingProConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Lighting Pro.

    This flow guides the user through:
    1. Initial setup
    2. Zone configuration (1-5 zones)
    3. Global settings
    4. Environmental settings
    5. Integration settings
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._zones: list[dict[str, Any]] = []
        self._current_zone_index: int = 0
        self._zone_in_progress: dict[str, Any] = {}
        self._global_settings: dict[str, Any] = {}
        self._environmental_settings: dict[str, Any] = {}
        self._integration_settings: dict[str, Any] = {}
        self._name: str = "Adaptive Lighting Pro"

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle import from YAML configuration.

        This is called when configuration is provided in configuration.yaml
        via the adaptive_lighting_pro: section.

        Args:
            import_data: Configuration from YAML

        Returns:
            FlowResult creating the config entry
        """
        _LOGGER.info("Importing Adaptive Lighting Pro configuration from YAML")

        # Check if already configured (prevent duplicates)
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        # Validate Adaptive Lighting integration is present
        if not await validate_adaptive_lighting(self.hass):
            _LOGGER.error("Cannot import YAML config: Adaptive Lighting integration not found")
            return self.async_abort(reason="adaptive_lighting_not_found")

        # Create config entry directly from YAML data
        # The data format from YAML matches what async_step_finalize expects
        return self.async_create_entry(
            title="Adaptive Lighting Pro (YAML)",
            data=import_data,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - gather integration name.

        Args:
            user_input: User-provided data or None for initial display

        Returns:
            FlowResult to show form or proceed to next step
        """
        errors: dict[str, str] = {}

        # Check if already configured (single instance only)
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            # Validate Adaptive Lighting integration is present
            if not await validate_adaptive_lighting(self.hass):
                errors["base"] = "adaptive_lighting_not_found"
            else:
                self._name = user_input.get(CONF_NAME, "Adaptive Lighting Pro")
                return await self.async_step_zones()

        # Show initial form
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default="Adaptive Lighting Pro"
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={},
        )

    async def async_step_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle zone definition step.

        This step collects zone ID, name, lights, and AL switch.
        It loops to allow configuring multiple zones (up to MAX_ZONES).

        Args:
            user_input: User-provided data or None for initial display

        Returns:
            FlowResult to show form, proceed to zone profile, or finish zones
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate zone ID format
            zone_id = user_input[CONF_ZONE_ID]
            if not validate_zone_id(zone_id):
                errors["base"] = "invalid_zone_id"
            # Check for duplicate zone IDs
            elif any(z[CONF_ZONE_ID] == zone_id for z in self._zones):
                errors["base"] = "zone_id_exists"
            else:
                # Validate lights exist
                lights = user_input[CONF_ZONE_LIGHTS]
                if not lights:
                    errors["base"] = "no_lights_selected"
                else:
                    all_valid, missing = await validate_entities_exist(
                        self.hass, lights
                    )
                    if not all_valid:
                        errors["base"] = "entity_not_found"
                        errors["entity_id"] = missing or "unknown"
                    else:
                        # Validate AL switch exists
                        al_switch = user_input[CONF_ADAPTIVE_LIGHTING_SWITCH]
                        if not await validate_entity_exists(self.hass, al_switch):
                            errors["base"] = "switch_not_found"
                        else:
                            # Store zone data and move to profile configuration
                            self._zone_in_progress = user_input
                            return await self.async_step_zone_profile()

        # Build schema for zone definition
        # Get all light entities for multi-select
        entity_registry = er.async_get(self.hass)
        light_entities = [
            entry.entity_id
            for entry in entity_registry.entities.values()
            if entry.domain == "light"
        ]

        # Get all AL switches
        al_switches = [
            entry.entity_id
            for entry in entity_registry.entities.values()
            if entry.domain == "switch"
            and entry.entity_id.startswith("switch.adaptive_lighting_")
        ]

        zone_num = self._current_zone_index + 1
        schema = vol.Schema(
            {
                vol.Required(CONF_ZONE_ID): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT
                    )
                ),
                vol.Required(CONF_ZONE_NAME): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT
                    )
                ),
                vol.Required(CONF_ZONE_LIGHTS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="light",
                        multiple=True,
                    )
                ),
                vol.Required(CONF_ADAPTIVE_LIGHTING_SWITCH): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="switch",
                        multiple=False,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="zones",
            data_schema=schema,
            errors=errors,
            description_placeholders={"zone_name": f"Zone {zone_num}"},
        )

    async def async_step_zone_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle zone profile configuration step.

        This step collects brightness/color temp ranges and timers.

        Args:
            user_input: User-provided data or None for initial display

        Returns:
            FlowResult to show form or proceed to next zone/step
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate brightness range
            brightness_min = user_input.get(CONF_BRIGHTNESS_MIN, 1)
            brightness_max = user_input.get(CONF_BRIGHTNESS_MAX, 100)
            if brightness_min >= brightness_max:
                errors["base"] = "invalid_brightness_range"

            # Validate color temp range (only if not brightness-only)
            brightness_only = user_input.get("brightness_only", False)
            if not brightness_only:
                color_temp_min = user_input.get(CONF_COLOR_TEMP_MIN, 2000)
                color_temp_max = user_input.get(CONF_COLOR_TEMP_MAX, 5000)
                if color_temp_min >= color_temp_max:
                    errors["base"] = "invalid_color_temp_range"

            if not errors:
                # Merge zone definition with profile
                zone_config = {**self._zone_in_progress, **user_input}
                self._zones.append(zone_config)
                self._zone_in_progress = {}
                self._current_zone_index += 1

                # Check if we should add another zone or move to global settings
                if self._current_zone_index < MAX_ZONES:
                    # Ask if user wants to add another zone
                    return await self.async_step_add_another_zone()
                else:
                    # Max zones reached, move to global settings
                    return await self.async_step_global_settings()

        # Build schema for zone profile
        zone_name = self._zone_in_progress.get(CONF_ZONE_NAME, "Zone")
        schema = vol.Schema(
            {
                vol.Required(CONF_BRIGHTNESS_MIN, default=20): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(CONF_BRIGHTNESS_MAX, default=100): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                vol.Optional(CONF_SLEEP_BRIGHTNESS, default=5): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                vol.Optional("brightness_only", default=False): selector.BooleanSelector(),
                vol.Optional(CONF_COLOR_TEMP_MIN, default=2000): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1000,
                        max=10000,
                        step=50,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="K",
                    )
                ),
                vol.Optional(CONF_COLOR_TEMP_MAX, default=5000): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1000,
                        max=10000,
                        step=50,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="K",
                    )
                ),
                vol.Optional(CONF_SLEEP_COLOR_TEMP, default=2000): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1000,
                        max=10000,
                        step=50,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="K",
                    )
                ),
                vol.Optional(
                    CONF_MANUAL_TIMER_DURATION, default=DEFAULT_MANUAL_TIMEOUT_SECONDS
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=60,
                        max=28800,  # 8 hours
                        step=60,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(CONF_INTERVAL, default=20): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5,
                        max=300,
                        step=5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(CONF_ADAPT_DELAY, default=0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=60,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="zone_profile",
            data_schema=schema,
            errors=errors,
            description_placeholders={"zone_name": zone_name},
        )

    async def async_step_add_another_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask user if they want to add another zone.

        Args:
            user_input: User selection or None for initial display

        Returns:
            FlowResult to add another zone or proceed to global settings
        """
        if user_input is not None:
            if user_input.get("add_another", False):
                return await self.async_step_zones()
            else:
                return await self.async_step_global_settings()

        # Show form asking if user wants another zone
        schema = vol.Schema(
            {
                vol.Required("add_another", default=False): selector.BooleanSelector(),
            }
        )

        zones_configured = len(self._zones)
        zones_remaining = MAX_ZONES - zones_configured

        return self.async_show_form(
            step_id="add_another_zone",
            data_schema=schema,
            description_placeholders={
                "zones_configured": str(zones_configured),
                "zones_remaining": str(zones_remaining),
            },
        )

    async def async_step_global_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle global settings configuration.

        This step collects adjustment increments and default timeouts.

        Args:
            user_input: User-provided data or None for initial display

        Returns:
            FlowResult to show form or proceed to environmental settings
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            self._global_settings = user_input
            return await self.async_step_environmental()

        # Build schema for global settings
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BRIGHTNESS_INCREMENT, default=DEFAULT_BRIGHTNESS_INCREMENT
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=BRIGHTNESS_INCREMENT_MIN,
                        max=BRIGHTNESS_INCREMENT_MAX,
                        step=BRIGHTNESS_INCREMENT_STEP,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(
                    CONF_COLOR_TEMP_INCREMENT, default=DEFAULT_COLOR_TEMP_INCREMENT
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=COLOR_TEMP_INCREMENT_MIN,
                        max=COLOR_TEMP_INCREMENT_MAX,
                        step=COLOR_TEMP_INCREMENT_STEP,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="K",
                    )
                ),
                vol.Required(
                    CONF_MANUAL_CONTROL_TIMEOUT, default=DEFAULT_MANUAL_TIMEOUT_SECONDS
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=60,
                        max=28800,  # 8 hours
                        step=60,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Required(
                    CONF_GENERAL_TRANSITION_SPEED, default=DEFAULT_TRANSITION_SPEED
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=10.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="global_settings",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_environmental(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle environmental settings configuration.

        This step collects lux sensor, weather entity, and boost settings.

        Args:
            user_input: User-provided data or None for initial display

        Returns:
            FlowResult to show form or proceed to integrations
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate entities if environmental is enabled
            if user_input.get(CONF_ENVIRONMENTAL_ENABLED, False):
                lux_sensor = user_input.get(CONF_LUX_SENSOR)
                weather_entity = user_input.get(CONF_WEATHER_ENTITY)

                # Validate lux sensor if provided
                if lux_sensor and not await validate_entity_exists(
                    self.hass, lux_sensor
                ):
                    errors["base"] = "entity_not_found"
                    errors["entity_id"] = lux_sensor

                # Validate weather entity if provided
                if weather_entity and not await validate_entity_exists(
                    self.hass, weather_entity
                ):
                    errors["base"] = "entity_not_found"
                    errors["entity_id"] = weather_entity

            if not errors:
                self._environmental_settings = user_input
                return await self.async_step_integrations()

        # Build schema for environmental settings
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENVIRONMENTAL_ENABLED, default=False
                ): selector.BooleanSelector(),
                vol.Optional(CONF_LUX_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        multiple=False,
                    )
                ),
                vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="weather",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_MAX_BOOST, default=MAX_ENVIRONMENTAL_BOOST
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100,
                        step=5,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                vol.Optional(
                    CONF_SUNSET_FADE_ENABLED, default=False
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="environmental",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_integrations(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle integration settings (Sonos, Zen32).

        This is the final configuration step.

        Args:
            user_input: User-provided data or None for initial display

        Returns:
            FlowResult to show form or create config entry
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate Sonos entities if enabled
            if user_input.get(CONF_SONOS_ENABLED, False):
                sonos_sensor = user_input.get(CONF_SONOS_ALARM_SENSOR)
                if sonos_sensor and not await validate_entity_exists(
                    self.hass, sonos_sensor
                ):
                    errors["base"] = "entity_not_found"
                    errors["entity_id"] = sonos_sensor

            # Validate Zen32 entity if enabled
            if user_input.get(CONF_ZEN32_ENABLED, False):
                zen32_entity = user_input.get(CONF_ZEN32_EVENT_ENTITY)
                if zen32_entity and not await validate_entity_exists(
                    self.hass, zen32_entity
                ):
                    errors["base"] = "entity_not_found"
                    errors["entity_id"] = zen32_entity

            if not errors:
                self._integration_settings = user_input
                # All steps complete, create config entry
                return await self._create_entry()

        # Build schema for integration settings
        schema = vol.Schema(
            {
                vol.Optional(CONF_SONOS_ENABLED, default=False): selector.BooleanSelector(),
                vol.Optional(CONF_SONOS_ALARM_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        multiple=False,
                    )
                ),
                # Wake Sequence Settings (replaces old sunrise offset approach)
                vol.Optional(CONF_WAKE_SEQUENCE_ENABLED, default=True): selector.BooleanSelector(),
                vol.Optional(CONF_WAKE_SEQUENCE_TARGET_ZONE, default="bedroom"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_WAKE_SEQUENCE_DURATION, default=900): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=300,
                        max=1800,
                        step=60,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(CONF_WAKE_SEQUENCE_MAX_BOOST, default=20): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5,
                        max=50,
                        step=5,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                # DEPRECATED: Old sunrise offset approach (kept for backward compatibility)
                vol.Optional(
                    CONF_SONOS_BEDROOM_OFFSET, default=-1800
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-7200,
                        max=0,
                        step=60,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(
                    CONF_SONOS_KITCHEN_OFFSET, default=-2700
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-7200,
                        max=0,
                        step=60,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(CONF_ZEN32_ENABLED, default=False): selector.BooleanSelector(),
                vol.Optional(CONF_ZEN32_EVENT_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="event",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_ZEN32_DEBOUNCE, default=ZEN32_DEBOUNCE_SECONDS
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=5.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="integrations",
            data_schema=schema,
            errors=errors,
        )

    async def _create_entry(self) -> FlowResult:
        """Create the config entry with all collected data.

        Returns:
            FlowResult creating the config entry
        """
        # Combine all configuration data with nested structure for coordinator
        data = {
            CONF_NAME: self._name,
            CONF_ZONES: self._zones,
            "global_settings": self._global_settings,
            "environmental": self._environmental_settings,
            "integrations": self._integration_settings,
        }

        _LOGGER.info(
            "Creating Adaptive Lighting Pro config entry with %d zones",
            len(self._zones),
        )

        return self.async_create_entry(
            title=self._name,
            data=data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler.

        Args:
            config_entry: The config entry being configured

        Returns:
            OptionsFlowHandler instance
        """
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Adaptive Lighting Pro.

    Phase 1: Only allow reconfiguring global settings.
    Future phases will allow zone management.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow.

        Args:
            config_entry: The config entry being configured
        """
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options for global settings.

        Phase 1: Only global settings can be changed.
        Zones cannot be added/removed/modified via options flow.

        Args:
            user_input: User-provided data or None for initial display

        Returns:
            FlowResult to show form or update config entry
        """
        if user_input is not None:
            # Update the config entry with new settings
            # We need to merge with existing data to preserve zones
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
            )
            # Trigger reload to apply new settings
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Get current values from config entry
        current_data = self.config_entry.data

        # Build schema with current values as defaults
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BRIGHTNESS_INCREMENT,
                    default=current_data.get(
                        CONF_BRIGHTNESS_INCREMENT, DEFAULT_BRIGHTNESS_INCREMENT
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=BRIGHTNESS_INCREMENT_MIN,
                        max=BRIGHTNESS_INCREMENT_MAX,
                        step=BRIGHTNESS_INCREMENT_STEP,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(
                    CONF_COLOR_TEMP_INCREMENT,
                    default=current_data.get(
                        CONF_COLOR_TEMP_INCREMENT, DEFAULT_COLOR_TEMP_INCREMENT
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=COLOR_TEMP_INCREMENT_MIN,
                        max=COLOR_TEMP_INCREMENT_MAX,
                        step=COLOR_TEMP_INCREMENT_STEP,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="K",
                    )
                ),
                vol.Required(
                    CONF_MANUAL_CONTROL_TIMEOUT,
                    default=current_data.get(
                        CONF_MANUAL_CONTROL_TIMEOUT, DEFAULT_MANUAL_TIMEOUT_SECONDS
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=60,
                        max=28800,
                        step=60,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Required(
                    CONF_GENERAL_TRANSITION_SPEED,
                    default=current_data.get(
                        CONF_GENERAL_TRANSITION_SPEED, DEFAULT_TRANSITION_SPEED
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=10.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
