"""Sensor platform for Adaptive Lighting Pro.

Provides comprehensive visibility into all integration state.

Phase 2.2: Critical sensors for Sonos/Zen32 (9 sensors)
Phase 2.3: Complete sensor suite for full system visibility (13+ sensors)

Following claude.md: "You can't improve what you can't see"
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, EVENT_CALCULATION_COMPLETE
from .entity import ALPEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ALP sensor platform."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data.get("coordinator") if isinstance(entry_data, dict) else entry_data

    sensors: list[SensorEntity] = []

    # Critical debugging sensors for Sonos wake sequence
    sensors.extend([
        WakeSequenceOffsetSensor(coordinator, config_entry),
        NextAlarmSensor(coordinator, config_entry),
        WakeStartTimeSensor(coordinator, config_entry),
        EnvironmentalBoostSensor(coordinator, config_entry),
        SunsetBoostSensor(coordinator, config_entry),
    ])

    # Critical debugging sensor for Zen32 scene control
    sensors.append(CurrentSceneSensor(coordinator, config_entry))

    # Global adjustment sensors (needed to see total brightness)
    sensors.extend([
        BrightnessAdjustmentSensor(coordinator, config_entry),
        WarmthAdjustmentSensor(coordinator, config_entry),
    ])

    # Health sensor (verify integration is running)
    sensors.append(HealthStatusSensor(coordinator, config_entry))

    # Phase 2.3: Full sensor suite for complete visibility
    # Primary status sensor with 15+ attributes
    sensors.append(ALPStatusSensor(coordinator, config_entry))

    # Real-time event-driven monitor
    sensors.append(RealtimeMonitorSensor(coordinator, config_entry, hass))

    # Per-zone manual control sensors
    for zone_id in coordinator.zones.keys():
        sensors.append(ZoneManualControlSensor(coordinator, config_entry, zone_id))

    # Aggregate sensors
    sensors.extend([
        TotalManualControlSensor(coordinator, config_entry),
        ZonesWithManualControlSensor(coordinator, config_entry),
        DeviationTrackerSensor(coordinator, config_entry),
    ])

    # System health with scoring
    sensors.append(SystemHealthSensor(coordinator, config_entry))

    # Performance and usage tracking (missing from implementation_1.yaml)
    sensors.extend([
        PerformanceMetricsSensor(coordinator, config_entry),
        UsageStatisticsSensor(coordinator, config_entry),
        ActiveLightsCountSensor(coordinator, config_entry, hass),
        ManualAdjustmentStatusSensor(coordinator, config_entry),
        BrightnessStatusSensor(coordinator, config_entry),
    ])

    # Wake sequence status with progress tracking
    sensors.append(WakeSequenceStatusSensor(coordinator, config_entry))

    # Phase 7: Additional diagnostic sensors for troubleshooting
    sensors.extend([
        ALPLastActionSensor(coordinator, config_entry),
        ALPTimerStatusSensor(coordinator, config_entry),
        ALPZoneHealthSensor(coordinator, config_entry),
    ])

    _LOGGER.info("Setting up %d sensors for complete system visibility", len(sensors))
    async_add_entities(sensors)


class WakeSequenceOffsetSensor(ALPEntity, SensorEntity):
    """Sensor showing current Sonos wake sequence brightness offset."""

    _attr_icon = "mdi:alarm-light"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry):
        """Initialize wake sequence offset sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_wake_sequence_offset"
        self._attr_name = "ALP Wake Sequence Offset"

    @property
    def native_value(self) -> int:
        """Return wake sequence offset (0-20%)."""
        if not self.coordinator.data:
            return 0
        wake_state = self.coordinator.data.get("wake_sequence", {})
        return wake_state.get("current_boost_pct", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        wake_state = self.coordinator.data.get("wake_sequence", {})
        max_boost = wake_state.get("max_boost_pct", 20)
        current_boost = wake_state.get("current_boost_pct", 0)

        return {
            "wake_active": wake_state.get("active", False),
            "target_zone": wake_state.get("target_zone"),
            "ramp_progress": f"{current_boost}/{max_boost}%",
            "progress_pct": wake_state.get("progress_pct", 0.0),
            "alarm_time": wake_state.get("alarm_time"),
            "wake_start_time": wake_state.get("wake_start_time"),
        }


class NextAlarmSensor(ALPEntity, SensorEntity):
    """Sensor showing next Sonos alarm time."""

    _attr_icon = "mdi:alarm"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, config_entry):
        """Initialize next alarm sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_next_alarm"
        self._attr_name = "ALP Next Alarm"

    @property
    def native_value(self) -> str | None:
        """Return next alarm time as ISO timestamp."""
        if not self.coordinator.data:
            return None
        wake_state = self.coordinator.data.get("wake_sequence", {})
        return wake_state.get("alarm_time")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        wake_state = self.coordinator.data.get("wake_sequence", {})
        return {
            "target_zone": wake_state.get("target_zone"),
            "alarm_detected": wake_state.get("alarm_time") is not None,
            "wake_sequence_active": wake_state.get("active", False),
        }


class WakeStartTimeSensor(ALPEntity, SensorEntity):
    """Sensor showing when wake sequence will/did start."""

    _attr_icon = "mdi:alarm-light-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, config_entry):
        """Initialize wake start time sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_wake_start_time"
        self._attr_name = "ALP Wake Start Time"

    @property
    def native_value(self) -> str | None:
        """Return wake start time (alarm - 15min) as ISO timestamp."""
        if not self.coordinator.data:
            return None
        wake_state = self.coordinator.data.get("wake_sequence", {})
        return wake_state.get("wake_start_time")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        wake_state = self.coordinator.data.get("wake_sequence", {})
        duration_min = wake_state.get("duration_seconds", 900) // 60
        max_boost = wake_state.get("max_boost_pct", 20)

        return {
            "minutes_before_alarm": duration_min,
            "wake_duration": f"{duration_min} minutes",
            "max_offset": f"{max_boost}%",
        }


