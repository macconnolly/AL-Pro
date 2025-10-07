"""Sensor platform for Adaptive Lighting Pro."""
from __future__ import annotations

from typing import Any, Dict, Callable, List, Optional

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ANALYTICS_SENSOR_ID,
    DOMAIN,
    HEALTH_SENSOR_ID,
    REALTIME_SENSOR_ID,
    STATUS_SENSOR_ID,
    SONOS_ANCHOR_SENSOR_ID,
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
        AdaptiveLightingProSonosAnchorSensor(runtime),
        AdaptiveLightingProStatusSensor(runtime),
        AdaptiveLightingProRealtimeSensor(runtime),
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


class AdaptiveLightingProSonosAnchorSensor(
    AdaptiveLightingProEntity, SensorEntity
):
    """Expose upcoming sunrise anchor timestamp."""

    _attr_entity_id = SONOS_ANCHOR_SENSOR_ID
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Sunrise Anchor", SONOS_ANCHOR_SENSOR_ID)

    @property
    def native_value(self) -> datetime | None:
        snapshot = self._runtime.sonos_anchor_snapshot()
        return snapshot.get("anchor")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        snapshot = self._runtime.sonos_anchor_snapshot().copy()
        anchor = snapshot.pop("anchor", None)
        snapshot["anchor_iso"] = anchor.isoformat() if anchor else None
        return snapshot


