"""Runtime orchestration for Adaptive Lighting Pro."""
from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from ..const import (
    CONF_CONTROLLERS,
    CONF_DEBUG,
    CONF_FORCE_APPLY,
    CONF_ENV_BOOST,
    CONF_NIGHTLY_SWEEP,
    CONF_OPTIONS_MODE_MULTIPLIERS,
    CONF_PER_ZONE_OVERRIDES,
    CONF_RATE_LIMIT,
    CONF_SCENES,
    CONF_SENSORS,
    CONF_SONOS_SETTINGS,
    CONF_TIMEOUTS,
    CONF_WATCHDOG,
    CONF_ZONES,
    DEFAULT_DEBUG_CONFIG,
    DEFAULT_MODE_MULTIPLIERS,
    DEFAULT_NIGHTLY_SWEEP_TIME,
    DEFAULT_RATE_LIMIT_MAX_EVENTS,
    DEFAULT_RATE_LIMIT_WINDOW,
    DEFAULT_SCENE_ORDER,
    DEFAULT_SCENE_PRESETS,
    DEFAULT_WATCHDOG_INTERVAL_MIN,
    DEFAULT_FORCE_APPLY,
    DEFAULT_ENV_MULTIPLIER_BOOST,
    DEFAULT_BRIGHTNESS_STEP,
    DEFAULT_COLOR_TEMP_STEP,
    MODE_ALIASES,
    DOMAIN,
    EVENT_MANUAL_DETECTED,
    EVENT_MANUAL_RELEASED,
    EVENT_ENVIRONMENTAL_CHANGED,
    EVENT_MODE_CHANGED,
    EVENT_RESET_REQUESTED,
    EVENT_SCENE_CHANGED,
    EVENT_SYNC_REQUIRED,
    EVENT_TIMER_EXPIRED,
    EVENT_STARTUP_COMPLETE,
    EVENT_BUTTON_PRESSED,
    RETRY_ATTEMPTS,
    RETRY_BACKOFFS,
    SERVICE_ADJUST,
    SERVICE_BACKUP_PREFS,
    SERVICE_DISABLE_ZONE,
    SERVICE_ENABLE_ZONE,
    SERVICE_FORCE_SYNC,
    SERVICE_RESET_ZONE,
    SERVICE_RESTORE_PREFS,
    SERVICE_SET_ZONE_BOOST,
    SERVICE_SKIP_NEXT_ALARM,
    SERVICE_SELECT_MODE,
    SERVICE_SELECT_SCENE,
    SYNC_TRANSITION_SEC,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)
from ..devices.zen32_handler import Zen32Config, Zen32Handler
from ..features.environmental import EnvironmentalConfig, EnvironmentalObserver
from ..features.manual_control import ManualControlConfig, ManualControlObserver
from ..features.modes import ModeManager
from ..features.scenes import SceneConfig, SceneManager
from ..features.sonos_integration import (
    SonosAnchorSnapshot,
    SonosConfig,
    SonosSunriseCoordinator,
)
from ..robustness.rate_limiter import RateLimitConfig, RateLimiter
from ..robustness.retry_manager import RetryManager
from ..robustness.watchdog import Watchdog
from ..utils.metrics import MetricsRegistry
from ..utils.statistics import DailyCounters
from ..utils.storage import StorageAdapter
from ..utils.validators import validate_mode, validate_scene
from .event_bus import EventBus
from .executors import ExecutorManager
from .health_monitor import HealthMonitor
from .timer_manager import TimerManager
from .zone_manager import ZoneConfig, ZoneManager


_LOGGER = logging.getLogger(__name__)


