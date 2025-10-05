"""Environmental adaptation observers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

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
        self.evaluate()

    def evaluate(self) -> None:
        sun_state = self._hass.states.get("sun.sun")
        elevation = float(sun_state.attributes.get("elevation", 0)) if sun_state else 0
        boost = False
        if self._lux_value is not None and self._lux_value < 30:
            boost = True
        if self._cloud_coverage is not None and self._cloud_coverage >= 70:
            boost = True
        if elevation < 0:
            boost = True
        if boost != self._boost_active:
            self._boost_active = boost
            log_debug(self._config.debug, "Environmental boost=%s", boost)
            self._timer_manager.set_environment(boost)
            self._event_bus.post(
                EVENT_ENVIRONMENTAL_CHANGED,
                boost_active=boost,
                elevation=elevation,
                lux=self._lux_value,
                cloud_coverage=self._cloud_coverage,
            )

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
        if elevation > SUNSET_ELEVATION_DEG or elevation < -4:
            return 0
        if elevation > 4:
            base = max(0.0, (SUNSET_ELEVATION_DEG - elevation) / (SUNSET_ELEVATION_DEG - 4))
            base_boost = base * 10
        else:
            base_boost = (4 - elevation) / 8 * 25
        base_boost = max(0.0, min(25.0, base_boost))
        if self._lux_value is not None:
            if self._lux_value >= 5000:
                return 0
            scale = max(0.0, min(1.0, (5000 - self._lux_value) / 5000))
            base_boost *= max(0.3, scale)
        if self._cloud_coverage is not None and self._cloud_coverage >= 70:
            base_boost = min(25.0, base_boost + 5.0)
        return int(round(base_boost))
