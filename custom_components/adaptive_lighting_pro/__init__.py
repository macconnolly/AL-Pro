"""The Adaptive Lighting Pro integration.

This integration provides sophisticated adaptive lighting control with per-zone
manual overrides, environmental adaptation, and home mode management.

Ported from implementation_1.yaml (3,216 lines) with fixes and enhancements.

Configuration:
- UI Config Flow: Settings → Integrations → Add Integration → Adaptive Lighting Pro
- YAML Config: Add to configuration.yaml:
    adaptive_lighting_pro:
      lux_sensor: sensor.outdoor_illuminance
      weather_entity: weather.home
      zones:
        - zone_id: "zone_name"
          # ... zone config
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, ADAPTIVE_LIGHTING_DOMAIN
from .coordinator import ALPDataUpdateCoordinator
from .services import async_register_services, async_unregister_services
from .integrations.sonos import SonosIntegration
from .integrations.zen32 import Zen32Integration

if TYPE_CHECKING:
    from .coordinator import ALPDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Platforms to be loaded
PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SENSOR,  # Critical sensors for Sonos/Zen32 debugging
    Platform.BUTTON,  # Quick action buttons (Phase 2.4)
    Platform.SELECT,  # Scene selector dropdown (Phase 2.5)
    # Future phases will add:
    # Platform.LIGHT,
]

# YAML Configuration Schema
ZONE_SCHEMA = vol.Schema({
    vol.Required("zone_id"): cv.string,
    vol.Optional("name"): cv.string,
    vol.Required("adaptive_lighting_switch"): cv.entity_id,
    vol.Required("lights"): cv.entity_ids,
    vol.Required("brightness_min"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    vol.Required("brightness_max"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    vol.Optional("color_temp_min"): vol.All(vol.Coerce(int), vol.Range(min=1000, max=10000)),
    vol.Optional("color_temp_max"): vol.All(vol.Coerce(int), vol.Range(min=1000, max=10000)),
    vol.Optional("enabled", default=True): cv.boolean,
    vol.Optional("environmental_enabled", default=True): cv.boolean,
    vol.Optional("sunset_enabled", default=True): cv.boolean,
    vol.Optional("wake_sequence_enabled", default=False): cv.boolean,
    vol.Optional("priority", default=0): vol.Coerce(int),
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional("lux_sensor"): cv.entity_id,
        vol.Optional("weather_entity"): cv.entity_id,
        vol.Optional("environmental_enabled", default=True): cv.boolean,
        vol.Optional("sunset_boost_enabled", default=True): cv.boolean,
        vol.Optional("wake_sequence_enabled", default=False): cv.boolean,
        vol.Optional("wake_target_zone"): cv.string,
        vol.Optional("wake_duration_minutes", default=15): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
        vol.Optional("wake_max_boost_pct", default=20): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("brightness_increment", default=5): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Optional("color_temp_increment", default=500): vol.All(vol.Coerce(int), vol.Range(min=100, max=2000)),
        vol.Optional("manual_control_timeout", default=7200): vol.All(vol.Coerce(int), vol.Range(min=300, max=14400)),
        vol.Optional("zen32_enabled", default=False): cv.boolean,
        vol.Optional("zen32_button_entities"): dict,
        vol.Optional("zen32_button_actions"): dict,
        vol.Optional("zen32_debounce_duration", default=0.5): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
        vol.Required("zones"): vol.All(cv.ensure_list, [ZONE_SCHEMA]),
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up Adaptive Lighting Pro from YAML configuration.

    This function handles YAML configuration by creating a config entry
    via the import source. Home Assistant will then call async_setup_entry.

    Args:
        hass: Home Assistant instance
        config: Configuration dictionary from configuration.yaml

    Returns:
        True if YAML setup initiated successfully
    """
    if DOMAIN not in config:
        # No YAML config, integration will be set up via UI only
        return True

    _LOGGER.info("Found Adaptive Lighting Pro YAML configuration, importing...")

    # Extract our config from the full config
    alp_config = config[DOMAIN]

    # Check if a config entry already exists (avoid duplicate imports)
    existing_entries = hass.config_entries.async_entries(DOMAIN)
    if existing_entries:
        _LOGGER.warning(
            "Adaptive Lighting Pro already configured via UI. "
            "YAML config will be ignored. Remove YAML config or delete UI config entry."
        )
        return True

    # Create a config entry from YAML (import source)
    # This will trigger async_setup_entry with the YAML data
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=alp_config,
        )
    )

    _LOGGER.info("Adaptive Lighting Pro YAML configuration imported successfully")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Lighting Pro from a config entry.

    This is called when the integration is added via the UI config flow.

    Args:
        hass: Home Assistant instance
        entry: Config entry containing zone definitions and settings

    Returns:
        True if setup was successful, False otherwise

    Raises:
        ConfigEntryNotReady: If the Adaptive Lighting integration is not available
    """
    _LOGGER.info("Setting up Adaptive Lighting Pro integration")

    # Verify that Adaptive Lighting integration is loaded
    # This is a required dependency (manifest.json)
    if ADAPTIVE_LIGHTING_DOMAIN not in hass.data:
        _LOGGER.error(
            "Adaptive Lighting integration not found. "
            "Please install and configure it first."
        )
        raise ConfigEntryNotReady(
            "Adaptive Lighting integration must be installed"
        )

    # Initialize the coordinator (main engine)
    # The coordinator polls AL integration state and calculates adjustments
    coordinator = ALPDataUpdateCoordinator(hass, entry)

    # Perform initial data fetch
    # This populates coordinator.data with initial state
    await coordinator.async_config_entry_first_refresh()

    # Initialize coordinator to clean startup state (Phase 1.10)
    # This replaces automation.al_startup_cleanup from YAML
    await coordinator.async_initialize()

    # Store coordinator in hass.data for platform access
    # Pattern: hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator, ...}
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Setup Sonos integration for wake sequence (Phase 2.1)
    # This monitors Sonos alarm sensor and triggers wake sequences
    integrations_config = entry.data.get("integrations", {})
    sonos_enabled = integrations_config.get("sonos_enabled", False)
    sonos_alarm_sensor = integrations_config.get("sonos_alarm_sensor")

    if sonos_enabled and sonos_alarm_sensor:
        _LOGGER.info("Setting up Sonos integration for wake sequence")
        sonos_integration = SonosIntegration(hass, coordinator.wake_sequence)
        sonos_integration.configure(
            enabled=True,
            alarm_sensor=sonos_alarm_sensor,
        )

        # Start monitoring Sonos alarm sensor
        setup_ok = await sonos_integration.async_setup()
        if setup_ok:
            # Store reference for cleanup during unload
            hass.data[DOMAIN][entry.entry_id]["sonos"] = sonos_integration
            _LOGGER.info("Sonos integration setup complete, monitoring %s", sonos_alarm_sensor)
        else:
            _LOGGER.warning(
                "Sonos integration setup failed. Wake sequence will not trigger automatically. "
                "You can still manually trigger wake sequences via services."
            )
    elif sonos_enabled:
        _LOGGER.warning(
            "Sonos integration enabled but no alarm_sensor configured. "
            "Wake sequence will not trigger automatically."
        )

    # Setup Zen32 integration for physical button control (Phase 3.1)
    # This monitors Zen32 event entities and translates button presses to coordinator actions
    zen32_enabled = integrations_config.get("zen32_enabled", False)
    zen32_button_entities = integrations_config.get("zen32_button_entities", {})
    zen32_button_actions = integrations_config.get("zen32_button_actions", {})
    zen32_debounce = integrations_config.get("zen32_debounce_duration", 0.5)

    if zen32_enabled and zen32_button_entities:
        _LOGGER.info("Setting up Zen32 integration for physical button control")
        zen32_integration = Zen32Integration(hass, coordinator)
        zen32_integration.configure(
            enabled=True,
            button_entities=zen32_button_entities,
            button_actions=zen32_button_actions,
            debounce_duration=zen32_debounce,
        )

        # Start monitoring Zen32 button entities
        setup_ok = await zen32_integration.async_setup()
        if setup_ok:
            # Store reference for cleanup during unload
            hass.data[DOMAIN][entry.entry_id]["zen32"] = zen32_integration
            _LOGGER.info(
                "Zen32 integration setup complete, monitoring %d buttons",
                len(zen32_button_entities),
            )
        else:
            _LOGGER.warning(
                "Zen32 integration setup failed. Physical button control will not work. "
                "You can still use services and UI controls."
            )
    elif zen32_enabled:
        _LOGGER.warning(
            "Zen32 integration enabled but no button entities configured. "
            "Physical button control will not work."
        )

    # Register the integration as a device
    # This creates a device entry that all entities will be associated with
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Adaptive Lighting Pro",
        manufacturer="Adaptive Lighting Pro",
        model="ALP v1.0",
        sw_version="1.0.0",
    )

    # Register services (once globally for all instances)
    if DOMAIN not in hass.data or len(hass.data[DOMAIN]) == 1:
        async_register_services(hass)
        _LOGGER.info("Services registered")

    # Forward setup to platforms
    # This creates entities for each platform (currently just switch)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(
        "Adaptive Lighting Pro setup complete with %d zones",
        len(entry.data.get("zones", [])),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    This is called when the integration is removed via the UI.

    Args:
        hass: Home Assistant instance
        entry: Config entry being removed

    Returns:
        True if unload was successful, False otherwise
    """
    _LOGGER.info("Unloading Adaptive Lighting Pro integration")

    # Unload all platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Get data before cleanup
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)

        # Shutdown Sonos integration if it was setup
        if isinstance(entry_data, dict) and "sonos" in entry_data:
            sonos_integration: SonosIntegration = entry_data["sonos"]
            await sonos_integration.async_shutdown()
            _LOGGER.info("Sonos integration shut down")

        # Shutdown Zen32 integration if it was setup
        if isinstance(entry_data, dict) and "zen32" in entry_data:
            zen32_integration: Zen32Integration = entry_data["zen32"]
            await zen32_integration.async_shutdown()
            _LOGGER.info("Zen32 integration shut down")

        # Get coordinator from the dict
        if isinstance(entry_data, dict) and "coordinator" in entry_data:
            coordinator = entry_data["coordinator"]
        else:
            # Fallback for old storage pattern (coordinator stored directly)
            coordinator = entry_data

        # Stop the coordinator update loop
        if hasattr(coordinator, "async_shutdown"):
            await coordinator.async_shutdown()

        # If this was the last instance, remove the domain key and unregister services
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            async_unregister_services(hass)
            _LOGGER.info("Services unregistered")

        _LOGGER.info("Adaptive Lighting Pro unloaded successfully")
    else:
        _LOGGER.error("Failed to unload Adaptive Lighting Pro platforms")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry.

    This is called when the integration configuration is updated via options flow.

    Args:
        hass: Home Assistant instance
        entry: Config entry being reloaded
    """
    _LOGGER.info("Reloading Adaptive Lighting Pro integration")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
