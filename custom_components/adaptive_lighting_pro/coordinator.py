"""Data Update Coordinator for Adaptive Lighting Pro.

This module implements the central coordination engine for the Adaptive Lighting Pro
integration. The coordinator manages state updates, zone synchronization, and
orchestrates all lighting calculations.

Phase 2 Implementation:
- Full polling of Adaptive Lighting integration switches
- Asymmetric boundary adjustment application to zones
- Zone timer management with expiry detection
- Manual control state tracking per zone
- Event firing for calculation completion
- Integration with ZoneManager and AdjustmentEngine
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .adjustment_engine import apply_adjustment_to_zone
from .const import (
    ADAPTIVE_LIGHTING_DOMAIN,
    BRIGHTNESS_INCREMENT_MAX,
    BRIGHTNESS_INCREMENT_MIN,
    COLOR_TEMP_INCREMENT_MAX,
    COLOR_TEMP_INCREMENT_MIN,
    CONF_BRIGHTNESS_INCREMENT,
    CONF_BRIGHTNESS_MAX,
    CONF_BRIGHTNESS_MIN,
    CONF_COLOR_TEMP_INCREMENT,
    CONF_COLOR_TEMP_MAX,
    CONF_COLOR_TEMP_MIN,
    CONF_MANUAL_CONTROL_TIMEOUT,
    COORDINATOR_UPDATE_INTERVAL,
    DEFAULT_BRIGHTNESS_INCREMENT,
    DEFAULT_COLOR_TEMP_INCREMENT,
    DEFAULT_MANUAL_TIMEOUT_SECONDS,
    DOMAIN,
    EVENT_CALCULATION_COMPLETE,
    MANUAL_TIMEOUT_MAX,
    MANUAL_TIMEOUT_MIN,
    SCENE_CONFIGS,
    SCENE_PRESETS,
    Scene,
)
from .features.environmental import EnvironmentalAdapter
from .features.sunset_boost import SunsetBoostCalculator
from .features.wake_sequence import WakeSequenceCalculator
from .features.zone_manager import ZoneManager
from .features.manual_control import ManualControlDetector

_LOGGER = logging.getLogger(__name__)


class ALPDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for managing Adaptive Lighting Pro state updates.

    This coordinator serves as the central engine for ALP, replacing the
    adaptive_lighting_core_engine_v2 automation from the original YAML package.

    Responsibilities:
    - Poll Home Assistant Adaptive Lighting integration state (30s interval)
    - Maintain coordinator state structure for zones, global settings,
      environmental data, and integrations
    - Apply asymmetric boundary adjustments to zones not in manual control
    - Manage manual control timers through ZoneManager
    - Trigger updates to all platform entities
    - Fire events for external automation

    Phase 2: Full implementation with manual adjustments and asymmetric boundaries
    Future Phases:
    - Phase 3: Environmental boost and sunset fade
    - Phase 4: Mode system integration
    - Phase 6: Sonos and Zen32 integration

    Attributes:
        hass: Home Assistant instance
        config_entry: Configuration entry for this integration instance
        zones: Dictionary of zone IDs to zone configuration
        zone_manager: Manager for zone state and timers
        update_interval: How often to poll for updates (30 seconds)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: Any,  # ConfigEntry type from HA core
    ) -> None:
        """Initialize the ALP coordinator.

        Args:
            hass: Home Assistant instance
            config_entry: Configuration entry containing zone and settings data
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=COORDINATOR_UPDATE_INTERVAL),
        )

        self.config_entry = config_entry
        self.zones: dict[str, dict[str, Any]] = {}

        # Initialize manual control detector (for smart timeout)
        self._manual_detector = ManualControlDetector(hass)

        # Initialize ZoneManager for timer and manual control tracking
        self.zone_manager = ZoneManager(hass, config_entry, self._manual_detector, coordinator=self)

        # Initialize environmental features
        self._env_adapter = EnvironmentalAdapter(hass)
        self._sunset_boost = SunsetBoostCalculator(hass)
        self._wake_sequence = WakeSequenceCalculator(hass)

        # Extract zone configuration from config entry
        zones_config = config_entry.data.get("zones", [])
        for zone in zones_config:
            zone_id = zone.get("id", zone.get("zone_id", ""))
            if zone_id:
                self.zones[zone_id] = zone

        # Configure environmental features
        environmental_config = config_entry.data.get("environmental", {})
        lux_sensor = environmental_config.get("lux_sensor")
        weather_entity = environmental_config.get("weather_entity")
        env_enabled = environmental_config.get("enabled", True)
        sunset_enabled = environmental_config.get("sunset_boost_enabled", True)

        if lux_sensor and weather_entity:
            self._env_adapter.configure(
                lux_sensor=lux_sensor,
                weather_entity=weather_entity,
                enabled=env_enabled,
            )
            self._sunset_boost.configure(enabled=sunset_enabled)
            _LOGGER.info(
                "Environmental features configured: lux=%s, weather=%s, env_enabled=%s, sunset_enabled=%s",
                lux_sensor,
                weather_entity,
                env_enabled,
                sunset_enabled,
            )
        else:
            _LOGGER.warning(
                "Environmental features not configured (lux_sensor=%s, weather_entity=%s)",
                lux_sensor,
                weather_entity,
            )

        # Configure wake sequence (Phase 2.1)
        integrations_config = config_entry.data.get("integrations", {})
        wake_enabled = integrations_config.get("wake_sequence_enabled", True)  # Default True
        wake_target_zone = integrations_config.get("wake_sequence_target_zone", "bedroom")
        wake_duration = integrations_config.get("wake_sequence_duration", 900)
        wake_max_boost = integrations_config.get("wake_sequence_max_boost", 20)

        self._wake_sequence.configure(
            enabled=wake_enabled,
            target_zone=wake_target_zone,
            duration_seconds=wake_duration,
            max_boost_pct=wake_max_boost,
        )

        _LOGGER.info(
            "Wake sequence configured: enabled=%s, target_zone=%s, duration=%ds, max_boost=%d%%",
            wake_enabled,
            wake_target_zone,
            wake_duration,
            wake_max_boost,
        )

        # Extract global settings with defaults
        global_settings = config_entry.data.get("global_settings", {})
        self._brightness_increment = global_settings.get(
            CONF_BRIGHTNESS_INCREMENT, DEFAULT_BRIGHTNESS_INCREMENT
        )
        self._color_temp_increment = global_settings.get(
            CONF_COLOR_TEMP_INCREMENT, DEFAULT_COLOR_TEMP_INCREMENT
        )
        self._manual_control_timeout = global_settings.get(
            CONF_MANUAL_CONTROL_TIMEOUT, DEFAULT_MANUAL_TIMEOUT_SECONDS
        )

        # Store current adjustment values
        self._brightness_adjustment = 0
        self._warmth_adjustment = 0
        self._current_scene = Scene.DEFAULT
        self._scene_index = 0
        self._scene_list = list(SCENE_CONFIGS.keys())

        # Phase 1.8: Track scene offsets for sensor display
        self._scene_brightness_offset = 0
        self._scene_warmth_offset = 0

        # Phase 1.8: Track last calculated boosts for sensors
        self._last_env_boost = 0
        self._last_sunset_boost = 0
        self._last_wake_boost = 0

        _LOGGER.info(
            "ALP Coordinator initialized with %d zones: %s",
            len(self.zones),
            ", ".join(self.zones.keys()) if self.zones else "none"
        )
        _LOGGER.debug(
            "Global settings: brightness_increment=%d%%, color_temp_increment=%dK, timeout=%ds",
            self._brightness_increment,
            self._color_temp_increment,
            self._manual_control_timeout,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Home Assistant Adaptive Lighting integration.

        This method is called every COORDINATOR_UPDATE_INTERVAL seconds (30s).

        Phase 2 Implementation:
        1. Check for expired timers and restore adaptive control
        2. Poll AL integration switches for each zone
        3. Extract manual control state and current lighting values
        4. Apply asymmetric boundary adjustments to non-manual zones
        5. Build comprehensive state structure
        6. Fire calculation complete event

        Returns:
            Dictionary containing coordinator state with keys:
            - zones: Per-zone state (manual control, timers, current values)
            - global: Global settings (pause state, mode, adjustments)
            - environmental: Environmental data (boost, sunset fade)
            - integrations: External integration state (Sonos, Zen32)

        Raises:
            UpdateFailed: If critical update operations fail
        """
        try:
            # Step 1: Check for expired timers
            expired_zones = await self.zone_manager.async_update_timers()
            for zone_id in expired_zones:
                _LOGGER.info("Timer expired for zone %s, restoring adaptive control", zone_id)
                await self._restore_adaptive_control(zone_id)

            # Calculate environmental features
            env_boost = self._env_adapter.calculate_boost()
            lux = self._get_current_lux()
            sunset_boost = self._sunset_boost.calculate_boost(lux)

            # Initialize state structure
            state: dict[str, Any] = {
                "zones": {},
                "global": {
                    "paused": False,
                    "current_mode": "default",
                    "total_brightness_adjustment": self._brightness_adjustment,
                    "total_warmth_adjustment": self._warmth_adjustment,
                    "brightness_increment": self._brightness_increment,
                    "color_temp_increment": self._color_temp_increment,
                    "manual_control_timeout": self._manual_control_timeout,
                    # Phase 1.8: Scene offset tracking for sensors
                    "scene_brightness_offset": self._scene_brightness_offset,
                    "scene_warmth_offset": self._scene_warmth_offset,
                    "current_scene": self._current_scene.value if self._current_scene else "default",
                },
                "environmental": {
                    "boost_active": env_boost > 0,
                    "current_boost_pct": env_boost,
                    "sunset_boost_active": sunset_boost > 0,
                    "sunset_boost_offset": sunset_boost,
                    "current_lux": lux,
                    # Phase 1.8: Store last calculated boosts
                    "last_env_boost": self._last_env_boost,
                    "last_sunset_boost": self._last_sunset_boost,
                    # Phase 2.1: Store wake sequence boost
                    "wake_boost_active": self._last_wake_boost > 0,
                    "wake_boost_pct": self._last_wake_boost,
                },
                "wake_sequence": self._wake_sequence.get_state_dict(),
                "integrations": {
                    "sonos_next_sunrise": None,
                    "zen32_last_scene": None,
                },
            }

            # Step 2 & 3: Poll AL integration switches for each zone
            for zone_id, zone_config in self.zones.items():
                al_switch = zone_config.get("adaptive_lighting_switch")
                if not al_switch:
                    _LOGGER.debug("Zone %s missing adaptive_lighting_switch, skipping", zone_id)
                    state["zones"][zone_id] = self._get_default_zone_state(zone_id)
                    continue

                # Phase 1.11: Check if switch is in unavailable list from health check
                switch_health = state["global"].get("switch_health", {})
                unavailable_switches = switch_health.get("unavailable", [])
                if al_switch in unavailable_switches or f"{al_switch} (missing manual_control)" in unavailable_switches:
                    _LOGGER.debug(
                        "Zone %s has unavailable AL switch %s, skipping",
                        zone_id,
                        al_switch,
                    )
                    state["zones"][zone_id] = self._get_default_zone_state(zone_id)
                    continue

                # Get AL switch state
                al_state = self.hass.states.get(al_switch)
                if not al_state:
                    _LOGGER.debug(
                        "AL switch %s not found for zone %s, skipping",
                        al_switch,
                        zone_id,
                    )
                    state["zones"][zone_id] = self._get_default_zone_state(zone_id)
                    continue

                # Extract manual control from AL integration
                # The AL integration tracks manual_control in its attributes
                al_manual_control = al_state.attributes.get("manual_control", False)

                # Get timer info from zone manager
                timer_info = self.zone_manager.get_zone_timer_info(zone_id)

                # Extract current lighting values from AL switch attributes
                current_brightness_pct = al_state.attributes.get("brightness_pct", 0)
                current_color_temp = al_state.attributes.get("color_temp_kelvin", 0)

                # Count lights that are on in this zone
                lights_on_count = self._count_lights_on(zone_config.get("lights", []))

                # Build zone state
                state["zones"][zone_id] = {
                    "manual_control_active": timer_info.get("manual_control_active", False),
                    "timer_remaining": timer_info.get("timer_remaining_seconds", 0),
                    "current_brightness_pct": current_brightness_pct,
                    "current_color_temp": current_color_temp,
                    "lights_on_count": lights_on_count,
                    "adaptive_lighting_active": al_state.state == "on",
                    "al_manual_control": al_manual_control,  # From AL integration
                    # Phase 1.8: Include computed boundaries if available
                    "computed_brightness_range": self._computed_boundaries.get(zone_id, {}) if hasattr(self, '_computed_boundaries') else {},
                }

                # Step 4: Apply asymmetric boundary adjustments if NOT in manual control
                if not self.zone_manager.is_manual_control_active(zone_id):
                    await self._apply_adjustments_to_zone(zone_id, zone_config)
                else:
                    _LOGGER.debug(
                        "Skipping adjustment for zone %s (manual control active)",
                        zone_id,
                    )

            # Step 5: Calculate health score
            health_score, health_status = self._calculate_health_score(state)
            state["global"]["health_score"] = health_score
            state["global"]["health_status"] = health_status

            _LOGGER.debug(
                "Coordinator update complete - zones: %s, mode: %s, adjustments: brightness=%d%%, warmth=%dK, health: %s",
                len(state["zones"]),
                state["global"]["current_mode"],
                self._brightness_adjustment,
                self._warmth_adjustment,
                health_status,
            )

            # Step 6: Fire enhanced calculation complete event
            self.hass.bus.async_fire(
                EVENT_CALCULATION_COMPLETE,
                {
                    "timestamp": dt_util.now().isoformat(),
                    "trigger_source": "coordinator_update",
                    "zones": list(state["zones"].keys()),
                    "final_brightness_adjustment": self._brightness_adjustment + env_boost + sunset_boost,
                    "final_warmth_adjustment": self._warmth_adjustment,
                    "components": {
                        "brightness_manual": self._brightness_adjustment,
                        "brightness_environmental": env_boost,
                        "brightness_sunset": sunset_boost,
                        "warmth_manual": self._warmth_adjustment,
                    },
                    "sun_elevation": self.hass.states.get("sun.sun").attributes.get("elevation", 0) if self.hass.states.get("sun.sun") else 0,
                    "environmental_active": env_boost > 0,
                    "zones_updated": list(state["zones"].keys()),
                    "expired_timers": expired_zones,
                    "health_score": health_score,
                    "health_status": health_status,
                },
            )

            return state

        except Exception as err:
            _LOGGER.error("Error updating ALP coordinator: %s", err, exc_info=True)
            raise UpdateFailed(f"Error communicating with coordinator: {err}") from err

    async def _apply_adjustments_to_zone(
        self, zone_id: str, zone_config: dict[str, Any]
    ) -> None:
        """Apply asymmetric boundary adjustments to a zone.

        Calculates adjusted boundaries and calls AL integration service to update.
        Combines environmental boost, sunset boost, and manual adjustments.

        Args:
            zone_id: Zone identifier
            zone_config: Zone configuration dictionary
        """
        # Check if zone is enabled
        if not zone_config.get("enabled", True):
            _LOGGER.debug("Zone %s is disabled, skipping adjustments", zone_id)
            return

        # Calculate environmental features (check per-zone flags)
        env_boost = 0
        sunset_boost = 0
        wake_boost = 0

        # Phase 2.5: Calculate environmental boost with detailed breakdown
        env_breakdown = {}
        sunset_breakdown = {}
        if zone_config.get("environmental_enabled", True):
            env_boost, env_breakdown = self._env_adapter.calculate_boost()

        if zone_config.get("sunset_enabled", True):
            lux = self._get_current_lux()
            sunset_boost, sunset_breakdown = self._sunset_boost.calculate_boost(lux)

        # Phase 2.1: Calculate wake sequence boost (per-zone, only affects target zone)
        if zone_config.get("wake_sequence_enabled", True):
            wake_boost = self._wake_sequence.calculate_boost(zone_id)

        # Phase 1.8: Track last calculated boosts for sensor access
        self._last_env_boost = env_boost
        self._last_sunset_boost = sunset_boost
        self._last_wake_boost = wake_boost

        # Phase 2.5: Store environmental and sunset breakdowns for sensors
        if not hasattr(self, '_env_breakdown'):
            self._env_breakdown = {}
        if not hasattr(self, '_sunset_breakdown'):
            self._sunset_breakdown = {}
        self._env_breakdown = env_breakdown
        self._sunset_breakdown = sunset_breakdown

        # Combine all offsets with intelligent capping
        # Layer all 5 brightness components: env + sunset + wake + manual + scene
        raw_brightness_boost = (env_boost + sunset_boost + wake_boost +
                                self._brightness_adjustment + self._scene_brightness_offset)

        # Calculate zone range for intelligent capping
        zone_min = zone_config.get("brightness_min", 0)
        zone_max = zone_config.get("brightness_max", 100)
        zone_range = zone_max - zone_min

        # Smart capping based on zone range
        if zone_range < 35:
            # Narrow zones: Hard cap at 30% to prevent collapse
            max_allowed = 30
        elif zone_range < 45:
            # Medium zones: Cap at zone_range - 5 (preserve 5% AL variation)
            max_allowed = zone_range - 5
        else:
            # Wide zones: Allow full boost (they can handle it)
            max_allowed = 50

        # Apply cap
        total_brightness = min(raw_brightness_boost, max_allowed)
        # Layer warmth components: manual + scene
        total_warmth = self._warmth_adjustment + self._scene_warmth_offset

        # Log warning if capping occurred
        capping_occurred = raw_brightness_boost > total_brightness
        if capping_occurred:
            _LOGGER.warning(
                "Zone %s: Combined boost capped at %d%% (requested %d%%). "
                "Zone range is %d%%. Consider widening range for full boost.",
                zone_id,
                total_brightness,
                raw_brightness_boost,
                zone_range,
            )

        # Skip if no adjustments active
        if total_brightness == 0 and total_warmth == 0:
            return

        try:
            # Calculate adjusted boundaries using adjustment engine
            adjusted_config = apply_adjustment_to_zone(
                zone_config,
                total_brightness,
                total_warmth,
            )

            # Phase 1.8: Store computed boundaries for sensor access
            if not hasattr(self, '_computed_boundaries'):
                self._computed_boundaries = {}

            brightness_min = adjusted_config["brightness_min"]
            brightness_max = adjusted_config["brightness_max"]
            brightness_range = brightness_max - brightness_min
            boundary_collapsed = brightness_min >= brightness_max

            self._computed_boundaries[zone_id] = {
                "brightness_min": brightness_min,
                "brightness_max": brightness_max,
                "brightness_range_pct": brightness_range,
                "color_temp_min": adjusted_config.get("color_temp_min"),
                "color_temp_max": adjusted_config.get("color_temp_max"),
                "boundary_collapsed": boundary_collapsed,
            }

            _LOGGER.debug(
                "Zone %s offsets: env=%d%%, sunset=%d%%, manual_b=%d%%, manual_w=%dK → total_b=%d%%, total_w=%dK",
                zone_id,
                env_boost,
                sunset_boost,
                self._brightness_adjustment,
                total_warmth,
                total_brightness,
                total_warmth,
            )

            # Prepare service data
            al_switch = zone_config.get("adaptive_lighting_switch")
            service_data = {
                "entity_id": al_switch,
                "min_brightness": adjusted_config["brightness_min"],
                "max_brightness": adjusted_config["brightness_max"],
            }

            # Add color temp if zone supports it
            if adjusted_config.get("color_temp_min") is not None:
                service_data["min_color_temp"] = adjusted_config["color_temp_min"]
                service_data["max_color_temp"] = adjusted_config["color_temp_max"]

            # Call adaptive_lighting.change_switch_settings
            await self.hass.services.async_call(
                ADAPTIVE_LIGHTING_DOMAIN,
                "change_switch_settings",
                service_data,
                blocking=False,
            )

            _LOGGER.debug(
                "Applied adjustments to zone %s: %s",
                zone_id,
                service_data,
            )

        except Exception as err:
            _LOGGER.error(
                "Failed to apply adjustments to zone %s: %s",
                zone_id,
                err,
                exc_info=True,
            )

    async def _mark_zone_lights_as_manual(self, zone_id: str) -> None:
        """Mark all lights in a zone as manually controlled in AL.

        This prevents AL from overriding user adjustments until timer expires.

        Args:
            zone_id: Zone identifier
        """
        try:
            # Get zone config
            zone_config = self.zones.get(zone_id)
            if not zone_config:
                _LOGGER.warning("Cannot mark zone %s - config not found", zone_id)
                return

            al_switch = zone_config.get("adaptive_lighting_switch")
            if not al_switch:
                _LOGGER.debug("Zone %s has no AL switch - skipping manual control mark", zone_id)
                return

            # Get all lights in zone
            lights = zone_config.get("lights", [])
            if not lights:
                _LOGGER.debug("Zone %s has no lights configured", zone_id)
                return

            # Mark lights as manually controlled in AL
            await self.hass.services.async_call(
                ADAPTIVE_LIGHTING_DOMAIN,
                "set_manual_control",
                {
                    "entity_id": al_switch,
                    "lights": lights,
                    "manual_control": True,
                },
                blocking=False,
            )

            _LOGGER.debug(
                "Marked %d lights in zone %s as manually controlled",
                len(lights),
                zone_id,
            )

        except Exception as err:
            _LOGGER.error(
                "Failed to mark zone %s as manual: %s",
                zone_id,
                err,
                exc_info=True,
            )

    async def _restore_adaptive_control(self, zone_id: str) -> None:
        """Restore adaptive control for a zone after timer expiry.

        Clears manual control flag in zone manager and triggers AL integration
        to reapply adaptive lighting. If this was the last active zone timer,
        also clears global manual adjustments (matches YAML behavior).

        Args:
            zone_id: Zone identifier
        """
        try:
            # Clear manual control in zone manager
            await self.zone_manager.async_cancel_timer(zone_id)

            # Get zone config
            zone_config = self.zones.get(zone_id)
            if not zone_config:
                _LOGGER.warning("Cannot restore zone %s - config not found", zone_id)
                return

            al_switch = zone_config.get("adaptive_lighting_switch")
            if not al_switch:
                _LOGGER.warning("Cannot restore zone %s - AL switch not configured", zone_id)
                return

            # Step 1: Clear manual_control flag in AL integration
            await self.hass.services.async_call(
                ADAPTIVE_LIGHTING_DOMAIN,
                "set_manual_control",
                {
                    "entity_id": al_switch,
                    "manual_control": False,
                },
                blocking=False,
            )

            # Step 2: Apply adaptive lighting to restore control
            await self.hass.services.async_call(
                ADAPTIVE_LIGHTING_DOMAIN,
                "apply",
                {
                    "entity_id": al_switch,
                    "lights": zone_config.get("lights", []),
                    "turn_on_lights": False,
                    "transition": 2,
                },
                blocking=False,
            )

            _LOGGER.info("Restored adaptive control for zone %s", zone_id)

            # Step 3: Check if ALL zone timers have expired
            # If so, clear manual adjustments (YAML-like behavior)
            if not self.zone_manager.any_manual_timers_active():
                if self._brightness_adjustment != 0 or self._warmth_adjustment != 0:
                    _LOGGER.info(
                        "All zone timers expired, clearing manual adjustments: "
                        "brightness %+d%% → 0%%, warmth %+dK → 0K",
                        self._brightness_adjustment,
                        self._warmth_adjustment,
                    )
                    self._brightness_adjustment = 0
                    self._warmth_adjustment = 0
                    # Trigger refresh to apply cleared adjustments
                    await self.async_request_refresh()

        except Exception as err:
            _LOGGER.error(
                "Failed to restore adaptive control for zone %s: %s",
                zone_id,
                err,
                exc_info=True,
            )

    def _get_default_zone_state(self, zone_id: str) -> dict[str, Any]:
        """Get default zone state when AL switch unavailable.

        Args:
            zone_id: Zone identifier

        Returns:
            Default zone state dictionary
        """
        timer_info = self.zone_manager.get_zone_timer_info(zone_id)
        return {
            "manual_control_active": timer_info.get("manual_control_active", False),
            "timer_remaining": timer_info.get("timer_remaining_seconds", 0),
            "current_brightness_pct": 0,
            "current_color_temp": 0,
            "lights_on_count": 0,
            "adaptive_lighting_active": False,
            "al_manual_control": False,
        }

    def _count_lights_on(self, light_entities: list[str]) -> int:
        """Count how many lights in a zone are currently on.

        Args:
            light_entities: List of light entity IDs

        Returns:
            Count of lights in 'on' state
        """
        count = 0
        for light_id in light_entities:
            light_state = self.hass.states.get(light_id)
            if light_state and light_state.state == "on":
                count += 1
        return count

    async def async_initialize(self) -> None:
        """Initialize coordinator to clean startup state.

        This is called once after the first data refresh to ensure a clean
        startup state, replacing the automation.al_startup_cleanup from YAML.

        Actions performed:
        - Reset all manual adjustments to 0
        - Clear all zone timers
        - Set global pause to False
        - Initialize environmental adapters with initial calculation
        - Validate AL switch availability (Phase 1.11)

        Note: Must be called AFTER async_config_entry_first_refresh() so that
        self.data is populated.
        """
        _LOGGER.info("Initializing Adaptive Lighting Pro coordinator to clean state")

        # Reset all manual adjustments to 0
        self._brightness_adjustment = 0
        self._warmth_adjustment = 0
        if self.data:
            self.data["global"]["total_brightness_adjustment"] = 0
            self.data["global"]["total_warmth_adjustment"] = 0

        # Clear all zone timers
        cleared_count = await self.zone_manager.async_cancel_all_timers()

        # Set global pause to False
        if self.data:
            self.data["global"]["paused"] = False

        # Initialize environmental adapters with initial calculation
        if self._env_adapter:
            # Trigger initial calculation
            self._env_adapter.calculate_boost()
            _LOGGER.debug("Environmental adapter initialized with initial boost calculation")

        # Validate AL switch availability for all zones (Phase 1.11)
        unavailable_switches = []
        available_switch_ids = []
        for zone_id, zone_config in self.zones.items():
            al_switch = zone_config.get("adaptive_lighting_switch")
            if not al_switch:
                _LOGGER.warning("Zone %s missing adaptive_lighting_switch configuration", zone_id)
                unavailable_switches.append(f"{zone_id} (not configured)")
                continue

            # Check if switch entity exists
            switch_state = self.hass.states.get(al_switch)
            if not switch_state:
                _LOGGER.warning(
                    "AL switch %s not found for zone %s - zone will be skipped during updates",
                    al_switch,
                    zone_id,
                )
                unavailable_switches.append(al_switch)
            else:
                # Check for required attributes
                attrs = switch_state.attributes
                if "manual_control" not in attrs:
                    _LOGGER.warning(
                        "AL switch %s missing 'manual_control' attribute for zone %s - "
                        "this switch may not be from Adaptive Lighting integration",
                        al_switch,
                        zone_id,
                    )
                    unavailable_switches.append(f"{al_switch} (missing manual_control)")
                else:
                    available_switch_ids.append(al_switch)

        # Store switch health status in coordinator data
        if self.data:
            self.data["global"]["switch_health"] = {
                "total_switches": len(self.zones),
                "available_switches": len(self.zones) - len(unavailable_switches),
                "unavailable": unavailable_switches,
                "available_switch_ids": available_switch_ids,
                "status": "OK" if not unavailable_switches else "Degraded",
            }

        # Validate light entities for all zones (Phase 1.12)
        light_to_zones: dict[str, list[str]] = {}  # Track which zones contain which lights
        unavailable_lights = []
        total_lights = 0
        zones_without_lights = []

        for zone_id, zone_config in self.zones.items():
            lights = zone_config.get("lights", [])
            if not lights:
                _LOGGER.warning("Zone %s has no lights configured", zone_id)
                zones_without_lights.append(zone_id)
                continue

            total_lights += len(lights)
            zone_unavailable_count = 0

            for light in lights:
                # Check if light entity exists
                light_state = self.hass.states.get(light)
                if not light_state:
                    _LOGGER.warning(
                        "Light %s not found in Home Assistant for zone %s - "
                        "ensure entity exists or check entity_id spelling",
                        light,
                        zone_id,
                    )
                    if light not in unavailable_lights:
                        unavailable_lights.append(light)
                    zone_unavailable_count += 1

                # Track for multi-zone detection (even if unavailable)
                if light not in light_to_zones:
                    light_to_zones[light] = []
                light_to_zones[light].append(zone_id)

            # Warn if all lights unavailable
            if zone_unavailable_count == len(lights):
                _LOGGER.warning(
                    "Zone %s has NO available lights (%d/%d unavailable) - "
                    "zone will not control any lights",
                    zone_id,
                    zone_unavailable_count,
                    len(lights),
                )

        # Detect and warn about multi-zone lights
        multi_zone_lights = {
            light: zones for light, zones in light_to_zones.items() if len(zones) > 1
        }
        for light, zones in multi_zone_lights.items():
            _LOGGER.warning(
                "Light %s appears in multiple zones: %s - "
                "this may cause conflicts if zones have different settings",
                light,
                ", ".join(zones),
            )

        # Store light health status in coordinator data
        available_light_count = total_lights - len(unavailable_lights)
        if self.data:
            self.data["global"]["light_health"] = {
                "total_lights": total_lights,
                "available_lights": available_light_count,
                "unavailable_lights": unavailable_lights,
                "multi_zone_lights": multi_zone_lights,
                "zones_without_lights": zones_without_lights,
                "status": (
                    "OK"
                    if not unavailable_lights and not multi_zone_lights
                    else "Warning"
                    if multi_zone_lights and not unavailable_lights
                    else "Degraded"
                ),
            }

        # Build comprehensive status message
        switch_status = "all switches available" if not unavailable_switches else f"{len(unavailable_switches)} switch(es) unavailable"
        light_status = "all lights available" if not unavailable_lights else f"{len(unavailable_lights)} light(s) unavailable"
        _LOGGER.info(
            "Adaptive Lighting Pro initialized: %d zones configured, %d timers cleared, adjustments reset, %s, %s",
            len(self.zones),
            cleared_count,
            switch_status,
            light_status,
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh of coordinator data.

        This is called once when the integration is first loaded. It ensures
        the coordinator has valid data before any entities are created.

        Overrides the base class method to add custom initialization logic.
        """
        _LOGGER.info("Performing first coordinator refresh for ALP")

        try:
            await super().async_config_entry_first_refresh()
            _LOGGER.info("First coordinator refresh completed successfully")
        except Exception as err:
            _LOGGER.error(
                "Failed to perform first refresh: %s",
                err,
                exc_info=True
            )
            raise

    async def async_shutdown(self) -> None:
        """Clean up coordinator resources on shutdown.

        Called when the integration is unloaded or Home Assistant is shutting down.

        Phase 2: Persist zone timer state for recovery
        Future phases will add cleanup for:
        - Cancelling active timers
        - Unregistering event listeners
        - Closing external connections
        """
        _LOGGER.info("Shutting down ALP coordinator")

        try:
            # Persist zone timer state
            await self.zone_manager.async_persist_state()
            _LOGGER.debug("Zone timer state persisted")
        except Exception as err:
            _LOGGER.error("Error persisting state during shutdown: %s", err)

        _LOGGER.info("ALP coordinator shutdown complete")

    # ========== Public API: Zone Queries ==========

    @property
    def zone_ids(self) -> list[str]:
        """Get list of configured zone IDs.

        Returns:
            List of zone ID strings (e.g., ["main_living", "kitchen_island"])
        """
        return list(self.zones.keys())

    def get_zone_config(self, zone_id: str) -> dict[str, Any] | None:
        """Get configuration for a specific zone.

        Args:
            zone_id: Zone identifier (e.g., "main_living")

        Returns:
            Zone configuration dictionary, or None if zone doesn't exist
        """
        return self.zones.get(zone_id)

    def get_zone_state(self, zone_id: str) -> dict[str, Any] | None:
        """Get current state for a specific zone.

        Args:
            zone_id: Zone identifier (e.g., "main_living")

        Returns:
            Zone state dictionary from coordinator data, or None if not found
        """
        if not self.data:
            return None
        return self.data.get("zones", {}).get(zone_id)

    # ========== Public API: Adjustment Management ==========

    async def set_brightness_adjustment(self, value: int, start_timers: bool = False) -> None:
        """Update global brightness adjustment value.

        Args:
            value: Brightness adjustment in percent (-100 to +100)
            start_timers: If True, starts manual control timers for all zones.
                         Use True for temporary overrides (buttons, services).
                         Use False for persistent preferences (sliders).
        """
        if not (-100 <= value <= 100):
            _LOGGER.error("Invalid brightness adjustment: %d (must be -100 to +100)", value)
            return

        old_value = self._brightness_adjustment
        self._brightness_adjustment = value

        _LOGGER.info(
            "Brightness adjustment changed: %d%% → %d%%",
            old_value,
            value,
        )

        # Start manual timers for temporary overrides (buttons, not sliders)
        if start_timers and old_value != value:  # Only if value actually changed
            for zone_id in self.zones:
                await self.start_manual_timer(zone_id)
            _LOGGER.info(
                "Started manual timers for %d zones (temporary brightness override)",
                len(self.zones)
            )

        # Trigger immediate coordinator update
        await self.async_request_refresh()

    async def set_warmth_adjustment(self, value: int, start_timers: bool = False) -> None:
        """Update global warmth adjustment value.

        Args:
            value: Warmth adjustment in Kelvin (-2500 to +2500)
            start_timers: If True, starts manual control timers for all zones.
                         Use True for temporary overrides (buttons, services).
                         Use False for persistent preferences (sliders).
        """
        if not (-2500 <= value <= 2500):
            _LOGGER.error("Invalid warmth adjustment: %dK (must be -2500 to +2500)", value)
            return

        old_value = self._warmth_adjustment
        self._warmth_adjustment = value

        _LOGGER.info(
            "Warmth adjustment changed: %+dK → %+dK",
            old_value,
            value,
        )

        # Start manual timers for temporary overrides (buttons, not sliders)
        if start_timers and old_value != value:  # Only if value actually changed
            for zone_id in self.zones:
                await self.start_manual_timer(zone_id)
            _LOGGER.info(
                "Started manual timers for %d zones (temporary warmth override)",
                len(self.zones)
            )

        # Trigger immediate coordinator update
        await self.async_request_refresh()

    async def set_brightness_increment(self, value: int) -> None:
        """Update brightness increment for button actions.

        Configuration values don't affect zone calculations, only future button
        presses, so we update listeners without triggering a full refresh.

        Args:
            value: Brightness increment in percent (5-50)
        """
        # Clamp to valid range (forgiving, as per claude.md graceful degradation)
        clamped_value = max(BRIGHTNESS_INCREMENT_MIN, min(value, BRIGHTNESS_INCREMENT_MAX))

        if clamped_value != value:
            _LOGGER.warning(
                "Brightness increment %d%% out of range, clamped to %d%%",
                value,
                clamped_value,
            )

        old_value = self._brightness_increment
        self._brightness_increment = clamped_value

        _LOGGER.info(
            "Brightness increment changed: %d%% → %d%%",
            old_value,
            clamped_value,
        )

        # Update entities without triggering zone recalculation
        self.async_update_listeners()

    async def set_color_temp_increment(self, value: int) -> None:
        """Update color temperature increment for button actions.

        Configuration values don't affect zone calculations, only future button
        presses, so we update listeners without triggering a full refresh.

        Args:
            value: Color temperature increment in Kelvin (100-1000)
        """
        # Clamp to valid range
        clamped_value = max(COLOR_TEMP_INCREMENT_MIN, min(value, COLOR_TEMP_INCREMENT_MAX))

        if clamped_value != value:
            _LOGGER.warning(
                "Color temp increment %dK out of range, clamped to %dK",
                value,
                clamped_value,
            )

        old_value = self._color_temp_increment
        self._color_temp_increment = clamped_value

        _LOGGER.info(
            "Color temp increment changed: %dK → %dK",
            old_value,
            clamped_value,
        )

        # Update entities without triggering zone recalculation
        self.async_update_listeners()

    async def set_manual_control_timeout(self, value: int) -> None:
        """Update manual control timeout duration.

        Configuration values don't affect zone calculations, only future timer
        behavior, so we update listeners without triggering a full refresh.

        Args:
            value: Timeout in seconds (300-14400, i.e., 5 min to 4 hours)
        """
        # Clamp to valid range
        clamped_value = max(MANUAL_TIMEOUT_MIN, min(value, MANUAL_TIMEOUT_MAX))

        if clamped_value != value:
            _LOGGER.warning(
                "Manual timeout %ds out of range, clamped to %ds",
                value,
                clamped_value,
            )

        old_value = self._manual_control_timeout
        self._manual_control_timeout = clamped_value

        _LOGGER.info(
            "Manual control timeout changed: %ds → %ds",
            old_value,
            clamped_value,
        )

        # Update entities without triggering zone recalculation
        self.async_update_listeners()

    def get_brightness_adjustment(self) -> int:
        """Get current global brightness adjustment.

        Returns:
            Brightness adjustment in percent (-100 to +100)
        """
        return self._brightness_adjustment

    def get_warmth_adjustment(self) -> int:
        """Get current global warmth adjustment.

        Returns:
            Warmth adjustment in Kelvin (-2500 to +2500)
        """
        return self._warmth_adjustment

    def get_brightness_increment(self) -> int:
        """Get configured brightness increment for manual adjustments.

        Returns:
            Brightness increment in percent (default 20%)
        """
        return self._brightness_increment

    def get_color_temp_increment(self) -> int:
        """Get configured color temperature increment for manual adjustments.

        Returns:
            Color temperature increment in Kelvin (default 500K)
        """
        return self._color_temp_increment

    def get_manual_control_timeout(self) -> int:
        """Get configured manual control timeout.

        Returns:
            Timeout in seconds (default 7200s / 2 hours)
        """
        return self._manual_control_timeout

    def get_scene_brightness_offset(self) -> int:
        """Get current scene brightness offset.

        Returns:
            Scene brightness offset in percent
        """
        return self._scene_brightness_offset

    def get_scene_warmth_offset(self) -> int:
        """Get current scene warmth offset.

        Returns:
            Scene warmth offset in Kelvin
        """
        return self._scene_warmth_offset

    def get_paused(self) -> bool:
        """Get current pause state.

        Returns:
            True if adaptive lighting is paused, False if active
        """
        return self.data.get("global", {}).get("paused", False)

    def get_last_env_boost(self) -> int:
        """Get last calculated environmental boost.

        Returns:
            Environmental boost percentage (0-25%)
        """
        return self._last_env_boost

    def get_last_sunset_boost(self) -> int:
        """Get last calculated sunset boost.

        Returns:
            Sunset boost percentage (0-25%)
        """
        return self._last_sunset_boost

    def get_last_wake_boost(self) -> int:
        """Get last calculated wake sequence boost.

        Returns:
            Wake sequence boost percentage (0-20%)
        """
        return self._last_wake_boost

    def get_wake_sequence_state(self) -> dict[str, Any]:
        """Get complete wake sequence state.

        Returns:
            Wake sequence state dictionary with alarm time, progress, etc.
        """
        return self._wake_sequence.get_state_dict()

    def get_zone_computed_boundaries(self, zone_id: str) -> dict[str, Any] | None:
        """Get computed boundaries for a zone after all offsets applied.

        Phase 1.8: Expose computed boundaries for sensor platform debugging.

        Args:
            zone_id: Zone identifier

        Returns:
            Dictionary with keys:
            - brightness_min: Final minimum brightness (0-100)
            - brightness_max: Final maximum brightness (0-100)
            - brightness_range_pct: Remaining range (max - min)
            - color_temp_min: Final minimum color temp (Kelvin) or None
            - color_temp_max: Final maximum color temp (Kelvin) or None
            - boundary_collapsed: True if min >= max
            Returns None if zone not found or boundaries not yet computed
        """
        if not hasattr(self, '_computed_boundaries'):
            return None
        return self._computed_boundaries.get(zone_id)

    # ========== Public API: Manual Control ==========

    async def start_manual_timer(self, zone_id: str, duration_seconds: int | None = None) -> bool:
        """Start manual control timer for a zone.

        Args:
            zone_id: Zone identifier
            duration_seconds: Optional timer duration (uses smart calculation if None)

        Returns:
            True if timer started successfully
        """
        # Get environmental data for smart timeout calculation
        sun_elevation = None
        env_boost = 0

        if duration_seconds is None:
            # Get sun elevation from sun.sun entity
            sun_state = self.hass.states.get("sun.sun")
            if sun_state:
                sun_elevation = sun_state.attributes.get("elevation")

            # Get current environmental boost
            env_boost = self._env_adapter.calculate_boost()

        # Step 1: Mark lights as manually controlled in AL
        await self._mark_zone_lights_as_manual(zone_id)

        # Step 2: Start timer with smart duration calculation
        await self.zone_manager.async_start_manual_timer(
            zone_id=zone_id,
            duration=duration_seconds,
            sun_elevation=sun_elevation,
            env_boost=env_boost,
        )

        # Step 3: Trigger immediate coordinator update to reflect new state
        await self.async_request_refresh()

        return True

    async def cancel_manual_timer(self, zone_id: str) -> bool:
        """Cancel manual control timer for a zone.

        Args:
            zone_id: Zone identifier

        Returns:
            True if timer cancelled successfully
        """
        success = await self.zone_manager.async_cancel_timer(zone_id)

        if success:
            # Restore adaptive control
            await self._restore_adaptive_control(zone_id)
            # Trigger immediate coordinator update
            await self.async_request_refresh()

        return success

    async def cancel_all_timers(self) -> int:
        """Cancel all active manual control timers.

        Returns:
            Number of timers cancelled
        """
        count = await self.zone_manager.async_cancel_all_timers()

        if count > 0:
            # Restore adaptive control for all zones
            for zone_id in self.zones:
                await self._restore_adaptive_control(zone_id)

            # Trigger immediate coordinator update
            await self.async_request_refresh()

        return count

    def _get_current_lux(self) -> float | None:
        """Get current outdoor lux from configured sensor.

        Returns:
            Current lux value, or None if sensor unavailable
        """
        environmental_config = self.config_entry.data.get("environmental", {})
        lux_sensor = environmental_config.get("lux_sensor")

        if not lux_sensor:
            return None

        state = self.hass.states.get(lux_sensor)
        if not state or state.state in ("unknown", "unavailable"):
            return None

        try:
            return float(state.state)
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid lux value from %s: %s", lux_sensor, state.state)
            return None

    # ========== Public API: Scenes ==========

    async def apply_scene(self, scene: Scene) -> bool:
        """Apply a scene with full actions and offsets.

        Args:
            scene: Scene enum value

        Returns:
            True if scene applied successfully
        """
        if scene not in SCENE_CONFIGS:
            _LOGGER.error("Unknown scene: %s", scene)
            return False

        config = SCENE_CONFIGS[scene]
        self._current_scene = scene

        # Execute scene actions first
        for action in config.get("actions", []):
            try:
                action_copy = action.copy()
                action_name = action_copy.pop("action")
                domain, service = action_name.split(".")
                await self.hass.services.async_call(
                    domain,
                    service,
                    action_copy,
                    blocking=False,
                )
                _LOGGER.debug("Scene '%s' executed action: %s", config["name"], action_name)
            except Exception as err:
                _LOGGER.error(
                    "Failed to execute scene action %s: %s",
                    action_copy if 'action_copy' in locals() else action,
                    err,
                    exc_info=True,
                )

        # Apply scene offsets (ALL scenes including ALL_LIGHTS use same pattern)
        # ALL_LIGHTS has 0 offsets, so it clears back to adaptive baseline
        # Manual adjustments are preserved - they're a separate layer
        self._scene_brightness_offset = config.get("brightness_offset", 0)
        self._scene_warmth_offset = config.get("warmth_offset", 0)

        _LOGGER.info(
            "Scene '%s' applied: brightness_offset=%+d%%, warmth_offset=%+dK",
            config["name"],
            self._scene_brightness_offset,
            self._scene_warmth_offset,
        )

        return True

    def get_current_scene(self) -> Scene:
        """Get current scene preset.

        Returns:
            Current Scene enum value
        """
        return self._current_scene

    async def clear_scene_offsets(self) -> None:
        """Clear scene offsets and return to DEFAULT scene.

        This is the proper API for resetting scene state. Used by:
        - reset_manual_adjustments service
        - reset_all service (nuclear reset)

        Does NOT clear manual adjustments - use set_brightness_adjustment(0) for that.
        """
        self._scene_brightness_offset = 0
        self._scene_warmth_offset = 0
        self._current_scene = Scene.DEFAULT
        _LOGGER.info("Scene offsets cleared, returned to DEFAULT scene")

    # ========== Public API: Pause State ==========

    async def set_paused(self, paused: bool) -> None:
        """Set global pause state.

        Args:
            paused: True to pause adaptive lighting, False to resume
        """
        if not self.data:
            _LOGGER.warning("Cannot set paused state - coordinator has no data")
            return

        old_value = self.data.get("global", {}).get("paused", False)
        self.data["global"]["paused"] = paused

        _LOGGER.info(
            "Global pause state changed: %s → %s",
            "paused" if old_value else "active",
            "paused" if paused else "active"
        )

        await self.async_request_refresh()

    async def cycle_scene(self) -> Scene:
        """Cycle to next scene in sequence.

        Returns:
            The newly applied scene
        """
        self._scene_index = (self._scene_index + 1) % len(self._scene_list)
        next_scene = self._scene_list[self._scene_index]

        _LOGGER.info(
            "Cycling to scene %d/%d: %s",
            self._scene_index + 1,
            len(self._scene_list),
            next_scene.value if hasattr(next_scene, 'value') else next_scene
        )

        await self.apply_scene(next_scene)
        return next_scene

    async def set_wake_alarm(self, alarm_time: datetime) -> None:
        """Set wake alarm manually (for testing or non-Sonos alarm systems).

        Wake sequence will start at alarm_time minus configured duration (default 15 min).
        Timezone-aware datetime required - if naive datetime provided, will be converted
        to local timezone.

        Args:
            alarm_time: When alarm will fire (wake sequence starts earlier)

        Raises:
            ValueError: If alarm time is in the past
        """
        # Ensure timezone-aware datetime (graceful handling of user input)
        if alarm_time.tzinfo is None:
            alarm_time = dt_util.as_local(alarm_time)
            _LOGGER.debug("Converted naive alarm time to timezone-aware: %s", alarm_time)

        # Validate alarm is not in past (strict validation for logic errors)
        now = dt_util.now()
        if alarm_time <= now:
            error_msg = (
                f"Cannot set wake alarm in the past. "
                f"Alarm time: {alarm_time.isoformat()}, Current time: {now.isoformat()}"
            )
            _LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Set alarm via wake sequence
        self._wake_sequence.set_next_alarm(alarm_time)

        wake_start = alarm_time - self._wake_sequence._duration

        _LOGGER.info(
            "Wake alarm set manually: alarm at %s, wake sequence starts at %s",
            alarm_time.isoformat(),
            wake_start.isoformat(),
        )

        # Trigger coordinator refresh to calculate wake boost
        await self.async_request_refresh()

    async def clear_wake_alarm(self) -> None:
        """Clear wake alarm and cancel active wake sequence.

        Safe to call even if no alarm is set.
        """
        had_alarm = self._wake_sequence._next_alarm is not None

        self._wake_sequence.clear_alarm()

        if had_alarm:
            _LOGGER.info("Wake alarm cleared, wake sequence cancelled")
        else:
            _LOGGER.debug("Clear wake alarm called, but no alarm was set")

        # Trigger coordinator refresh to reset wake boost to 0
        await self.async_request_refresh()

    def get_wake_start_time(self) -> datetime | None:
        """Get when wake sequence starts (alarm time minus duration).

        Returns:
            Datetime when wake sequence begins, or None if no alarm set
        """
        if not self._wake_sequence._next_alarm:
            return None

        return self._wake_sequence._next_alarm - self._wake_sequence._duration

    def _calculate_health_score(self, state: dict[str, Any]) -> tuple[int, str]:
        """Calculate system health score based on current state.

        Checks for:
        - Collapsed ranges (min >= max)
        - Unavailable AL switches
        - Zones with active manual control
        - Recent capping events

        Args:
            state: Current coordinator state

        Returns:
            Tuple of (score 0-100, status string)
        """
        score = 100
        issues = []

        # Check for collapsed brightness ranges
        for zone_id, zone_state in state.get("zones", {}).items():
            zone_config = self.zones.get(zone_id, {})
            min_brightness = zone_config.get("brightness_min", 0)
            max_brightness = zone_config.get("brightness_max", 100)

            if min_brightness >= max_brightness:
                score -= 20
                issues.append(f"Zone {zone_id} collapsed")

        # Check for unavailable AL switches
        unavailable_count = 0
        for zone_id, zone_config in self.zones.items():
            al_switch = zone_config.get("adaptive_lighting_switch")
            if al_switch:
                al_state = self.hass.states.get(al_switch)
                if not al_state or al_state.state in ("unknown", "unavailable"):
                    unavailable_count += 1
                    score -= 15

        if unavailable_count > 0:
            issues.append(f"{unavailable_count} switches offline")

        # Check for zones with manual control
        manual_zones = sum(
            1 for zone_state in state.get("zones", {}).values()
            if zone_state.get("manual_control_active", False)
        )
        if manual_zones > 0:
            score -= 5 * manual_zones
            issues.append(f"{manual_zones} zones manual")

        # Determine status
        if score >= 90:
            status = "Excellent"
        elif score >= 70:
            status = "Good"
        elif score >= 50:
            status = "Fair"
        else:
            status = "Poor"

        if issues:
            status += f" ({', '.join(issues)})"

        return max(0, score), status