class EnvironmentalBoostSensor(ALPEntity, SensorEntity):
    """Sensor showing current environmental boost."""

    _attr_icon = "mdi:weather-cloudy"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry):
        """Initialize environmental boost sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_environmental_boost"
        self._attr_name = "ALP Environmental Boost"

    @property
    def native_value(self) -> int:
        """Return environmental boost percentage."""
        return self.coordinator.get_last_env_boost()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        env = self.coordinator.data.get("environmental", {})
        return {
            "boost_active": env.get("boost_active", False),
            "current_lux": env.get("current_lux", 0),
        }


class SunsetBoostSensor(ALPEntity, SensorEntity):
    """Sensor showing current sunset boost."""

    _attr_icon = "mdi:weather-sunset"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry):
        """Initialize sunset boost sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_sunset_boost"
        self._attr_name = "ALP Sunset Boost"

    @property
    def native_value(self) -> int:
        """Return sunset boost percentage."""
        return self.coordinator.get_last_sunset_boost()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        env = self.coordinator.data.get("environmental", {})
        return {
            "boost_active": env.get("sunset_boost_active", False),
            "sunset_boost_offset": env.get("sunset_boost_offset", 0),
        }


class CurrentSceneSensor(ALPEntity, SensorEntity):
    """Sensor showing current active scene (for Zen32 debugging)."""

    _attr_icon = "mdi:palette"

    def __init__(self, coordinator, config_entry):
        """Initialize current scene sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_current_scene"
        self._attr_name = "ALP Current Scene"

    @property
    def native_value(self) -> str:
        """Return current scene name."""
        if not self.coordinator.data:
            return "default"
        return self.coordinator.data.get("global", {}).get("current_scene", "default")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return scene offset details."""
        if not self.coordinator.data:
            return {}

        global_data = self.coordinator.data.get("global", {})
        return {
            "brightness_offset": global_data.get("scene_brightness_offset", 0),
            "warmth_offset": global_data.get("scene_warmth_offset", 0),
            "last_changed_by": global_data.get("scene_changed_by", "unknown"),
        }


class BrightnessAdjustmentSensor(ALPEntity, SensorEntity):
    """Sensor showing total manual brightness adjustment."""

    _attr_icon = "mdi:brightness-6"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry):
        """Initialize brightness adjustment sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_brightness_adjustment"
        self._attr_name = "ALP Brightness Adjustment"

    @property
    def native_value(self) -> int:
        """Return brightness adjustment (-50 to +50)."""
        return self.coordinator.get_brightness_adjustment()


class WarmthAdjustmentSensor(ALPEntity, SensorEntity):
    """Sensor showing total manual warmth adjustment."""

    _attr_icon = "mdi:thermometer"
    _attr_native_unit_of_measurement = "K"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry):
        """Initialize warmth adjustment sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_warmth_adjustment"
        self._attr_name = "ALP Warmth Adjustment"

    @property
    def native_value(self) -> int:
        """Return warmth adjustment (-3000 to +3000K)."""
        return self.coordinator.get_warmth_adjustment()