class AdaptiveLightingProStatusSensor(AdaptiveLightingProEntity, SensorEntity):
    """Replicate legacy status template sensor."""

    _attr_entity_id = STATUS_SENSOR_ID

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Status", STATUS_SENSOR_ID)

    @property
    def native_value(self) -> str:
        if self._runtime.globally_paused():
            return "Globally Paused"
        mode = self._runtime.current_mode()
        scene = self._runtime.current_scene()
        manual_brightness = self._runtime.manual_brightness_total()
        manual_warmth = self._runtime.manual_warmth_total()
        env = self._runtime.environmental_summary()
        active = []
        if manual_brightness > 0:
            active.append("manual_brighter")
        elif manual_brightness < 0:
            active.append("manual_dimmer")
        if manual_warmth > 0:
            active.append("manual_cooler")
        elif manual_warmth < 0:
            active.append("manual_warmer")
        if env.get("active"):
            active.append("environmental_boost")
        scene_offsets = self._runtime.scene_offsets()
        if scene_offsets.get("brightness") or scene_offsets.get("warmth"):
            active.append("scene_offset")
        if self._runtime.sunset_active():
            active.append("sunset_fade")
        if mode == "movie":
            return "Movie Mode"
        if mode == "work":
            return "Work Mode"
        if mode == "late_night":
            return "Late Night Mode"
        if mode == "focus":
            return "Bright Focus" + (f" (+{manual_brightness}%)" if manual_brightness > 0 else "")
        if mode == "relax":
            return "Dim Relax" + (f" ({manual_brightness}%)" if manual_brightness < 0 else "")
        if env.get("active"):
            boost = env.get("boost_pct", 0)
            return f"Environmental Boost (+{boost}%)"
        if manual_brightness or manual_warmth:
            parts = []
            if manual_brightness:
                parts.append(f"{manual_brightness}%")
            if manual_warmth:
                parts.append(f"{manual_warmth}K")
            return f"Manual Adjusted ({', '.join(parts)})"
        if scene != "default":
            return f"Scene: {scene.replace('_', ' ').title()}"
        return "Adaptive Auto"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {}
        runtime = self._runtime
        manual_brightness = runtime.manual_brightness_total()
        manual_warmth = runtime.manual_warmth_total()
        env = runtime.environmental_summary()
        scene_offsets = runtime.scene_offsets()
        attrs["active_modifiers"] = self._active_modifiers(
            manual_brightness, manual_warmth, env, scene_offsets
        )
        last_action, last_time = self._last_action_details()
        attrs["last_action"] = last_action
        attrs["last_action_time"] = last_time
        attrs["system_health"] = self._system_health()
        attrs["current_adjustments"] = runtime.adjustment_breakdown()
        attrs["active_scene"] = runtime.current_scene()
        timers = runtime.zone_timer_snapshot()
        active_timers = [zone for zone, data in timers.items() if data.get("remaining", 0)]
        attrs["manual_timer_remaining"] = f"{len(active_timers)} zone(s) active" if active_timers else "Not Active"
        attrs["environmental_boost_active"] = bool(env.get("active"))
        attrs["next_timer_expiry"] = self._next_timer_expiry(timers)
        attrs["managed_zones"] = len(runtime.zone_states())
        attrs["active_adjustments"] = ", ".join(attrs["active_modifiers"]) if attrs["active_modifiers"] != ["none"] else "none"
        components = runtime.adjustment_breakdown()
        attrs["final_brightness_adjustment"] = components["final_brightness"]
        attrs["final_warmth_adjustment"] = components["final_warmth"]
        attrs["environmental_calculation"] = self._environmental_summary(env)
        attrs["sun_position"] = self._sun_position()
        attrs["active_switches"] = self._active_switches()
        attrs.update(self._range_attributes())
        return attrs

    def _active_modifiers(
        self,
        manual_brightness: int,
        manual_warmth: int,
        env: Dict[str, Any],
        scene_offsets: Dict[str, int],
    ) -> List[str]:
        modifiers: List[str] = []
        if manual_brightness > 0:
            modifiers.append("manual_brighter")
        elif manual_brightness < 0:
            modifiers.append("manual_dimmer")
        if manual_warmth > 0:
            modifiers.append("manual_cooler")
        elif manual_warmth < 0:
            modifiers.append("manual_warmer")
        if env.get("active"):
            modifiers.append("environmental_boost")
        if scene_offsets.get("brightness") or scene_offsets.get("warmth"):
            modifiers.append("scene_offset")
        if self._runtime.sunset_active():
            modifiers.append("sunset_fade")
        return modifiers or ["none"]

    def _last_action_details(self) -> tuple[str, str]:
        history = self._runtime.manual_action_history()
        candidates: List[tuple[datetime, str]] = []
        for action, when in history.items():
            if when:
                candidates.append((when, action))
        mode_change = self._runtime.last_mode_change()
        if mode_change:
            candidates.append((mode_change, f"mode:{self._runtime.current_mode()}"))
        scene_change = self._runtime.last_scene_change()
        if scene_change:
            candidates.append((scene_change, f"scene:{self._runtime.current_scene()}"))
        if not candidates:
            return "Unknown", "Never"
        latest = max(candidates, key=lambda item: item[0])
        return latest[1], latest[0].isoformat()

    def _system_health(self) -> str:
        switches = []
        for data in self._runtime.zone_states().values():
            entity_id = data.get("al_switch")
            if entity_id:
                switches.append(self.hass.states.get(entity_id))
        available = [state for state in switches if state and state.state != "unavailable"]
        if not switches:
            return "Unknown"
        if len(available) == len(switches):
            return "Normal"
        if available:
            return f"Degraded ({len(available)}/{len(switches)} switches)"
        return "Offline"

    def _environmental_summary(self, env: Dict[str, Any]) -> str:
        if not env.get("active"):
            return "Idle"
        lux = env.get("lux")
        weather = env.get("weather")
        boost = env.get("boost_pct", 0)
        return f"Lux: {lux} Weather: {weather} Boost: {boost}%"

    def _sun_position(self) -> str:
        sun = self.hass.states.get("sun.sun")
        if not sun:
            return "Unknown"
        elevation = float(sun.attributes.get("elevation", 0))
        if elevation < -4:
            phase = "Night"
        elif -4 <= elevation < 0:
            phase = "Sunset/Sunrise"
        elif 0 <= elevation < 10:
            phase = "Golden Hour"
        else:
            phase = "Day"
        return f"{phase} ({elevation:.1f}°)"

    def _active_switches(self) -> str:
        names = []
        for zone_id, data in self._runtime.zone_states().items():
            entity_id = data.get("al_switch")
            state = self.hass.states.get(entity_id) if entity_id else None
            if state and state.state == "on":
                friendly = getattr(state, "name", None)
                if not friendly:
                    friendly = state.attributes.get("friendly_name") if hasattr(state, "attributes") else None
                names.append(str(friendly) if friendly else zone_id)
        return ", ".join(names) if names else "None"

    def _range_attributes(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        boundaries = self._runtime.zone_boundaries()
        components = self._runtime.adjustment_breakdown()
        final_brightness = components["final_brightness"]
        final_warmth = components["final_warmth"]
        brightness_ranges = {}
        warmth_ranges = {}
        for zone_id, values in boundaries.items():
            baseline = values.get("baseline", {})
            current = values.get("current", {})
            if baseline and current:
                brightness_ranges[zone_id] = (
                    f"{current.get('min_brightness')}%-{current.get('max_brightness')}%"
                    f" (baseline {baseline.get('min_brightness')}%-{baseline.get('max_brightness')}%)"
                )
                warmth_ranges[zone_id] = (
                    f"{baseline.get('min_color_temp')}K-{baseline.get('max_color_temp')}K"
                    f" (+{final_warmth}K)"
                )
        data["computed_brightness_ranges"] = brightness_ranges
        data["computed_warmth_ranges"] = warmth_ranges
        return data

    def _next_timer_expiry(
        self, timers: Dict[str, Dict[str, int | datetime | None]]
    ) -> str:
        schedule: List[tuple[datetime, str]] = []
        for zone_id, values in timers.items():
            expires = values.get("expires_at")
            if isinstance(expires, datetime):
                schedule.append((expires, zone_id))
        if not schedule:
            return "Not set"
        next_zone = min(schedule, key=lambda item: item[0])
        local_time = dt_util.as_local(next_zone[0])
        return f"{next_zone[1]} @ {local_time.strftime('%H:%M')}"


class AdaptiveLightingProRealtimeSensor(AdaptiveLightingProEntity, SensorEntity):
    """Expose calculation heartbeat similar to legacy event sensor."""

    _attr_entity_id = REALTIME_SENSOR_ID

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Real-Time Monitor", REALTIME_SENSOR_ID)
        self._state = "Baseline"
        self._attrs: Dict[str, Any] = {}
        self._unsubscribe: Optional[Callable[[], None]] = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsubscribe = self.hass.bus.async_listen(
            "adaptive_lighting_calculation_complete", self._handle_event
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
        await super().async_will_remove_from_hass()

    async def _handle_event(self, event) -> None:
        data = getattr(event, "data", {}) or {}
        brightness = int(data.get("final_brightness_adjustment", 0) or 0)
        warmth = int(data.get("final_warmth_adjustment", 0) or 0)
        if brightness > 0:
            self._state = f"Brightened +{brightness}%"
        elif brightness < 0:
            self._state = f"Dimmed {brightness}%"
        elif warmth:
            self._state = f"Warmth {warmth}K"
        else:
            self._state = "Baseline"
        self._attrs = {
            "timestamp": data.get("timestamp"),
            "trigger_source": data.get("trigger_source"),
            "final_brightness_adjustment": brightness,
            "final_warmth_adjustment": warmth,
            "components": data.get("components", {}),
            "environmental_active": data.get("environmental_active"),
            "environmental": data.get("environmental"),
            "zones_updated": data.get("zones_updated", []),
            "zones_calculated": data.get("zones_calculated", []),
            "mode": data.get("mode"),
            "scene": data.get("scene"),
        }
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._attrs
