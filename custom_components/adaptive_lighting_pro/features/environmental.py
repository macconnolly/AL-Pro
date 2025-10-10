"""Environmental adaptation observers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Tuple

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from ..const import EVENT_ENVIRONMENTAL_CHANGED, EVENT_SYNC_REQUIRED, SUNSET_ELEVATION_DEG
from ..utils.logger import log_debug


@dataclass
class EnvironmentalConfig:
    lux_entity: str | None
    weather_entity: str | None
    debug: bool


class EnvironmentalObserver:
    """Monitors sensors to decide when to boost lighting."""

    def __init__(self, hass: HomeAssistant, event_bus, timer_manager, config: EnvironmentalConfig) -> None:
        self._hass = hass
        self._event_bus = event_bus
        self._timer_manager = timer_manager
        self._config = config
        self._boost_active = False
        self._lux_value: float | None = None
        self._cloud_coverage: float | None = None
        self._weather_state: str | None = None
        self._boost_pct: int = 0
        self._sunset_boost_pct: int = 0
        self._sun_listener = async_track_time_interval(
            hass, self._sunset_check, timedelta(minutes=5)
        )
        self._listeners: list = []

    def start(self) -> None:
        if self._config.lux_entity:
            self._listeners.append(
                async_track_state_change_event(
                    self._hass, [self._config.lux_entity], self._handle_lux
                )
            )
        if self._config.weather_entity:
            self._listeners.append(
                async_track_state_change_event(
                    self._hass, [self._config.weather_entity], self._handle_weather
                )
            )
        self.evaluate()

    def stop(self) -> None:
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()
        if self._sun_listener:
            self._sun_listener()
            self._sun_listener = None

    @property
    def boost_active(self) -> bool:
        return self._boost_active

    async def _handle_lux(self, event: Event) -> None:
        try:
            self._lux_value = float(event.data.get("new_state").state)
        except (TypeError, ValueError, AttributeError):  # pragma: no cover - defensive
            self._lux_value = None
        self.evaluate()

    async def _handle_weather(self, event: Event) -> None:
        attrs = getattr(event.data.get("new_state"), "attributes", {})
        cloud = attrs.get("cloud_coverage")
        try:
            self._cloud_coverage = float(cloud)
        except (TypeError, ValueError):
            self._cloud_coverage = None
        state = getattr(event.data.get("new_state"), "state", None)
        self._weather_state = self._normalize_weather_state(state)
        self.evaluate()

    def evaluate(self) -> None:
        sun_state = self._hass.states.get("sun.sun")
        elevation = float(sun_state.attributes.get("elevation", 0)) if sun_state else 0
        boost_pct, components = self._calculate_environmental_boost()
        multiplier = self._calculate_timer_multiplier(boost_pct)
        boost_active = boost_pct > 0
        state_changed = boost_active != self._boost_active or boost_pct != self._boost_pct
        self._boost_active = boost_active
        self._boost_pct = boost_pct
        if state_changed or components.get("weather_state") != self._weather_state:
            log_debug(
                self._config.debug,
                "Environmental boost updated active=%s pct=%s components=%s",
                boost_active,
                boost_pct,
                components,
            )
            self._timer_manager.set_environment(boost_active, multiplier=multiplier)
            payload = {
                "boost_active": boost_active,
                "boost_pct": boost_pct,
                "multiplier": multiplier,
                "elevation": elevation,
                "lux": self._lux_value,
                "cloud_coverage": self._cloud_coverage,
                **components,
            }
            self._event_bus.post(EVENT_ENVIRONMENTAL_CHANGED, **payload)

    async def _sunset_check(self, now: datetime) -> None:
        sun_state = self._hass.states.get("sun.sun")
        if not sun_state:
            return
        elevation = float(sun_state.attributes.get("elevation", 0))
        offset = self._calculate_sunset_boost(elevation)
        if offset != self._sunset_boost_pct:
            self._sunset_boost_pct = offset
            log_debug(
                self._config.debug,
                "Sunset boost updated to %s%% (elevation=%s, lux=%s, cloud=%s)",
                offset,
                elevation,
                self._lux_value,
                self._cloud_coverage,
            )
            self._event_bus.post(
                EVENT_ENVIRONMENTAL_CHANGED,
                boost_active=self._boost_active,
                sunset_boost_pct=offset,
                elevation=elevation,
                lux=self._lux_value,
                cloud_coverage=self._cloud_coverage,
            )
        if elevation < SUNSET_ELEVATION_DEG and offset:
            self._event_bus.post(EVENT_SYNC_REQUIRED, reason="sunset_boost")

    def _calculate_sunset_boost(self, elevation: float) -> int:
        if elevation > SUNSET_ELEVATION_DEG or elevation < -6:
            return 0
        lux = self._lux_value if self._lux_value is not None else 1000
        if lux > 400:
            return 0
        if self._boost_pct >= 22 and lux >= 50:
            return 0
        progress = (SUNSET_ELEVATION_DEG - elevation) / (SUNSET_ELEVATION_DEG + 6)
        progress = max(0.0, min(1.0, progress))
        gloom_factor = 1.0
        if self._cloud_coverage is not None:
            gloom_factor += max(0.0, min(1.0, self._cloud_coverage / 100)) * 0.6
        lux_bonus = 0.0
        if lux < 10:
            lux_bonus = 8.0
        elif lux < 25:
            lux_bonus = 6.0
        elif lux < 50:
            lux_bonus = 4.0
        elif lux < 100:
            lux_bonus = 2.0
        env_shortfall = max(0.0, 18.0 - float(self._boost_pct))
        base = (env_shortfall * 0.6 * progress) + lux_bonus
        if self._cloud_coverage is not None and self._cloud_coverage >= 70 and lux <= 150:
            base += 2.0
        boost = max(0.0, min(18.0, base * gloom_factor))
        return int(round(boost))

    def _calculate_environmental_boost(self) -> Tuple[int, Dict[str, object]]:
        lux_boost = self._calculate_lux_boost(self._lux_value)
        weather_boost = self._calculate_weather_boost(self._weather_state)
        season_adjust = self._seasonal_adjustment()
        base = lux_boost + weather_boost + season_adjust
        scaled, time_window = self._apply_time_of_day_scaling(base)
        boost_pct = int(round(max(0.0, min(25.0, scaled))))
        components: Dict[str, object] = {
            "lux_boost": lux_boost,
            "weather_boost": weather_boost,
            "seasonal_adjust": season_adjust,
            "time_window": time_window,
            "weather_state": self._weather_state,
        }
        return boost_pct, components

    def _calculate_lux_boost(self, lux: float | None) -> int:
        if lux is None:
            return 0
        if lux < 10:
            return 15
        if lux < 25:
            return 10
        if lux < 50:
            return 7
        if lux < 100:
            return 5
        if lux < 200:
            return 3
        if lux < 400:
            return 1
        return 0

    def _calculate_weather_boost(self, weather: str | None) -> int:
        if not weather:
            return 0
        weather_map = {
            "fog": 20,
            "mist": 18,
            "haze": 18,
            "smoke": 18,
            "pouring": 18,
            "hail": 18,
            "hailstorm": 18,
            "snowy": 15,
            "snow": 15,
            "snowshowers": 15,
            "flurries": 15,
            "snowyrainy": 15,
            "sleet": 15,
            "freezingrain": 15,
            "ice": 15,
            "blizzard": 15,
            "rainy": 12,
            "rain": 12,
            "drizzle": 12,
            "sprinkles": 12,
            "rainshower": 12,
            "rainshowers": 12,
            "lightningrainy": 12,
            "lightningrain": 12,
            "thunderstorm": 12,
            "thunderstorms": 12,
            "storm": 12,
            "lightning": 8,
            "cloudy": 10,
            "overcast": 10,
            "mostlycloudy": 10,
            "mostlycloudyday": 10,
            "mostlycloudynight": 10,
            "scatteredclouds": 10,
            "brokenclouds": 10,
            "partlycloudy": 5,
            "partlysunny": 5,
            "mostlysunny": 4,
            "fair": 4,
            "windy": 2,
            "wind": 2,
            "windyvariant": 2,
            "breezy": 2,
            "gusty": 2,
            "sunny": 0,
            "clearsky": 0,
            "clearnight": 0,
            "clear": 0,
            "exceptional": 15,
            "extreme": 15,
            "tornado": 15,
            "hurricane": 15,
        }
        alias_map = {
            "lightningstorm": "lightningrainy",
            "tstorm": "lightningrainy",
            "tstorms": "lightningrainy",
            "stormy": "lightningrainy",
            "heavyrain": "pouring",
            "pouringrain": "pouring",
            "heavysnow": "snowy",
            "sleetstorm": "snowyrainy",
            "mixedrainandsnow": "snowyrainy",
            "mixedrainandsleet": "snowyrainy",
            "mixedsnowandsleet": "snowyrainy",
            "mostlyclear": "partlycloudy",
            "mostlycloud": "mostlycloudy",
            "partlycloud": "partlycloudy",
            "daypartlysunny": "partlysunny",
            "nightpartlycloudy": "partlycloudy",
        }
        for alias, canonical in alias_map.items():
            if alias in weather_map:
                continue
            if canonical in weather_map:
                weather_map[alias] = weather_map[canonical]
        return weather_map.get(weather, 0)

    def _seasonal_adjustment(self) -> int:
        now = dt_util.now()
        if now.month in (12, 1, 2):
            return 8
        if now.month in (6, 7, 8):
            return -3
        return 0

    def _apply_time_of_day_scaling(self, base: float) -> Tuple[float, str]:
        now = dt_util.now()
        hour = now.hour
        if hour >= 22 or hour <= 6:
            return 0.0, "night"
        if 6 < hour <= 8 or 18 <= hour < 22:
            return base * 0.7, "shoulder"
        return base, "day"

    def _calculate_timer_multiplier(self, boost_pct: int) -> float:
        if boost_pct >= 22:
            return 0.75
        if boost_pct >= 18:
            return 0.78
        if boost_pct >= 14:
            return 0.82
        if boost_pct >= 10:
            return 0.86
        if boost_pct >= 5:
            return 0.9
        if boost_pct > 0:
            return 0.95
        return 1.0

    @staticmethod
    def _normalize_weather_state(state: str | None) -> str | None:
        if not state:
            return None
        normalized = state.lower().replace("_", "").replace("-", "").replace(" ", "")
        return normalized or None
