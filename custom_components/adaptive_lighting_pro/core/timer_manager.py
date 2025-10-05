"""Timer manager for manual control handling."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Dict, Optional

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time

from ..const import (
    DEFAULT_BASE_DAY_MIN,
    DEFAULT_BASE_NIGHT_MIN,
    DEFAULT_ENV_MULTIPLIER_BOOST,
    DEFAULT_MODE_MULTIPLIERS,
    EVENT_TIMER_EXPIRED,
)
from ..utils.logger import log_debug


class TimerManager:
    """Compute manual durations and manage per-zone timers."""

    def __init__(self, hass: HomeAssistant, event_bus, *, debug: bool) -> None:
        self._hass = hass
        self._event_bus = event_bus
        self._debug = debug
        self._base_day_min = DEFAULT_BASE_DAY_MIN
        self._base_night_min = DEFAULT_BASE_NIGHT_MIN
        self._mode_multipliers = DEFAULT_MODE_MULTIPLIERS.copy()
        self._current_mode = "adaptive"
        self._env_multiplier = 1.0
        self._env_boost = DEFAULT_ENV_MULTIPLIER_BOOST
        self._env_boost_active = False
        self._zone_multipliers: Dict[str, float] = {}
        self._zone_env_enabled: Dict[str, bool] = {}
        self._expires: Dict[str, datetime] = {}
        self._unsubs: Dict[str, CALLBACK_TYPE] = {}

    def update_timeouts(self, *, day_min: int, night_min: int) -> None:
        self._base_day_min = day_min
        self._base_night_min = night_min

    def update_mode_multipliers(self, multipliers: Dict[str, float]) -> None:
        self._mode_multipliers.update(multipliers)

    def set_mode(self, mode: str) -> None:
        if mode in self._mode_multipliers:
            self._current_mode = mode

    def available_modes(self) -> list[str]:
        """Return the currently configured mode identifiers."""

        return list(self._mode_multipliers.keys())

    def set_environment(self, boost_active: bool, multiplier: Optional[float] = None) -> None:
        self._env_boost_active = boost_active
        self._env_multiplier = (
            multiplier
            if multiplier is not None
            else (self._env_boost if boost_active else 1.0)
        )

    def set_environment_boost_factor(self, factor: float) -> None:
        self._env_boost = factor
        if self._env_boost_active:
            self._env_multiplier = factor

    def configure_zone(self, zone_id: str, zone_multiplier: float, *, env_enabled: bool = True) -> None:
        self._zone_multipliers[zone_id] = zone_multiplier
        self._zone_env_enabled[zone_id] = env_enabled

    def remove_zone(self, zone_id: str) -> None:
        self.cancel(zone_id)
        self._zone_multipliers.pop(zone_id, None)
        self._zone_env_enabled.pop(zone_id, None)
        self._expires.pop(zone_id, None)

    def compute_duration_seconds(self, zone_id: str) -> int:
        base_min = self._base_day_min if self._is_daytime() else self._base_night_min
        mode_multiplier = self._mode_multipliers.get(self._current_mode, 1.0)
        zone_multiplier = self._zone_multipliers.get(zone_id, 1.0)
        env_allowed = self._zone_env_enabled.get(zone_id, True)
        env_multiplier = (
            self._env_multiplier
            if env_allowed and self._env_boost_active and self._current_mode == "adaptive"
            else 1.0
        )
        if self._env_boost_active and not env_allowed:
            log_debug(
                self._debug,
                "Environment boost suppressed for zone=%s", zone_id,
            )
        if self._env_boost_active and self._current_mode != "adaptive":
            log_debug(
                self._debug,
                "Environment boost suppressed by mode=%s", self._current_mode,
            )
        duration_min = base_min * mode_multiplier * env_multiplier * zone_multiplier
        duration_s = max(1, int(duration_min * 60))
        log_debug(
            self._debug,
            "Timer duration zone=%s base=%s mode=%s env=%s zone_mult=%s -> %s",
            zone_id,
            base_min,
            mode_multiplier,
            env_multiplier,
            zone_multiplier,
            duration_s,
        )
        return duration_s

    def start(self, zone_id: str, duration_s: int) -> None:
        self.cancel(zone_id)
        when = datetime.now(UTC) + timedelta(seconds=duration_s)
        self._expires[zone_id] = when

        @callback
        def _fire(now: datetime) -> None:
            log_debug(self._debug, "Timer expired zone=%s", zone_id)
            self._expires.pop(zone_id, None)
            self._unsubs.pop(zone_id, None)
            self._event_bus.post(EVENT_TIMER_EXPIRED, zone=zone_id)

        self._unsubs[zone_id] = async_track_point_in_time(self._hass, _fire, when)

    def cancel(self, zone_id: str) -> None:
        unsub = self._unsubs.pop(zone_id, None)
        if unsub:
            unsub()
        self._expires.pop(zone_id, None)

    def remaining(self, zone_id: str) -> int:
        expires = self._expires.get(zone_id)
        if not expires:
            return 0
        delta = expires - datetime.now(UTC)
        return max(0, int(delta.total_seconds()))

    def _is_daytime(self) -> bool:
        state = self._hass.states.get("sun.sun")
        if state is None:
            return True
        elevation = float(state.attributes.get("elevation", 0))
        return elevation >= 0