class HealthStatusSensor(ALPEntity, SensorEntity):
    """Sensor showing integration health status."""

    _attr_icon = "mdi:heart-pulse"

    def __init__(self, coordinator, config_entry):
        """Initialize health status sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_health_status"
        self._attr_name = "ALP Health Status"

    @property
    def native_value(self) -> str:
        """Return health status text."""
        if not self.coordinator.data:
            return "Unknown"
        return self.coordinator.data.get("global", {}).get("health_status", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return health details."""
        if not self.coordinator.data:
            return {}

        global_data = self.coordinator.data.get("global", {})
        return {
            "health_score": global_data.get("health_score", 0),
            "last_update": self.coordinator.last_update_success_time.isoformat() if self.coordinator.last_update_success_time else None,
        }

# ==================== PHASE 2.3: COMPREHENSIVE SENSOR SUITE ====================


class ALPStatusSensor(ALPEntity, SensorEntity):
    """Primary status sensor with 15+ comprehensive attributes.
    
    This is YOUR dashboard into the system - shows everything at a glance.
    """

    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator, config_entry):
        """Initialize ALP status sensor."""
        super().__init__(coordinator, config_entry, "sensor", "status", "ALP Status")

    @property
    def native_value(self) -> str:
        """Return current system status description."""
        if not self.coordinator.data:
            return "Unknown"

        global_data = self.coordinator.data.get("global", {})
        env_data = self.coordinator.data.get("environmental", {})
        
        paused = global_data.get("paused", False)
        if paused:
            return "Paused"
        
        # Check if any boosts active
        boosts_active = []
        if env_data.get("boost_active"):
            boosts_active.append("Environmental")
        if env_data.get("sunset_boost_active"):
            boosts_active.append("Sunset")
        if env_data.get("wake_boost_active"):
            boosts_active.append("Wake")
        
        if boosts_active:
            return f"Active ({', '.join(boosts_active)})"
        
        manual_adj = global_data.get("total_brightness_adjustment", 0)
        if manual_adj != 0:
            return f"Manual Adjustment ({manual_adj:+d}%)"
        
        return "Adaptive"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return 15+ comprehensive attributes."""
        if not self.coordinator.data:
            return {}

        global_data = self.coordinator.data.get("global", {})
        env_data = self.coordinator.data.get("environmental", {})
        zones_data = self.coordinator.data.get("zones", {})

        return {
            # Active modifiers
            "active_modifiers": self._get_active_modifiers(),
            "last_action": "coordinator_update",
            
            # System health
            "system_health": global_data.get("health_status", "Unknown"),
            "health_score": global_data.get("health_score", 0),
            
            # Current adjustments
            "brightness_adjustment": global_data.get("total_brightness_adjustment", 0),
            "warmth_adjustment": global_data.get("total_warmth_adjustment", 0),
            "current_scene": global_data.get("current_scene", "default"),
            
            # Environmental calculation
            "environmental_boost": env_data.get("current_boost_pct", 0),
            "sunset_boost": env_data.get("sunset_boost_offset", 0),
            "wake_boost": env_data.get("wake_boost_pct", 0),
            "current_lux": env_data.get("current_lux", 0),
            
            # Sun position
            "sun_elevation": self.hass.states.get("sun.sun").attributes.get("elevation", 0) if self.hass.states.get("sun.sun") else 0,
            
            # Active switches and zones
            "active_switches": [zone_id for zone_id, zone in zones_data.items() if zone.get("adaptive_lighting_active")],
            "managed_zones": list(zones_data.keys()),
            
            # Computed ranges (for debugging boundary issues)
            "computed_ranges": {
                zone_id: zone.get("computed_brightness_range", {})
                for zone_id, zone in zones_data.items()
            },
            
            # Manual timer info
            "zones_with_timers": [
                zone_id for zone_id, zone in zones_data.items()
                if zone.get("manual_control_active") and zone.get("timer_remaining", 0) > 0
            ],
        }
    
    def _get_active_modifiers(self) -> list[str]:
        """Get list of active modifiers affecting brightness."""
        modifiers = []
        if not self.coordinator.data:
            return modifiers
        
        global_data = self.coordinator.data.get("global", {})
        env_data = self.coordinator.data.get("environmental", {})
        
        if env_data.get("boost_active"):
            modifiers.append(f"Environmental +{env_data.get('current_boost_pct', 0)}%")
        if env_data.get("sunset_boost_active"):
            modifiers.append(f"Sunset +{env_data.get('sunset_boost_offset', 0)}%")
        if env_data.get("wake_boost_active"):
            modifiers.append(f"Wake +{env_data.get('wake_boost_pct', 0)}%")
        if global_data.get("total_brightness_adjustment", 0) != 0:
            modifiers.append(f"Manual {global_data.get('total_brightness_adjustment', 0):+d}%")
        if global_data.get("current_scene", "default") != "default":
            modifiers.append(f"Scene: {global_data.get('current_scene')}")
        
        return modifiers if modifiers else ["None"]


class RealtimeMonitorSensor(ALPEntity, SensorEntity):
    """Real-time event-driven monitor - updates on every calculation.
    
    Listens to EVENT_CALCULATION_COMPLETE for instant feedback.
    """

    _attr_icon = "mdi:monitor-dashboard"

    def __init__(self, coordinator, config_entry, hass):
        """Initialize realtime monitor."""
        super().__init__(coordinator, config_entry, "sensor", "realtime_monitor", "ALP Realtime Monitor")
        self.hass = hass
        self._last_calculation = {}

        # Listen to calculation events
        self.hass.bus.async_listen(EVENT_CALCULATION_COMPLETE, self._calculation_event)

    @callback
    def _calculation_event(self, event: Event) -> None:
        """Handle calculation complete event."""
        self._last_calculation = event.data
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """Return adjustment summary."""
        if not self._last_calculation:
            return "Waiting for calculation"
        
        final_brightness = self._last_calculation.get("final_brightness_adjustment", 0)
        final_warmth = self._last_calculation.get("final_warmth_adjustment", 0)
        
        if final_brightness == 0 and final_warmth == 0:
            return "No adjustment"
        
        parts = []
        if final_brightness != 0:
            parts.append(f"{final_brightness:+d}% brightness")
        if final_warmth != 0:
            parts.append(f"{final_warmth:+d}K warmth")
        
        return ", ".join(parts)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return last calculation details."""
        if not self._last_calculation:
            return {"last_calculation": None}
        
        return {
            "last_calculation": self._last_calculation.get("timestamp"),
            "trigger_source": self._last_calculation.get("trigger_source"),
            "final_adjustments": {
                "brightness": self._last_calculation.get("final_brightness_adjustment"),
                "warmth": self._last_calculation.get("final_warmth_adjustment"),
            },
            "component_breakdown": self._last_calculation.get("components", {}),
            "sun_elevation": self._last_calculation.get("sun_elevation"),
            "environmental_active": self._last_calculation.get("environmental_active"),
            "zones_affected": self._last_calculation.get("zones_updated", []),
            "capping_occurred": len(self._last_calculation.get("expired_timers", [])) > 0,  # Placeholder
        }