class AdaptiveLightingProRuntime:
    """Main runtime orchestrator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._data = dict(entry.data)
        self._options = dict(entry.options)
        self._debug_config = self._options.get(CONF_DEBUG, DEFAULT_DEBUG_CONFIG)
        self._trace_enabled = bool(self._debug_config.get("trace_logbook", False))
        self._metrics = MetricsRegistry()
        self._counters = DailyCounters()
        self._health_monitor = HealthMonitor(self._metrics, self._counters)
        self._event_bus = EventBus(
            hass,
            debug=bool(self._debug_config.get("debug_log", False)),
            trace=self._trace_enabled,
        )
        self._storage = StorageAdapter(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}_{entry.entry_id}",
        )
        self._state_save_task: asyncio.Task | None = None
        self._timer_manager = TimerManager(
            hass, self._event_bus, debug=bool(self._debug_config.get("debug_log", False))
        )
        self._zone_manager = ZoneManager(self._timer_manager)
        rate_conf = self._options.get(
            CONF_RATE_LIMIT,
            {"max_events": DEFAULT_RATE_LIMIT_MAX_EVENTS, "window_sec": DEFAULT_RATE_LIMIT_WINDOW},
        )
        self._rate_limiter = RateLimiter(
            RateLimitConfig(
                max_events=int(rate_conf.get("max_events", DEFAULT_RATE_LIMIT_MAX_EVENTS)),
                window_sec=int(rate_conf.get("window_sec", DEFAULT_RATE_LIMIT_WINDOW)),
            )
        )
        self._retry = RetryManager(RETRY_ATTEMPTS, RETRY_BACKOFFS)
        self._executors = ExecutorManager(
            hass,
            rate_limiter=self._rate_limiter,
            retry_manager=self._retry,
            debug=bool(self._debug_config.get("debug_log", False)),
        )
        self._mode_manager = ModeManager(self._event_bus, self._timer_manager)
        scenes_options = self._options.get(CONF_SCENES, {})
        order = list(scenes_options.get("order", DEFAULT_SCENE_ORDER))
        preset_overrides = scenes_options.get("presets", {})
        self._scene_presets = self._build_scene_presets(preset_overrides)
        offsets_options = scenes_options.get("offsets", {})
        self._scene_offset_user = {
            "brightness": int(offsets_options.get("brightness", 0) or 0),
            "warmth": int(offsets_options.get("warmth", 0) or 0),
        }
        self._scene_offsets = {"brightness": 0, "warmth": 0}
        self._manual_action_flags: Dict[str, bool] = {
            "brighter": False,
            "dimmer": False,
            "warmer": False,
            "cooler": False,
        }
        self._scene_manager = SceneManager(
            hass,
            self._event_bus,
            self._executors,
            self._zone_manager,
            self._timer_manager,
            SceneConfig(
                order=order,
                force_apply=bool(self._options.get(CONF_FORCE_APPLY, DEFAULT_FORCE_APPLY)),
                debug=bool(self._debug_config.get("debug_log", False)),
                presets=self._scene_presets,
                user_offsets=dict(self._scene_offset_user),
                offsets_callback=self._handle_scene_offsets_changed,
                manual_action_callback=self._record_manual_action,
            ),
        )
        self._scene_manager.update_user_offsets(
            self._scene_offset_user["brightness"],
            self._scene_offset_user["warmth"],
        )
        self._manual_brightness_total = 0
        self._manual_warmth_total = 0
        self._manual_history: Dict[str, datetime | None] = {
            "brighter": None,
            "dimmer": None,
            "warmer": None,
            "cooler": None,
            "clear_brightness": None,
            "clear_warmth": None,
            "clear_all": None,
            "manual_adjust": None,
        }
        self._adjustment_components: Dict[str, int] = {
            "manual_brightness": 0,
            "manual_warmth": 0,
            "scene_brightness": 0,
            "scene_warmth": 0,
            "environmental_boost": 0,
            "sunset_boost": 0,
            "final_brightness": 0,
            "final_warmth": 0,
        }
        self._mode_aliases = dict(MODE_ALIASES)
        self._sunset_boost_pct = 0
        self._sunset_active = False
        self._zone_baselines: Dict[str, Dict[str, int]] = {}
        self._current_zone_settings: Dict[str, Dict[str, int]] = {}
        self._manual_observer: ManualControlObserver | None = None
        self._environmental: EnvironmentalObserver | None = None
        self._sonos: SonosSunriseCoordinator | None = None
        self._watchdog: Watchdog | None = None
        self._nightly_unsub: CALLBACK_TYPE | None = None
        self._entity_callbacks: List[Callable[[], None]] = []
        self._rate_limit_reached = False
        self._backup_prefs: Dict[str, Any] | None = None
        self._services_registered = False
        self._zen32: Zen32Handler | None = None
        self._previous_mode: str | None = None
        self._global_pause = False
        self._adjust_brightness_step = DEFAULT_BRIGHTNESS_STEP
        self._adjust_color_temp_step = DEFAULT_COLOR_TEMP_STEP
        self._environmental_state: Dict[str, Any] = {
            "active": False,
            "lux": None,
            "cloud_coverage": None,
            "elevation": None,
            "boost_pct": 0,
            "sunset_boost_pct": 0,
            "multiplier": 1.0,
        }
        self._last_mode_change: datetime | None = None
        self._last_scene_change: datetime | None = None
        self._last_event: Dict[str, Any] = {
            "event": "startup",
            "timestamp": dt_util.now().isoformat(),
            "details": {},
        }
        self._last_calculation_event: Dict[str, Any] = {
            "timestamp": dt_util.now().isoformat(),
            "trigger_source": "startup",
            "final_brightness_adjustment": 0,
            "final_warmth_adjustment": 0,
            "components": dict(self._adjustment_components),
            "environmental_active": False,
            "environmental": dict(self._environmental_state),
            "zones_updated": [],
            "zones_calculated": [],
            "mode": self._mode_manager.mode,
            "scene": self._scene_manager.scene,
        }
        self._recalculate_adjustments()

    async def async_setup(self) -> None:
        self._apply_zone_configuration()
        self._apply_options()
        self._register_event_handlers()
        self._setup_observers()
        self._setup_watchdog()
        self._schedule_nightly_sweep()
        self._register_services()
        await self._restore_runtime_state()
        self._event_bus.post(EVENT_STARTUP_COMPLETE)
        self._notify_entities()
        self._emit_calculation_event("startup")

    async def async_unload(self) -> None:
        await self._storage.async_save(self._serialize_runtime_state())
        if self._state_save_task and not self._state_save_task.done():
            self._state_save_task.cancel()
        self._state_save_task = None
        if self._manual_observer:
            self._manual_observer.stop()
        if self._environmental:
            self._environmental.stop()
        if self._sonos:
            self._sonos.stop()
        if self._watchdog:
            self._watchdog.stop()
        if self._nightly_unsub:
            self._nightly_unsub()
            self._nightly_unsub = None

    async def async_options_updated(self, entry: ConfigEntry) -> None:
        self._options = dict(entry.options)
        self._debug_config = self._options.get(CONF_DEBUG, DEFAULT_DEBUG_CONFIG)
        self._apply_options()
        self._notify_entities()

    def _apply_zone_configuration(self) -> None:
        zones = self._data.get(CONF_ZONES, [])
        self._zone_manager.load_zones(zones)
        self._capture_zone_baselines()

    def _apply_options(self) -> None:
        overrides = self._options.get(CONF_PER_ZONE_OVERRIDES, {})
        if overrides:
            self._zone_manager.apply_overrides(overrides)
        timeout_conf = self._options.get(
            CONF_TIMEOUTS,
            {"base_day_min": 60, "base_night_min": 180},
        )
        self._timer_manager.update_timeouts(
            day_min=int(timeout_conf.get("base_day_min", 60)),
            night_min=int(timeout_conf.get("base_night_min", 180)),
        )
        mode_mult = self._options.get(CONF_OPTIONS_MODE_MULTIPLIERS, DEFAULT_MODE_MULTIPLIERS)
        self._timer_manager.update_mode_multipliers(mode_mult)
        env_boost = float(self._options.get(CONF_ENV_BOOST, DEFAULT_ENV_MULTIPLIER_BOOST))
        self._timer_manager.set_environment_boost_factor(env_boost)
        if self._environmental:
            self._timer_manager.set_environment(self._environmental.boost_active)
        self._mode_manager.ensure_valid_mode()
        self._health_monitor.set_rate_load(self._rate_limiter.load)
        self._load_scene_options()
        sonos_options = self._options.get(CONF_SONOS_SETTINGS, {})
        if self._sonos:
            self._sonos.set_skip_next(bool(sonos_options.get("skip_next_alarm", False)))
        asyncio.create_task(self._update_zone_boundaries())
        self._notify_entities()

    def _register_event_handlers(self) -> None:
        self._event_bus.subscribe(EVENT_MANUAL_DETECTED, self._handle_manual_detected)
        self._event_bus.subscribe(EVENT_MANUAL_RELEASED, self._handle_manual_released)
        self._event_bus.subscribe(EVENT_TIMER_EXPIRED, self._handle_timer_expired)
        self._event_bus.subscribe(EVENT_SYNC_REQUIRED, self._handle_sync_required)
        self._event_bus.subscribe(EVENT_MODE_CHANGED, self._handle_mode_changed)
        self._event_bus.subscribe(EVENT_SCENE_CHANGED, self._handle_scene_changed)
        self._event_bus.subscribe(EVENT_RESET_REQUESTED, self._handle_reset_requested)
        self._event_bus.subscribe(
            EVENT_ENVIRONMENTAL_CHANGED, self._handle_environmental_changed
        )
        self._event_bus.subscribe(EVENT_BUTTON_PRESSED, self._handle_button_event)

    def _handle_sonos_skip_updated(self, skip: bool) -> None:
        sonos_options = dict(self._options.get(CONF_SONOS_SETTINGS, {}))
        if sonos_options.get("skip_next_alarm") != skip:
            sonos_options["skip_next_alarm"] = skip
            self._options[CONF_SONOS_SETTINGS] = sonos_options
            self._hass.config_entries.async_update_entry(
                self._entry, options=dict(self._options)
            )
        self._record_event("sonos_skip_updated", skip=skip)
        self._notify_entities()

    def _handle_sonos_anchor_updated(self) -> None:
        self._beat("sonos_anchor")
        if not self._sonos:
            return
        snapshot = self._sonos.anchor_snapshot()
        anchor_iso = snapshot.anchor.isoformat() if snapshot.anchor else None
        self._record_event(
            "sonos_anchor_updated",
            anchor=anchor_iso,
            source=snapshot.anchor_source,
            skip_next=snapshot.skip_next,
        )
        self._notify_entities()

    def _setup_observers(self) -> None:
        sensors = self._data.get(CONF_SENSORS, {})
        self._manual_observer = ManualControlObserver(
            self._hass,
            self._event_bus,
            self._timer_manager,
            self._zone_manager,
            ManualControlConfig(debug=bool(self._debug_config.get("debug_log", False))),
        )
        self._manual_observer.start()
        self._environmental = EnvironmentalObserver(
            self._hass,
            self._event_bus,
            self._timer_manager,
            EnvironmentalConfig(
                lux_entity=sensors.get("lux_entity"),
                weather_entity=sensors.get("weather_entity"),
                debug=bool(self._debug_config.get("debug_log", False)),
            ),
        )
        self._environmental.start()
        sonos_options = self._options.get(CONF_SONOS_SETTINGS, {})
        self._sonos = SonosSunriseCoordinator(
            self._hass,
            self._event_bus,
            self._zone_manager,
            SonosConfig(
                sensor=sensors.get("sonos_alarm_sensor"),
                skip_next_alarm=bool(sonos_options.get("skip_next_alarm", False)),
            ),
            debug=bool(self._debug_config.get("debug_log", False)),
            on_skip_updated=self._handle_sonos_skip_updated,
            on_anchor_updated=self._handle_sonos_anchor_updated,
        )
        self._sonos.start()
        controller_conf = self._data.get(CONF_CONTROLLERS, {})
        if controller_conf.get("zen32_device_id"):
            self._zen32 = Zen32Handler(
                self._hass,
                self._event_bus,
                Zen32Config(
                    device_id=controller_conf.get("zen32_device_id"),
                    debug=bool(self._debug_config.get("debug_log", False)),
                ),
            )
            self._zen32.start()

    def _setup_watchdog(self) -> None:
        interval_min = int(
            self._options.get(CONF_WATCHDOG, {}).get("interval_min", DEFAULT_WATCHDOG_INTERVAL_MIN)
        )
        interval = timedelta(minutes=interval_min)
        self._watchdog = Watchdog(
            self._hass,
            interval=interval,
            on_reset=lambda name: self._event_bus.post(EVENT_RESET_REQUESTED, scope=name),
            debug=bool(self._debug_config.get("debug_log", False)),
        )
        self._watchdog.start()
        self._beat("startup")

    def register_entity_callback(self, callback: Callable[[], None]) -> CALLBACK_TYPE:
        self._entity_callbacks.append(callback)

        def _remove() -> None:
            if callback in self._entity_callbacks:
                self._entity_callbacks.remove(callback)

        return _remove

    def device_info(self) -> Dict[str, Any]:
        """Return shared device metadata for Home Assistant entities."""

        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Adaptive Lighting Pro",
            "manufacturer": "Adaptive Lighting Community",
        }

    def _notify_entities(self) -> None:
        for callback in list(self._entity_callbacks):
            callback()

    def _beat(self, name: str) -> None:
        if self._watchdog:
            self._watchdog.beat(name)

    def _record_event(self, event: str, **details: Any) -> None:
        self._last_event = {
            "event": event,
            "timestamp": dt_util.now().isoformat(),
            "details": details,
        }

    def _schedule_state_save(self) -> None:
        if self._state_save_task and not self._state_save_task.done():
            self._state_save_task.cancel()

        async def _save() -> None:
            await asyncio.sleep(0)
            await self._storage.async_save(self._serialize_runtime_state())

        self._state_save_task = self._hass.async_create_task(_save())

    def _persist_runtime_state(self) -> None:
        self._schedule_state_save()

    def _serialize_runtime_state(self) -> Dict[str, Any]:
        return {
            "manual": self._zone_manager.manual_state_snapshot(),
            "sunset_boost_pct": self._sunset_boost_pct if self._sunset_active else 0,
        }

    def _recalculate_adjustments(self) -> None:
        env_active = bool(self._environmental_state.get("active"))
        env_boost = int(self._environmental_state.get("boost_pct") or 0)
        if not env_active:
            env_boost = 0
        sunset_boost = self._sunset_boost_pct if self._sunset_active else 0
        components = {
            "manual_brightness": int(self._manual_brightness_total),
            "manual_warmth": int(self._manual_warmth_total),
            "scene_brightness": int(self._scene_offsets.get("brightness", 0)),
            "scene_warmth": int(self._scene_offsets.get("warmth", 0)),
            "environmental_boost": int(env_boost),
            "sunset_boost": int(sunset_boost),
        }
        components["final_brightness"] = (
            components["manual_brightness"]
            + components["scene_brightness"]
            + components["environmental_boost"]
            + components["sunset_boost"]
        )
        components["final_warmth"] = (
            components["manual_warmth"] + components["scene_warmth"]
        )
        self._adjustment_components = components

    async def _restore_runtime_state(self) -> None:
        data = await self._storage.async_load()
        if not data:
            return
        manual_data = data.get("manual", {})
        restored: List[str] = []
        for zone_id, entry in manual_data.items():
            try:
                zone_conf = self._zone_manager.get_zone(zone_id)
            except KeyError:
                continue
            if not entry.get("manual_active"):
                continue
            expires_iso = entry.get("manual_expires")
            started_iso = entry.get("manual_started")
            remaining = int(entry.get("timer_remaining", 0) or 0)
            expires_at = dt_util.parse_datetime(expires_iso) if expires_iso else None
            started_at = dt_util.parse_datetime(started_iso) if started_iso else None
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt_util.UTC)
            if started_at and started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=dt_util.UTC)
            if expires_at is not None:
                remaining = max(
                    0, int((expires_at - dt_util.utcnow()).total_seconds())
                )
            if remaining <= 0:
                continue
            if expires_at is None:
                expires_at = dt_util.utcnow() + timedelta(seconds=remaining)
            self._zone_manager.set_manual(
                zone_id,
                True,
                remaining,
                started_at=started_at,
                expires_at=expires_at,
            )
            self._timer_manager.start(zone_id, remaining)
            await self._executors.set_manual_control(zone_conf.al_switch, True)
            restored.append(zone_id)
        stored_sunset = int(data.get("sunset_boost_pct", 0) or 0)
        if stored_sunset:
            self._sunset_boost_pct = stored_sunset
            self._sunset_active = stored_sunset > 0
            self._recalculate_adjustments()
        if restored:
            self._record_event("manual_restore", zones=restored)
            self._notify_entities()
            self._emit_calculation_event("manual_restore", zones=restored)
        if restored or stored_sunset:
            self._persist_runtime_state()

    def _update_manual_totals(
        self, *, brightness_delta: int = 0, warmth_delta: int = 0
    ) -> None:
        changed = False
        if brightness_delta:
            new_brightness = self._clamp(
                self._manual_brightness_total + brightness_delta, -100, 100
            )
            if new_brightness != self._manual_brightness_total:
                self._manual_brightness_total = new_brightness
                changed = True
        if warmth_delta:
            new_warmth = max(
                -4000, min(4000, self._manual_warmth_total + warmth_delta)
            )
            if new_warmth != self._manual_warmth_total:
                self._manual_warmth_total = new_warmth
                changed = True
        if changed:
            self._manual_history["manual_adjust"] = dt_util.utcnow()
            self._recalculate_adjustments()

    def _reset_manual_adjustments(self) -> None:
        if self._manual_brightness_total == 0 and self._manual_warmth_total == 0:
            return
        self._manual_brightness_total = 0
        self._manual_warmth_total = 0
        self._manual_history["clear_all"] = dt_util.utcnow()
        self._recalculate_adjustments()

    def _emit_calculation_event(
        self,
        trigger_source: str,
        *,
        zones: List[str] | None = None,
        details: Dict[str, Any] | None = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "timestamp": dt_util.utcnow().isoformat(),
            "trigger_source": trigger_source,
            "final_brightness_adjustment": self._adjustment_components.get(
                "final_brightness", 0
            ),
            "final_warmth_adjustment": self._adjustment_components.get(
                "final_warmth", 0
            ),
            "components": dict(self._adjustment_components),
            "environmental_active": bool(self._environmental_state.get("active")),
            "environmental": dict(self._environmental_state),
            "zones_updated": zones or [],
            "zones_calculated": list(self._zone_manager.as_dict().keys()),
            "mode": self._mode_manager.mode,
            "scene": self._scene_manager.scene,
        }
        if details:
            payload.update(details)
        self._last_calculation_event = dict(payload)
        self._hass.bus.async_fire("adaptive_lighting_calculation_complete", payload)

    def _handle_scene_offsets_changed(self, brightness: int, warmth: int) -> None:
        brightness = int(brightness)
        warmth = int(warmth)
        if (
            self._scene_offsets["brightness"] == brightness
            and self._scene_offsets["warmth"] == warmth
        ):
            return
        self._scene_offsets = {"brightness": brightness, "warmth": warmth}
        self._record_event(
            "scene_offsets_changed", brightness=brightness, warmth=warmth
        )
        self._recalculate_adjustments()
        self._notify_entities()
        self._emit_calculation_event("scene_offsets", zones=[])

    def _record_manual_action(self, action: str) -> None:
        now = dt_util.utcnow()
        self._manual_history[action] = now
        updated = False
        adjustments_changed = False
        if action == "brighter":
            updated |= not self._manual_action_flags["brighter"]
            self._manual_action_flags["brighter"] = True
            if self._manual_action_flags["dimmer"]:
                updated = True
            self._manual_action_flags["dimmer"] = False
        elif action == "dimmer":
            updated |= not self._manual_action_flags["dimmer"]
            self._manual_action_flags["dimmer"] = True
            if self._manual_action_flags["brighter"]:
                updated = True
            self._manual_action_flags["brighter"] = False
        elif action == "warmer":
            updated |= not self._manual_action_flags["warmer"]
            self._manual_action_flags["warmer"] = True
            if self._manual_action_flags["cooler"]:
                updated = True
            self._manual_action_flags["cooler"] = False
        elif action == "cooler":
            updated |= not self._manual_action_flags["cooler"]
            self._manual_action_flags["cooler"] = True
            if self._manual_action_flags["warmer"]:
                updated = True
            self._manual_action_flags["warmer"] = False
        elif action == "clear_brightness":
            if (
                self._manual_action_flags["brighter"]
                or self._manual_action_flags["dimmer"]
            ):
                updated = True
            self._manual_action_flags["brighter"] = False
            self._manual_action_flags["dimmer"] = False
            if self._manual_brightness_total != 0:
                self._manual_brightness_total = 0
                adjustments_changed = True
        elif action == "clear_warmth":
            if (
                self._manual_action_flags["warmer"]
                or self._manual_action_flags["cooler"]
            ):
                updated = True
            self._manual_action_flags["warmer"] = False
            self._manual_action_flags["cooler"] = False
            if self._manual_warmth_total != 0:
                self._manual_warmth_total = 0
                adjustments_changed = True
        elif action == "clear_all":
            if any(self._manual_action_flags.values()):
                updated = True
            for key in self._manual_action_flags:
                self._manual_action_flags[key] = False
            if self._manual_brightness_total or self._manual_warmth_total:
                self._manual_brightness_total = 0
                self._manual_warmth_total = 0
                adjustments_changed = True
        if adjustments_changed:
            self._recalculate_adjustments()
        if updated or adjustments_changed:
            self._notify_entities()

    def _reset_manual_flags(self, *, brightness: bool = True, warmth: bool = True) -> None:
        if brightness:
            self._record_manual_action("clear_brightness")
        if warmth:
            self._record_manual_action("clear_warmth")

    def _load_scene_options(self) -> None:
        scenes_options = self._options.get(CONF_SCENES, {})
        order = list(scenes_options.get("order", DEFAULT_SCENE_ORDER))
        self._scene_manager.update_order(order)
        overrides = scenes_options.get("presets", {})
        self._scene_presets = self._build_scene_presets(overrides)
        self._scene_manager.update_presets(self._scene_presets)
        offsets_options = scenes_options.get("offsets", {})
        self._scene_offset_user = {
            "brightness": int(offsets_options.get("brightness", 0) or 0),
            "warmth": int(offsets_options.get("warmth", 0) or 0),
        }
        self._scene_manager.update_user_offsets(
            self._scene_offset_user["brightness"],
            self._scene_offset_user["warmth"],
        )

    def _build_scene_presets(self, overrides: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        presets = {scene: deepcopy(data) for scene, data in DEFAULT_SCENE_PRESETS.items()}
        for scene, data in overrides.items():
            base = presets.setdefault(scene, {})
            if not isinstance(data, dict):
                continue
            for key, value in data.items():
                base[key] = deepcopy(value)
        return presets

    def _capture_zone_baselines(self) -> None:
        baselines: Dict[str, Dict[str, int]] = {}
        for zone in self._zone_manager.zones():
            state = self._hass.states.get(zone.al_switch)
            attrs = getattr(state, "attributes", {}) if state else {}
            baselines[zone.zone_id] = {
                "min_brightness": self._safe_int(attrs.get("min_brightness"), 1),
                "max_brightness": self._safe_int(attrs.get("max_brightness"), 100),
                "min_color_temp": self._safe_int(attrs.get("min_color_temp"), 1800),
                "max_color_temp": self._safe_int(attrs.get("max_color_temp"), 6500),
            }
        self._zone_baselines = baselines
        self._current_zone_settings = {
            zone_id: dict(values) for zone_id, values in baselines.items()
        }

    async def _update_zone_boundaries(self) -> None:
        if not self._zone_baselines:
            return
        tasks = []
        for zone in self._zone_manager.zones():
            baseline = self._zone_baselines.get(zone.zone_id)
            if not baseline:
                continue
            target = dict(baseline)
            boost = (
                self._sunset_boost_pct
                if self._sunset_active and zone.sunset_boost_enabled
                else 0
            )
            if boost > 0:
                max_allowed_min = max(
                    baseline["min_brightness"], baseline["max_brightness"] - 5
                )
                new_min = min(max_allowed_min, baseline["min_brightness"] + boost)
                target["min_brightness"] = self._safe_int(new_min, baseline["min_brightness"])
            current = self._current_zone_settings.get(zone.zone_id)
            if current == target:
                continue
            self._current_zone_settings[zone.zone_id] = target
            if self._zone_manager.manual_active(zone.zone_id):
                continue
            payload = {
                "min_brightness": target["min_brightness"],
                "max_brightness": target["max_brightness"],
                "min_color_temp": target["min_color_temp"],
                "max_color_temp": target["max_color_temp"],
                "transition": SYNC_TRANSITION_SEC,
            }
            tasks.append(
                self._executors.change_switch_settings(zone.al_switch, payload)
            )
        if tasks:
            await asyncio.gather(*tasks)

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return default

    def _resolve_mode(self, mode: str) -> str:
        if mode in self._mode_manager.available_modes():
            return mode
        if not mode:
            return mode
        normalized = mode.strip()
        if normalized in self._mode_aliases:
            return self._mode_aliases[normalized]
        lower = normalized.lower()
        for alias, target in self._mode_aliases.items():
            if alias.lower() == lower:
                return target
        return normalized

    async def _clear_manual_states(self) -> List[str]:
        cleared = self._zone_manager.clear_all_manuals()
        if cleared:
            await asyncio.gather(
                *[
                    self._executors.set_manual_control(
                        self._zone_manager.get_zone(zone_id).al_switch, False
                    )
                    for zone_id in cleared
                ]
            )
            self._previous_mode = None
            self._reset_manual_flags()
            self._reset_manual_adjustments()
            self._persist_runtime_state()
        return cleared

    async def _toggle_all_lights(self) -> None:
        lights: List[str] = []
        for zone in self._zone_manager.zones():
            lights.extend(zone.lights)
        unique = sorted({light for light in lights})
        if not unique:
            return
        await self._executors.call_light_service("toggle", {"entity_id": unique})

    async def _restore_previous_mode_if_idle(self) -> None:
        if not self._previous_mode:
            return
        if any(
            self._zone_manager.manual_active(zone.zone_id)
            for zone in self._zone_manager.zones()
        ):
            return
        self._reset_manual_adjustments()
        mode_to_restore = self._previous_mode
        self._previous_mode = None
        self._reset_manual_flags()
        if self._mode_manager.mode != mode_to_restore:
            _LOGGER.info(
                "Manual timers cleared. Restoring %s mode.",
                mode_to_restore,
            )
            await self.select_mode(mode_to_restore)

    def _schedule_nightly_sweep(self) -> None:
        if self._nightly_unsub:
            self._nightly_unsub()
        time_conf = self._options.get(CONF_NIGHTLY_SWEEP, {"time": DEFAULT_NIGHTLY_SWEEP_TIME})
        target_time = time_conf.get("time", DEFAULT_NIGHTLY_SWEEP_TIME)
        hour, minute = [int(part) for part in target_time.split(":", 1)]
        now = dt_util.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        self._nightly_unsub = async_track_point_in_time(
            self._hass, self._nightly_sweep, next_run
        )

    async def _nightly_sweep(self, now: datetime) -> None:
        cleared = await self._clear_manual_states()
        self._counters.reset()
        self._event_bus.post(EVENT_SYNC_REQUIRED, reason="nightly_sweep")
        self._schedule_nightly_sweep()
        self._beat("nightly_sweep")
        self._record_event("nightly_sweep", cleared=len(cleared))
        self._notify_entities()
        self._emit_calculation_event("nightly_sweep", zones=[])

    async def _handle_manual_detected(self, zone: str, duration_s: int) -> None:
        self._beat("manual_detected")
        self._counters.increment("manual_detects")
        current_mode = self._mode_manager.mode
        pending_switch = False
        if current_mode != "adaptive" and self._previous_mode is None:
            self._previous_mode = current_mode
            pending_switch = True
            _LOGGER.info(
                "Manual adjustment detected in %s mode. Switching to ADAPTIVE until manual timer expires.",
                current_mode,
            )
        elif current_mode == "adaptive" and self._previous_mode is not None:
            _LOGGER.info(
                "Manual adjustment detected while operating under temporary %s override.",
                self._previous_mode,
            )
        self._zone_manager.set_manual(zone, True, duration_s)
        self._timer_manager.start(zone, duration_s)
        zone_conf = self._zone_manager.get_zone(zone)
        await self._executors.set_manual_control(zone_conf.al_switch, True)
        if pending_switch:
            await self.select_mode("adaptive")
        self._record_event(
            "manual_detected",
            zone=zone,
            duration_s=duration_s,
            switched_to_adaptive=pending_switch,
        )
        self._notify_entities()
        self._emit_calculation_event(
            "manual_detected", zones=[zone], details={"duration_s": duration_s}
        )
        self._persist_runtime_state()

    async def _handle_manual_released(
        self,
        zone: str,
        source: str | None = None,
        previous_lights: List[str] | None = None,
    ) -> None:
        self._beat("manual_released")
        try:
            zone_conf = self._zone_manager.get_zone(zone)
        except KeyError:
            return
        timer_remaining = self._timer_manager.remaining(zone)
        manual_active = self._zone_manager.manual_active(zone)
        if manual_active:
            self._zone_manager.set_manual(zone, False)
        if timer_remaining > 0:
            self._timer_manager.cancel(zone)
        if manual_active:
            await self._executors.set_manual_control(zone_conf.al_switch, False)
        await self._restore_previous_mode_if_idle()
        self._event_bus.post(EVENT_SYNC_REQUIRED, reason="manual_release", zone=zone)
        self._record_event(
            "manual_released",
            zone=zone,
            source=source,
            previous_lights=previous_lights,
        )
        self._notify_entities()
        self._emit_calculation_event("manual_release", zones=[zone])
        self._persist_runtime_state()

    async def _handle_timer_expired(self, zone: str) -> None:
        self._beat("timer_expired")
        zone_conf = self._zone_manager.get_zone(zone)
        self._zone_manager.set_manual(zone, False)
        await self._executors.set_manual_control(zone_conf.al_switch, False)
        await self._restore_previous_mode_if_idle()
        self._event_bus.post(EVENT_SYNC_REQUIRED, reason="timer", zone=zone)
        self._record_event("timer_expired", zone=zone)
        self._notify_entities()
        self._emit_calculation_event("timer_expired", zones=[zone])
        self._persist_runtime_state()

    async def _handle_sync_required(self, reason: str, zone: str | None = None) -> None:
        self._beat("sync_required")
        result = await self.force_sync(zone)
        self._record_event(
            "sync_required",
            reason=reason,
            zone=zone,
            status=result.get("status"),
        )

    def _handle_mode_changed(self, mode: str) -> None:
        self._beat("mode_changed")
        self._health_monitor.set_mode(mode)
        self._last_mode_change = dt_util.utcnow()
        self._record_event("mode_changed", mode=mode)
        self._notify_entities()
        self._emit_calculation_event("mode", zones=[])

    def _handle_scene_changed(self, scene: str) -> None:
        self._beat("scene_changed")
        self._health_monitor.set_scene(scene)
        self._last_scene_change = dt_util.utcnow()
        self._record_event("scene_changed", scene=scene)
        self._notify_entities()
        self._emit_calculation_event("scene", zones=[])

    def _handle_reset_requested(self, scope: str, zone: str | None = None) -> None:
        self._beat("reset_requested")
        if scope == "watchdog":
            self._counters.increment("watchdog_resets")
        self._event_bus.post(EVENT_SYNC_REQUIRED, reason="reset", zone=zone)
        self._record_event("reset_requested", scope=scope, zone=zone)
        self._emit_calculation_event("reset_requested", zones=[zone] if zone else [])

    async def _handle_environmental_changed(self, boost_active: bool, **payload: Any) -> None:
        mode = self._mode_manager.mode
        sunset_boost = int(payload.get("sunset_boost_pct", 0) or 0)
        if mode != "adaptive":
            if boost_active:
                _LOGGER.info(
                    "Environmental boost skipped in %s mode. Switch to ADAPTIVE mode to enable automatic boosts.",
                    mode,
                )
            self._timer_manager.set_environment(False)
            if self._sunset_boost_pct or self._sunset_active:
                self._sunset_boost_pct = 0
                self._sunset_active = False
                await self._update_zone_boundaries()
            self._environmental_state.update(
                active=False,
                lux=payload.get("lux"),
                cloud_coverage=payload.get("cloud_coverage"),
                elevation=payload.get("elevation"),
                boost_pct=0,
                sunset_boost_pct=sunset_boost,
                multiplier=1.0,
            )
            self._beat("environmental")
            self._record_event(
                "environmental_skipped",
                mode=mode,
                boost_active=boost_active,
                sunset_boost_pct=sunset_boost,
            )
            self._recalculate_adjustments()
            self._notify_entities()
            self._emit_calculation_event(
                "environmental",
                zones=[],
                details={"skipped": True, "mode": mode},
            )
            return
        multiplier = payload.get("multiplier")
        self._timer_manager.set_environment(boost_active, multiplier=multiplier)
        if boost_active:
            for zone_conf in self._zone_manager.zones():
                if not zone_conf.environmental_boost_enabled:
                    _LOGGER.info(
                        "Environmental boost active but disabled for zone %s. Skipping timer multiplier.",
                        zone_conf.zone_id,
                    )
        sunset_boost = max(0, sunset_boost)
        sunset_changed = False
        if sunset_boost != self._sunset_boost_pct or (sunset_boost > 0) != self._sunset_active:
            self._sunset_boost_pct = sunset_boost
            self._sunset_active = sunset_boost > 0
            sunset_changed = True
        if sunset_changed:
            await self._update_zone_boundaries()
        boost_value = self._environmental_state.get("boost_pct", 0)
        if boost_active and "boost_pct" in payload:
            try:
                boost_value = int(payload.get("boost_pct") or 0)
            except (TypeError, ValueError):  # pragma: no cover - defensive
                boost_value = boost_value
        if not boost_active:
            boost_value = 0
        self._environmental_state.update(
            active=boost_active,
            lux=payload.get("lux"),
            cloud_coverage=payload.get("cloud_coverage"),
            elevation=payload.get("elevation"),
            boost_pct=boost_value,
            sunset_boost_pct=self._sunset_boost_pct,
            multiplier=multiplier if multiplier is not None else (
                self._environmental_state.get("multiplier", 1.0)
                if boost_active
                else 1.0
            ),
        )
        if not boost_active:
            self._environmental_state["multiplier"] = 1.0
        self._beat("environmental")
        self._record_event(
            "environmental_changed",
            boost_active=boost_active,
            multiplier=payload.get("multiplier"),
            sunset_boost_pct=self._sunset_boost_pct,
        )
        self._recalculate_adjustments()
        self._notify_entities()
        self._emit_calculation_event("environmental", zones=[])
        self._persist_runtime_state()

    async def _handle_button_event(
        self, device: str, button: str | None = None, action: str | None = None
    ) -> None:
        if device != "zen32":
            return
        self._beat("button")
        button_raw = button or ""
        action_raw = action or ""
        button_code = "".join(ch for ch in button_raw if ch.isdigit())
        if not button_code and button_raw:
            button_code = button_raw.strip()
        button_code = button_code or "unknown"
        action_norm = action_raw.strip().lower()
        is_hold = any(token in action_norm for token in ("hold", "held", "long"))
        is_single = False
        if not is_hold:
            if any(token in action_norm for token in ("single", "press", "short")):
                is_single = True
            elif action_norm in {"keypressed", "keyreleased", "released"}:
                is_single = True
            elif action_norm.isdigit():
                is_single = action_norm in {"0", "1"}
            elif not action_norm:
                is_single = True
        if action_norm.isdigit() and action_norm == "2":
            is_hold = True

        if button_code == "001" and is_single:
            if self._mode_manager.mode != "adaptive":
                _LOGGER.info(
                    "Zen32 scene cycle ignored in %s mode.", self._mode_manager.mode
                )
                self._record_event(
                    "zen32_scene_blocked",
                    button=button_code,
                    action=action_raw,
                    mode=self._mode_manager.mode,
                )
                return
            await self._scene_manager.cycle()
            self._record_event(
                "zen32_scene_cycle", button=button_code, action=action_raw
            )
            return

        if button_code == "002":
            if is_hold:
                await self.adjust(step_color_temp=-self._adjust_color_temp_step)
                self._record_event(
                    "zen32_adjust_warmer",
                    button=button_code,
                    action=action_raw,
                    step=-self._adjust_color_temp_step,
                )
            elif is_single:
                await self.adjust(step_brightness_pct=self._adjust_brightness_step)
                self._record_event(
                    "zen32_adjust_brighter",
                    button=button_code,
                    action=action_raw,
                    step=self._adjust_brightness_step,
                )
            return

        if button_code == "004":
            if is_hold:
                await self.adjust(step_color_temp=self._adjust_color_temp_step)
                self._record_event(
                    "zen32_adjust_cooler",
                    button=button_code,
                    action=action_raw,
                    step=self._adjust_color_temp_step,
                )
            elif is_single:
                await self.adjust(step_brightness_pct=-self._adjust_brightness_step)
                self._record_event(
                    "zen32_adjust_dimmer",
                    button=button_code,
                    action=action_raw,
                    step=-self._adjust_brightness_step,
                )
            return

        if button_code == "003":
            await self.select_mode("adaptive")
            scene_result = await self.select_scene("default")
            self._record_event(
                "zen32_reset",
                button=button_code,
                action=action_raw,
                cleared=scene_result.get("cleared", 0),
            )
            return

        if button_code == "005" and is_single:
            await self._toggle_all_lights()
            self._record_event(
                "zen32_toggle_all", button=button_code, action=action_raw
            )
            return

        _LOGGER.debug(
            "Unhandled Zen32 input button=%s action=%s", button_code, action_raw
        )

    async def force_sync(self, zone: str | None = None) -> Dict[str, Any]:
        self._beat("force_sync")
        if self._global_pause:
            self._record_event("sync_skipped_paused", zone=zone)
            return {"status": "error", "error_code": "PAUSED"}
        zones = (
            [self._zone_manager.get_zone(zone)]
            if zone
            else self._zone_manager.enabled_zones()
        )
        results = []
        rate_limited = False
        updated_zone_ids: List[str] = []
        for zone_conf in zones:
            if self._zone_manager.manual_active(zone_conf.zone_id):
                continue
            payload = {
                "transition": SYNC_TRANSITION_SEC,
                "lights": zone_conf.lights,
                "force": self._options.get(CONF_FORCE_APPLY, DEFAULT_FORCE_APPLY),
            }
            result = await self._executors.apply(zone_conf.al_switch, payload)
            if result.get("error_code") == "RATE_LIMITED":
                rate_limited = True
                self._counters.increment("rate_limited")
            self._metrics.record_sync(result.get("duration_ms", 0), failed=result.get("status") != "ok")
            self._zone_manager.update_sync_result(
                zone_conf.zone_id,
                result.get("duration_ms", 0),
                result.get("error_code"),
            )
            results.append(result)
            updated_zone_ids.append(zone_conf.zone_id)
        self._rate_limit_reached = rate_limited
        self._health_monitor.set_rate_load(self._rate_limiter.load)
        self._counters.increment("sync_requests")
        self._notify_entities()
        self._emit_calculation_event(
            "force_sync",
            zones=updated_zone_ids,
            details={"rate_limited": rate_limited, "requested_zone": zone},
        )
        return {"status": "ok", "results": results}

    async def reset_zone(self, zone: str) -> Dict[str, Any]:
        zone_conf = self._zone_manager.get_zone(zone)
        self._zone_manager.set_manual(zone, False)
        await self._executors.set_manual_control(zone_conf.al_switch, False)
        await self.force_sync(zone)
        self._persist_runtime_state()
        return {"status": "ok"}

    async def enable_zone(self, zone: str) -> Dict[str, Any]:
        self._zone_manager.set_enabled(zone, True)
        await self.force_sync(zone)
        return {"status": "ok"}

    async def disable_zone(self, zone: str) -> Dict[str, Any]:
        self._zone_manager.set_enabled(zone, False)
        return {"status": "ok"}

    async def set_zone_boost(
        self,
        zone: str,
        environmental: bool | None = None,
        sunset: bool | None = None,
    ) -> Dict[str, Any]:
        changes: Dict[str, Any] = {}
        if environmental is not None:
            if self._zone_manager.set_environmental_boost_enabled(zone, bool(environmental)):
                changes["environmental_boost_enabled"] = bool(environmental)
        if sunset is not None:
            if self._zone_manager.set_sunset_boost_enabled(zone, bool(sunset)):
                changes["sunset_boost_enabled"] = bool(sunset)
        if not changes:
            return {"status": "ok", "updated": False}
        overrides = dict(self._options.get(CONF_PER_ZONE_OVERRIDES, {}))
        zone_override = dict(overrides.get(zone, {}))
        zone_override.update(changes)
        overrides[zone] = zone_override
        self._options[CONF_PER_ZONE_OVERRIDES] = overrides
        self._hass.config_entries.async_update_entry(
            self._entry, options=dict(self._options)
        )
        if not self._zone_manager.manual_active(zone):
            await self.force_sync(zone)
        self._record_event("zone_boost_updated", zone=zone, changes=changes)
        self._notify_entities()
        self._emit_calculation_event(
            "zone_boost", zones=[zone], details={"changes": changes}
        )
        self._persist_runtime_state()
        return {"status": "ok", "updated": True, "changes": changes}

    async def skip_next_alarm(self, skip: bool = True) -> Dict[str, Any]:
        self._beat("sonos_skip")
        if not self._sonos:
            return {"status": "error", "error_code": "SONOS_DISABLED"}
        desired = bool(skip)
        before = self.sonos_skip_next()
        self._sonos.set_skip_next(desired)
        if before == desired:
            self._record_event("sonos_skip_noop", skip=desired)
        return {"status": "ok", "skip_next": desired}

    async def select_mode(self, mode: str) -> Dict[str, Any]:
        canonical = self._resolve_mode(mode)
        validate_mode(canonical)
        if canonical != "adaptive":
            self._previous_mode = None
        self._mode_manager.select(canonical)
        await self.force_sync()
        return {"status": "ok", "mode": canonical}

    async def select_scene(self, scene: str) -> Dict[str, Any]:
        validate_scene(scene)
        if self._mode_manager.mode != "adaptive":
            _LOGGER.warning(
                "Cannot apply scene %s while in %s mode. Scenes require ADAPTIVE mode.",
                scene,
                self._mode_manager.mode,
            )
            return {"status": "error", "error_code": "MODE_BLOCKED"}
        cleared = 0
        if scene == "default":
            cleared_zones = await self._clear_manual_states()
            cleared = len(cleared_zones)
        await self._scene_manager.select(scene)
        if scene == "default":
            await self.force_sync()
        return {"status": "ok", "cleared": cleared}

    async def adjust(
        self,
        step_brightness_pct: int | None = None,
        step_color_temp: int | None = None,
    ) -> Dict[str, Any]:
        if step_brightness_pct is None and step_color_temp is None:
            return {"status": "error", "error_code": "NO_ADJUSTMENT"}

        if step_brightness_pct is not None:
            if step_brightness_pct > 0:
                self._record_manual_action("brighter")
            elif step_brightness_pct < 0:
                self._record_manual_action("dimmer")
        if step_color_temp is not None:
            if step_color_temp < 0:
                self._record_manual_action("warmer")
            elif step_color_temp > 0:
                self._record_manual_action("cooler")

        zones = self._zone_manager.enabled_zones()
        applied = False
        results: List[Dict[str, Any]] = []
        adjusted_zones: List[str] = []
        force_flag = bool(self._options.get(CONF_FORCE_APPLY, DEFAULT_FORCE_APPLY))
        rate_limited = False

        for zone_conf in zones:
            if self._zone_manager.manual_active(zone_conf.zone_id):
                continue

            payload: Dict[str, Any] = {
                "transition": SYNC_TRANSITION_SEC,
                "lights": zone_conf.lights,
                "force": force_flag,
                "turn_on_lights": True,
                "context": {
                    "source": "alp_adjust",
                    "zone": zone_conf.zone_id,
                },
            }
            brightness_target: int | None = None
            color_target: int | None = None

            if step_brightness_pct is not None:
                current = self._current_brightness_pct(zone_conf)
                brightness_target = self._clamp(current + step_brightness_pct, 1, 100)
                payload["brightness_pct"] = brightness_target
                payload["adapt_brightness"] = False
                payload["context"]["brightness_step_pct"] = step_brightness_pct
                payload["context"]["brightness_target_pct"] = brightness_target

            if step_color_temp is not None:
                current_kelvin = self._current_color_temp_kelvin(zone_conf)
                color_target = self._clamp(current_kelvin + step_color_temp, 1800, 6500)
                payload["color_temp_kelvin"] = color_target
                payload["adapt_color_temp"] = False
                payload["context"]["color_temp_step"] = step_color_temp
                payload["context"]["color_temp_target_kelvin"] = color_target

            if brightness_target is None:
                payload.setdefault("adapt_brightness", True)
            if color_target is None:
                payload.setdefault("adapt_color_temp", True)

            if brightness_target is None and color_target is None:
                continue

            applied = True
            adjusted_zones.append(zone_conf.zone_id)
            duration = self._timer_manager.compute_duration_seconds(zone_conf.zone_id)
            self._event_bus.post(
                EVENT_MANUAL_DETECTED,
                zone=zone_conf.zone_id,
                duration_s=duration,
            )
            result = await self._executors.apply(zone_conf.al_switch, payload)
            if result.get("error_code") == "RATE_LIMITED":
                rate_limited = True
                self._counters.increment("rate_limited")
            self._metrics.record_sync(
                result.get("duration_ms", 0), failed=result.get("status") != "ok"
            )
            self._zone_manager.update_sync_result(
                zone_conf.zone_id,
                result.get("duration_ms", 0),
                result.get("error_code"),
            )
            results.append(result)

        if not applied:
            return {"status": "error", "error_code": "NO_TARGET_ZONE"}

        self._rate_limit_reached = rate_limited
        self._health_monitor.set_rate_load(self._rate_limiter.load)
        self._counters.increment("sync_requests")
        self._record_event(
            "adjust",
            zones=adjusted_zones,
            step_brightness=step_brightness_pct,
            step_color_temp=step_color_temp,
        )
        self._update_manual_totals(
            brightness_delta=step_brightness_pct or 0,
            warmth_delta=step_color_temp or 0,
        )
        self._notify_entities()
        self._emit_calculation_event(
            "manual_adjust",
            zones=adjusted_zones,
            details={"rate_limited": rate_limited},
        )
        return {"status": "ok", "results": results}

    async def backup_prefs(self) -> Dict[str, Any]:
        self._backup_prefs = {
            "options": dict(self._options),
            "data": dict(self._data),
        }
        return {"status": "ok"}

    async def restore_prefs(self) -> Dict[str, Any]:
        if not self._backup_prefs:
            return {"status": "error", "error_code": "NO_BACKUP"}
        self._options = dict(self._backup_prefs["options"])
        self._data = dict(self._backup_prefs["data"])
        self._apply_zone_configuration()
        self._apply_options()
        await self.force_sync()
        return {"status": "ok"}

    def health_score(self) -> int:
        return self._health_monitor.snapshot().score

    def analytics_summary(self) -> Dict[str, Any]:
        snapshot = self._health_monitor.snapshot()
        return snapshot.summary

    def rate_limit_reached(self) -> bool:
        return self._rate_limit_reached

    def zone_states(self) -> Dict[str, Dict[str, Any]]:
        return self._zone_manager.as_dict()

    def manual_action_flags(self) -> Dict[str, bool]:
        return dict(self._manual_action_flags)

    def available_modes(self) -> List[str]:
        """Expose available modes to Home Assistant platforms."""

        modes = self._mode_manager.available_modes()
        alias_options = [
            alias
            for alias in self._mode_aliases.keys()
            if alias not in modes
        ]
        return modes + alias_options

    def current_mode(self) -> str:
        """Return the active lighting mode."""

        return self._mode_manager.mode

    def available_scenes(self) -> List[str]:
        """Expose configured scenes in display order."""

        return self._scene_manager.available()

    def current_scene(self) -> str:
        """Return the currently selected scene."""

        return self._scene_manager.scene

    def scene_offsets(self) -> Dict[str, int]:
        return dict(self._scene_offsets)

    def scene_brightness_offset(self) -> int:
        return int(self._scene_offset_user["brightness"])

    def scene_warmth_offset(self) -> int:
        return int(self._scene_offset_user["warmth"])

    def set_scene_brightness_offset(self, value: float) -> None:
        brightness = int(value)
        if self._scene_offset_user["brightness"] == brightness:
            return
        self._scene_offset_user["brightness"] = brightness
        self._scene_manager.update_user_offsets(
            brightness, self._scene_offset_user["warmth"]
        )
        self._persist_scene_offsets()
        self._hass.async_create_task(self.select_scene(self._scene_manager.scene))

    def sonos_skip_next(self) -> bool:
        if not self._sonos:
            return False
        return self._sonos.skip_next

    def sonos_anchor_snapshot(self) -> Dict[str, Any]:
        """Return details about the upcoming sunrise anchor."""

        if not self._sonos:
            return {
                "state": "unavailable",
                "anchor": None,
                "anchor_source": "unavailable",
                "skip_next": False,
                "next_alarm_iso": None,
                "sunrise_iso": None,
                "seconds_until_anchor": None,
                "updated_iso": None,
            }
        snapshot: SonosAnchorSnapshot = self._sonos.anchor_snapshot()

        def _as_local(value: datetime | None) -> datetime | None:
            if value is None:
                return None
            return dt_util.as_local(value)

        anchor_local = _as_local(snapshot.anchor)
        anchor_utc = snapshot.anchor.astimezone(dt_util.UTC) if snapshot.anchor else None
        seconds_until: int | None = None
        if anchor_utc is not None:
            delta = anchor_utc - dt_util.utcnow()
            seconds_until = max(0, int(delta.total_seconds()))

        return {
            "state": "ready" if anchor_local else "idle",
            "anchor": anchor_local,
            "anchor_source": snapshot.anchor_source,
            "skip_next": snapshot.skip_next,
            "next_alarm_iso": _as_local(snapshot.next_alarm).isoformat()
            if snapshot.next_alarm
            else None,
            "sunrise_iso": _as_local(snapshot.sun_anchor).isoformat()
            if snapshot.sun_anchor
            else None,
            "seconds_until_anchor": seconds_until,
            "updated_iso": _as_local(snapshot.updated).isoformat()
            if snapshot.updated
            else None,
        }

    def set_scene_warmth_offset(self, value: float) -> None:
        warmth = int(value)
        if self._scene_offset_user["warmth"] == warmth:
            return
        self._scene_offset_user["warmth"] = warmth
        self._scene_manager.update_user_offsets(
            self._scene_offset_user["brightness"], warmth
        )
        self._persist_scene_offsets()
        self._hass.async_create_task(self.select_scene(self._scene_manager.scene))

    def _persist_scene_offsets(self) -> None:
        scenes_options = dict(self._options.get(CONF_SCENES, {}))
        offsets = dict(scenes_options.get("offsets", {}))
        offsets["brightness"] = int(self._scene_offset_user["brightness"])
        offsets["warmth"] = int(self._scene_offset_user["warmth"])
        scenes_options["offsets"] = offsets
        self._options[CONF_SCENES] = scenes_options
        self._hass.config_entries.async_update_entry(
            self._entry, options=dict(self._options)
        )

    async def set_global_pause(self, paused: bool) -> None:
        if self._global_pause == paused:
            return
        self._global_pause = paused
        self._record_event("global_pause", paused=paused)
        self._notify_entities()
        if not paused:
            await self.force_sync()

    def globally_paused(self) -> bool:
        return self._global_pause

    def adjust_brightness_step(self) -> int:
        return self._adjust_brightness_step

    def adjust_color_temp_step(self) -> int:
        return self._adjust_color_temp_step

    def set_adjust_brightness_step(self, value: float) -> None:
        self._adjust_brightness_step = int(value)
        self._record_event("adjust_step_updated", brightness_step=int(value))
        self._notify_entities()

    def set_adjust_color_temp_step(self, value: float) -> None:
        self._adjust_color_temp_step = int(value)
        self._record_event("adjust_step_updated", color_temp_step=int(value))
        self._notify_entities()

    def telemetry_snapshot(self) -> Dict[str, Any]:
        zone_data = self.zone_states()
        manual_zones = [zone for zone, data in zone_data.items() if data.get("manual_active")]
        enabled_zones = [zone for zone, data in zone_data.items() if data.get("enabled")]
        last_syncs = {zone: data.get("last_sync_ms") for zone, data in zone_data.items()}
        last_errors = {
            zone: data.get("last_error")
            for zone, data in zone_data.items()
            if data.get("last_error")
        }
        summary = self.analytics_summary()
        anchor_snapshot = self.sonos_anchor_snapshot().copy()
        anchor_dt = anchor_snapshot.pop("anchor", None)
        anchor_snapshot["anchor_iso"] = anchor_dt.isoformat() if anchor_dt else None
        telemetry = {
            "state": "paused" if self._global_pause else "active",
            "mode": self._mode_manager.mode,
            "scene": self._scene_manager.scene,
            "manual_zones": manual_zones,
            "enabled_zones": enabled_zones,
            "rate_limit": self._rate_limit_reached,
            "avg_sync_ms": summary.get("avg_sync_ms"),
            "last_syncs": last_syncs,
            "last_errors": last_errors,
            "rate_window_load": summary.get("rate_window_load"),
            "counters": self._counters.as_dict(),
            "last_event": self._last_event,
            "scene_offsets": dict(self._scene_offsets),
            "sunset_boost_pct": self._sunset_boost_pct,
            "manual_actions": dict(self._manual_action_flags),
            "sonos_anchor": anchor_snapshot,
        }
        return telemetry

    def manual_brightness_total(self) -> int:
        return int(self._manual_brightness_total)

    def manual_warmth_total(self) -> int:
        return int(self._manual_warmth_total)

    def environmental_summary(self) -> Dict[str, Any]:
        return dict(self._environmental_state)

    def sunset_active(self) -> bool:
        return self._sunset_active

    def manual_action_history(self) -> Dict[str, datetime | None]:
        return dict(self._manual_history)

    def last_mode_change(self) -> datetime | None:
        return self._last_mode_change

    def last_scene_change(self) -> datetime | None:
        return self._last_scene_change

    def zone_timer_snapshot(self) -> Dict[str, Dict[str, Any]]:
        return self._timer_manager.snapshot()

    def zone_boundaries(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        data: Dict[str, Dict[str, Dict[str, int]]] = {}
        for zone in self._zone_manager.zones():
            baseline = self._zone_baselines.get(zone.zone_id, {})
            current = self._current_zone_settings.get(zone.zone_id, baseline)
            data[zone.zone_id] = {
                "baseline": dict(baseline),
                "current": dict(current),
            }
        return data

    def adjustment_breakdown(self) -> Dict[str, int]:
        return dict(self._adjustment_components)

    def last_calculation_event(self) -> Dict[str, Any]:
        return dict(self._last_calculation_event)

    def zone_sunrise_offset(self, zone_id: str) -> int:
        """Return the configured sunrise offset for a zone."""

        return self._zone_manager.get_zone(zone_id).sunrise_offset_min

    def set_zone_sunrise_offset(self, zone_id: str, value: float) -> None:
        """Update a zone's sunrise offset and refresh dependent schedulers."""

        offset = int(value)
        self._zone_manager.update_zone(zone_id, sunrise_offset_min=offset)
        if self._sonos:
            self._sonos.refresh()
        self._record_event("zone_sunrise_offset_updated", zone=zone_id, offset=offset)
        self._notify_entities()

    def zone_multiplier(self, zone_id: str) -> float:
        """Return the current zone multiplier."""

        return self._zone_manager.get_zone(zone_id).zone_multiplier

    def set_zone_multiplier(self, zone_id: str, value: float) -> None:
        """Persist a new zone multiplier and update timers."""

        multiplier = float(value)
        self._zone_manager.update_zone(zone_id, zone_multiplier=multiplier)
        self._record_event("zone_multiplier_updated", zone=zone_id, multiplier=multiplier)
        self._notify_entities()

    @staticmethod
    def _clamp(value: int, lower: int, upper: int) -> int:
        return max(lower, min(upper, value))

    def _current_brightness_pct(self, zone_conf: ZoneConfig) -> int:
        for entity_id in zone_conf.lights:
            state = self._hass.states.get(entity_id)
            if state and "brightness" in state.attributes:
                brightness = int(state.attributes["brightness"])
                return self._clamp(round(brightness / 255 * 100), 1, 100)
        return 50

    def _current_color_temp_kelvin(self, zone_conf: ZoneConfig) -> int:
        for entity_id in zone_conf.lights:
            state = self._hass.states.get(entity_id)
            if not state:
                continue
            if "color_temp_kelvin" in state.attributes:
                return self._clamp(int(state.attributes["color_temp_kelvin"]), 1800, 6500)
            if "color_temp" in state.attributes and state.attributes["color_temp"]:
                try:
                    mired = float(state.attributes["color_temp"])
                    kelvin = int(round(1_000_000 / mired))
                    return self._clamp(kelvin, 1800, 6500)
                except (ValueError, ZeroDivisionError, TypeError):
                    continue
        return 3000

    def _register_services(self) -> None:
        if self._services_registered:
            return

        async def _handle(call: ServiceCall, handler: Callable[..., Any]) -> None:
            result = await handler(**call.data)
            call.response = result

        self._hass.services.async_register(
            DOMAIN,
            SERVICE_FORCE_SYNC,
            lambda call: self._hass.async_create_task(
                _handle(call, self.force_sync)
            ),
            schema=None,
            supports_response=True,
        )
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_RESET_ZONE,
            lambda call: self._hass.async_create_task(
                _handle(call, self.reset_zone)
            ),
            supports_response=True,
        )
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_ENABLE_ZONE,
            lambda call: self._hass.async_create_task(
                _handle(call, self.enable_zone)
            ),
            supports_response=True,
        )
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_DISABLE_ZONE,
            lambda call: self._hass.async_create_task(
                _handle(call, self.disable_zone)
            ),
            supports_response=True,
        )
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_SELECT_MODE,
            lambda call: self._hass.async_create_task(
                _handle(call, self.select_mode)
            ),
            supports_response=True,
        )
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_SELECT_SCENE,
            lambda call: self._hass.async_create_task(
                _handle(call, self.select_scene)
            ),
            supports_response=True,
        )
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_ADJUST,
            lambda call: self._hass.async_create_task(
                _handle(call, self.adjust)
            ),
            supports_response=True,
        )
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_BACKUP_PREFS,
            lambda call: self._hass.async_create_task(
                _handle(call, self.backup_prefs)
            ),
            supports_response=True,
        )
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_RESTORE_PREFS,
            lambda call: self._hass.async_create_task(
                _handle(call, self.restore_prefs)
            ),
            supports_response=True,
        )
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_SKIP_NEXT_ALARM,
            lambda call: self._hass.async_create_task(
                _handle(call, self.skip_next_alarm)
            ),
            supports_response=True,
        )
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ZONE_BOOST,
            lambda call: self._hass.async_create_task(
                _handle(call, self.set_zone_boost)
            ),
            supports_response=True,
        )
        self._services_registered = True

    def get_health_entity_state(self) -> tuple[int, Dict[str, Any]]:
        snapshot = self._health_monitor.snapshot()
        return snapshot.score, snapshot.summary

    def get_rate_limit_state(self) -> bool:
        return self._rate_limit_reached