class ZoneManualControlSensor(ALPEntity, SensorEntity):
    """Per-zone manual control status sensor."""

    _attr_icon = "mdi:hand-back-right"

    def __init__(self, coordinator, config_entry, zone_id: str):
        """Initialize zone manual control sensor."""
        super().__init__(
            coordinator,
            config_entry,
            "sensor",
            f"manual_control_{zone_id}",
            f"{zone_id.replace('_', ' ').title()} Manual Control"
        )
        self._zone_id = zone_id

    @property
    def native_value(self) -> str:
        """Return manual control status."""
        if not self.coordinator.data:
            return "Unknown"
        
        zones = self.coordinator.data.get("zones", {})
        zone_data = zones.get(self._zone_id, {})
        
        manual_active = zone_data.get("manual_control_active", False)
        if not manual_active:
            return "No manual control"
        
        lights_count = zone_data.get("lights_on_count", 0)
        return f"{lights_count} lights manually controlled"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return manual control details."""
        if not self.coordinator.data:
            return {}
        
        zones = self.coordinator.data.get("zones", {})
        zone_data = zones.get(self._zone_id, {})
        zone_config = self.coordinator.zones.get(self._zone_id, {})

        timer_remaining = zone_data.get("timer_remaining", 0)
        timer_remaining_display = self._format_time_remaining(timer_remaining)

        return {
            "manual_control_active": zone_data.get("manual_control_active", False),
            "timer_remaining_seconds": timer_remaining,
            "timer_remaining": timer_remaining_display,
            "timer_finishes_at": zone_data.get("timer_finishes_at"),
            "controlled_lights": zone_config.get("lights", []),
        }

    def _format_time_remaining(self, seconds: float) -> str:
        """Format seconds into human-readable time."""
        if seconds <= 0:
            return "Expired"
        elif seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"


class TotalManualControlSensor(ALPEntity, SensorEntity):
    """Aggregate sensor - total manual control zones."""

    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry):
        """Initialize total manual control sensor."""
        super().__init__(coordinator, config_entry, "sensor", "total_manual_control", "ALP Total Manual Control")

    @property
    def native_value(self) -> int:
        """Return count of zones with manual control active."""
        if not self.coordinator.data:
            return 0
        
        zones = self.coordinator.data.get("zones", {})
        return sum(1 for zone in zones.values() if zone.get("manual_control_active", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return breakdown."""
        if not self.coordinator.data:
            return {}
        
        zones = self.coordinator.data.get("zones", {})
        active_zones = [
            zone_id for zone_id, zone in zones.items()
            if zone.get("manual_control_active", False)
        ]
        
        return {
            "active_zones": active_zones,
            "total_zones": len(zones),
        }


class ZonesWithManualControlSensor(ALPEntity, SensorEntity):
    """List of zones with active manual control."""

    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, coordinator, config_entry):
        """Initialize zones with manual control sensor."""
        super().__init__(coordinator, config_entry, "sensor", "zones_with_manual_control", "ALP Zones With Manual Control")

    @property
    def native_value(self) -> str:
        """Return comma-separated list of zones."""
        if not self.coordinator.data:
            return "None"
        
        zones = self.coordinator.data.get("zones", {})
        active_zones = [
            zone_id.replace("_", " ").title()
            for zone_id, zone in zones.items()
            if zone.get("manual_control_active", False)
        ]
        
        return ", ".join(active_zones) if active_zones else "None"


class DeviationTrackerSensor(ALPEntity, SensorEntity):
    """Track deviation from baseline adaptive lighting."""

    _attr_icon = "mdi:chart-line-variant"

    def __init__(self, coordinator, config_entry):
        """Initialize deviation tracker."""
        super().__init__(coordinator, config_entry, "sensor", "deviation_tracker", "ALP Deviation Tracker")

    @property
    def native_value(self) -> str:
        """Return deviation classification."""
        if not self.coordinator.data:
            return "Unknown"
        
        global_data = self.coordinator.data.get("global", {})
        brightness_dev = abs(global_data.get("total_brightness_adjustment", 0))
        warmth_dev = abs(global_data.get("total_warmth_adjustment", 0)) // 500  # Scale to percentage
        
        total_deviation = brightness_dev + warmth_dev
        
        if total_deviation == 0:
            return "No deviation"
        elif total_deviation < 15:
            return "Minor"
        elif total_deviation < 30:
            return "Moderate"
        else:
            return "Significant"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return deviation details."""
        if not self.coordinator.data:
            return {}
        
        global_data = self.coordinator.data.get("global", {})
        return {
            "brightness_deviation": global_data.get("total_brightness_adjustment", 0),
            "warmth_deviation": global_data.get("total_warmth_adjustment", 0),
            "total_deviation_score": abs(global_data.get("total_brightness_adjustment", 0)) + 
                                    abs(global_data.get("total_warmth_adjustment", 0)) // 500,
        }


class SystemHealthSensor(ALPEntity, SensorEntity):
    """System health sensor with comprehensive scoring."""

    _attr_icon = "mdi:shield-check"

    def __init__(self, coordinator, config_entry):
        """Initialize system health sensor."""
        super().__init__(coordinator, config_entry, "sensor", "system_health", "ALP System Health")

    @property
    def native_value(self) -> str:
        """Return health status."""
        if not self.coordinator.data:
            return "Unknown"
        
        score = self._calculate_health_score()
        
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 50:
            return "Fair"
        else:
            return "Poor"

    def _calculate_health_score(self) -> int:
        """Calculate health score 0-100."""
        if not self.coordinator.data:
            return 0
        
        score = 100
        zones = self.coordinator.data.get("zones", {})
        
        # Deduct for unavailable switches
        offline_switches = sum(1 for zone in zones.values() if not zone.get("adaptive_lighting_active"))
        score -= offline_switches * 15
        
        # Deduct for boundary collapses
        collapses = sum(1 for zone in zones.values() 
                       if zone.get("computed_brightness_range", {}).get("boundary_collapsed", False))
        score -= collapses * 20
        
        # Deduct if environmental sensors unavailable
        env_data = self.coordinator.data.get("environmental", {})
        if env_data.get("current_lux", 0) == 0:
            score -= 10  # Lux sensor might be unavailable
        
        return max(0, min(100, score))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return health details."""
        if not self.coordinator.data:
            return {}
        
        zones = self.coordinator.data.get("zones", {})
        online_switches = [zone_id for zone_id, zone in zones.items() if zone.get("adaptive_lighting_active")]
        
        return {
            "health_score": self._calculate_health_score(),
            "switches_online": len(online_switches),
            "total_switches": len(zones),
            "online_switch_ids": online_switches,
            "last_successful_adjustment": self.coordinator.last_update_success_time.isoformat() if self.coordinator.last_update_success_time else None,
            "environmental_sensors_status": "OK" if self.coordinator.data.get("environmental", {}).get("current_lux", 0) > 0 else "Degraded",
            "boundary_collapse_warnings": [
                zone_id for zone_id, zone in zones.items()
                if zone.get("computed_brightness_range", {}).get("boundary_collapsed", False)
            ],
        }


class PerformanceMetricsSensor(ALPEntity, SensorEntity):
    """Track performance metrics."""

    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_performance_metrics"
        self._attr_name = "ALP Performance Metrics"
        self._last_update_count = 0
        self._daily_updates = []

    @property
    def native_value(self):
        return "Active" if self.coordinator.last_updated else "Idle"

    @property
    def extra_state_attributes(self):
        # Track daily automation counts
        today_count = len([t for t in self._daily_updates
                          if t.date() == dt.datetime.now().date()])

        return {
            "last_calculation": self.coordinator.last_updated,
            "total_automations_today": today_count,
            "avg_lights_per_zone": len(self.coordinator.zones),
            "response_time_ms": self.coordinator.data.get("last_update_duration_ms", 0)
        }


class UsageStatisticsSensor(ALPEntity, SensorEntity):
    """Track usage patterns and statistics."""

    _attr_icon = "mdi:chart-timeline-variant"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_usage_statistics"
        self._attr_name = "ALP Usage Statistics"
        self._mode_start_time = dt.datetime.now()
        self._current_mode = "auto"

    @property
    def native_value(self):
        duration = (dt.datetime.now() - self._mode_start_time).total_seconds() / 3600
        return f"{duration:.1f} hours in {self._current_mode}"

    @property
    def extra_state_attributes(self):
        scene = self.coordinator.get_current_scene()
        if scene != self._current_mode:
            self._mode_start_time = dt.datetime.now()
            self._current_mode = scene

        return {
            "current_mode": scene,
            "mode_duration_hours": (dt.datetime.now() - self._mode_start_time).total_seconds() / 3600,
            "total_brightness_changes_today": self.coordinator.data.get("brightness_changes_today", 0),
            "total_warmth_changes_today": self.coordinator.data.get("warmth_changes_today", 0),
            "environmental_boosts_today": self.coordinator.data.get("env_boosts_today", 0)
        }


class ActiveLightsCountSensor(ALPEntity, SensorEntity):
    """Count active lights with details."""

    _attr_icon = "mdi:lightbulb"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry, hass):
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_active_lights_count"
        self._attr_name = "ALP Active Lights Count"
        self.hass = hass

    @property
    def native_value(self):
        lights_on = [e for e in self.hass.states.async_all("light")
                    if e.state == "on"]
        return len(lights_on)

    @property
    def extra_state_attributes(self):
        lights_on = [e.entity_id for e in self.hass.states.async_all("light")
                    if e.state == "on"]
        return {
            "lights_on": lights_on,
            "count_by_zone": self._count_by_zone(lights_on)
        }

    def _count_by_zone(self, lights_on):
        zone_counts = {}
        for zone_id, zone in self.coordinator.zones.items():
            zone_lights = zone.get("lights", [])
            count = len([l for l in zone_lights if l in lights_on])
            if count > 0:
                zone_counts[zone_id] = count
        return zone_counts


class ManualAdjustmentStatusSensor(ALPEntity, SensorEntity):
    """Quick manual adjustment status."""

    _attr_icon = "mdi:timer-cog-outline"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_manual_adjustment_status"
        self._attr_name = "ALP Manual Adjustment Status"

    @property
    def native_value(self):
        active_zones = len(self.coordinator.get_manual_control_zones())
        b_adj = self.coordinator.get_brightness_adjustment()
        w_adj = self.coordinator.get_warmth_adjustment()

        if active_zones > 0:
            return f"{active_zones} zone(s) manual"
        elif b_adj != 0 or w_adj != 0:
            return "Adjustments applied"
        else:
            return "No adjustments"

    @property
    def extra_state_attributes(self):
        return {
            "zones_with_manual": list(self.coordinator.get_manual_control_zones()),
            "brightness_adjustment": f"{self.coordinator.get_brightness_adjustment()}%",
            "warmth_adjustment": f"{self.coordinator.get_warmth_adjustment()}K"
        }


class BrightnessStatusSensor(ALPEntity, SensorEntity):
    """Human-readable brightness status."""

    _attr_icon = "mdi:brightness-percent"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_brightness_status"
        self._attr_name = "ALP Brightness Status"

    @property
    def native_value(self):
        adj = self.coordinator.get_brightness_adjustment()
        if adj > 0:
            return f"+{adj}% brighter"
        elif adj < 0:
            return f"{adj}% dimmer"
        else:
            return "Default brightness"


class WakeSequenceStatusSensor(ALPEntity, SensorEntity):
    """Comprehensive wake sequence status with progress tracking."""

    _attr_icon = "mdi:alarm"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_wake_sequence_status"
        self._attr_name = "ALP Wake Sequence Status"

    @property
    def native_value(self):
        """Current wake sequence state."""
        wake_data = self.coordinator.data.get("wake_sequence", {})

        if wake_data.get("active"):
            start_time = wake_data.get("start_time")
            duration = wake_data.get("duration_minutes", 30)
            if start_time:
                elapsed = (dt.datetime.now() - start_time).total_seconds() / 60
                progress = min(100, (elapsed / duration) * 100)
                return f"Active ({progress:.0f}% complete)"
            return "Active"

        next_alarm = wake_data.get("next_alarm")
        if next_alarm:
            return f"Scheduled for {next_alarm.strftime('%I:%M %p')}"

        return "Not Scheduled"

    @property
    def extra_state_attributes(self):
        """Detailed wake sequence information."""
        wake_data = self.coordinator.data.get("wake_sequence", {})

        attrs = {
            "active": wake_data.get("active", False),
            "zones_in_wake": list(self.coordinator.get_wake_active_zones()),
            "duration_minutes": wake_data.get("duration_minutes", 30),
            "current_offset": wake_data.get("current_offset", 0)
        }

        if wake_data.get("next_alarm"):
            attrs["next_alarm"] = wake_data["next_alarm"].isoformat()
            attrs["time_until_alarm"] = str(wake_data["next_alarm"] - dt.datetime.now())

        if wake_data.get("start_time"):
            attrs["start_time"] = wake_data["start_time"].isoformat()
            attrs["elapsed_minutes"] = (dt.datetime.now() - wake_data["start_time"]).total_seconds() / 60

        return attrs


# ==================== PHASE 7: ADDITIONAL DIAGNOSTIC SENSORS ====================


class ALPLastActionSensor(ALPEntity, SensorEntity):
    """Sensor tracking the last action taken by the system.

    Critical for debugging: "Why did my lights just change?"
    """

    _attr_icon = "mdi:history"

    def __init__(self, coordinator, config_entry):
        """Initialize last action sensor."""
        super().__init__(coordinator, config_entry, "sensor", "last_action", "ALP Last Action")
        self._last_action = "System initialized"
        self._last_action_time = dt.datetime.now()

    @property
    def native_value(self) -> str:
        """Return last action taken."""
        # Get last action from coordinator data if available
        if self.coordinator.data:
            global_data = self.coordinator.data.get("global", {})
            last_action = global_data.get("last_action", self._last_action)
            if last_action != self._last_action:
                self._last_action = last_action
                self._last_action_time = dt.datetime.now()

        return self._last_action

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return last action details."""
        time_since = (dt.datetime.now() - self._last_action_time).total_seconds()

        return {
            "action": self._last_action,
            "timestamp": self._last_action_time.isoformat(),
            "seconds_ago": int(time_since),
            "time_ago_human": self._format_time_ago(time_since),
        }

    def _format_time_ago(self, seconds: float) -> str:
        """Format seconds into human-readable time ago."""
        if seconds < 60:
            return f"{int(seconds)} seconds ago"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{int(minutes)} minutes ago"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{int(hours)} hours ago"
        else:
            days = seconds / 86400
            return f"{int(days)} days ago"


class ALPTimerStatusSensor(ALPEntity, SensorEntity):
    """Sensor showing summary of all active manual timers.

    Dashboard visibility: "Which zones have active timers?"
    """

    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator, config_entry):
        """Initialize timer status sensor."""
        super().__init__(coordinator, config_entry, "sensor", "timer_status", "ALP Manual Timer Status")

    @property
    def native_value(self) -> str:
        """Return count of active timers."""
        if not self.coordinator.data:
            return "No Active Timers"

        zones = self.coordinator.data.get("zones", {})
        active_count = sum(
            1 for zone in zones.values()
            if zone.get("manual_control_active", False) and zone.get("timer_remaining", 0) > 0
        )

        if active_count == 0:
            return "No Active Timers"
        elif active_count == 1:
            return "1 Active Timer"
        else:
            return f"{active_count} Active Timers"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return per-zone timer details."""
        if not self.coordinator.data:
            return {}

        zones = self.coordinator.data.get("zones", {})
        timers = {}

        for zone_id, zone_data in zones.items():
            if zone_data.get("manual_control_active", False):
                remaining = zone_data.get("timer_remaining", 0)
                if remaining and remaining > 0:
                    minutes = remaining / 60
                    timers[zone_id] = {
                        "remaining_seconds": int(remaining),
                        "remaining_minutes": round(minutes, 1),
                        "remaining_human": self._format_time_remaining(remaining),
                        "finishes_at": zone_data.get("timer_finishes_at"),
                    }

        return {
            "active_zones": list(timers.keys()),
            "timer_details": timers,
            "total_active": len(timers),
        }

    def _format_time_remaining(self, seconds: float) -> str:
        """Format seconds into human-readable time remaining."""
        if seconds <= 0:
            return "Expired"
        elif seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} min"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hr"


class ALPZoneHealthSensor(ALPEntity, SensorEntity):
    """Sensor showing health status of all zones.

    System health: "Are all zones configured correctly?"
    """

    _attr_icon = "mdi:heart-pulse"

    def __init__(self, coordinator, config_entry):
        """Initialize zone health sensor."""
        super().__init__(coordinator, config_entry, "sensor", "zone_health", "ALP Zone Health")

    @property
    def native_value(self) -> str:
        """Return overall health status."""
        if not self.coordinator.data:
            return "Unknown"

        zones = self.coordinator.data.get("zones", {})

        # Count healthy zones (AL switch online and responding)
        healthy = sum(
            1 for zone in zones.values()
            if zone.get("adaptive_lighting_active", False)
        )
        total = len(zones)

        if healthy == total:
            return "All Zones Healthy"
        elif healthy == 0:
            return "All Zones Unavailable"
        else:
            return f"{healthy}/{total} Zones Healthy"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return per-zone health details."""
        if not self.coordinator.data:
            return {}

        zones = self.coordinator.data.get("zones", {})
        health = {}

        for zone_id, zone_data in zones.items():
            zone_config = self.coordinator.zones.get(zone_id, {})

            # Check health criteria
            al_switch = zone_config.get("adaptive_lighting_switch")
            al_active = zone_data.get("adaptive_lighting_active", False)
            lights = zone_config.get("lights", [])
            brightness_min = zone_config.get("brightness_min", 0)
            brightness_max = zone_config.get("brightness_max", 100)

            health[zone_id] = {
                "available": al_active,
                "al_switch": al_switch,
                "al_switch_online": al_active,
                "lights_configured": len(lights),
                "light_entities": lights,
                "boundary_valid": brightness_min < brightness_max,
                "brightness_range": f"{brightness_min}% - {brightness_max}%",
            }

        healthy_count = sum(1 for h in health.values() if h["available"])

        return {
            "zones": health,
            "healthy_count": healthy_count,
            "total_zones": len(health),
            "unhealthy_zones": [zone_id for zone_id, h in health.items() if not h["available"]],
        }
