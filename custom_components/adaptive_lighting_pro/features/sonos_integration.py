"""Sonos sunrise integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Iterable, List, Optional
from zoneinfo import ZoneInfo

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from ..const import EVENT_SYNC_REQUIRED, SONOS_SYNC_WINDOW
from ..utils.logger import log_debug


@dataclass
class SonosConfig:
    sensor: str | None
    skip_next_alarm: bool = False


def _parse_iso(value: str, tz: ZoneInfo) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def find_next_alarm(
    *,
    now: datetime,
    tz: ZoneInfo,
    state: str | None,
    attributes: dict | None,
) -> Optional[datetime]:
    """Find earliest Sonos alarm within 24h."""
    candidates: List[datetime] = []
    attrs = attributes or {}
    alarms = attrs.get("alarms")
    if isinstance(alarms, Iterable):
        for entry in alarms:
            if not isinstance(entry, dict):
                continue
            iso = entry.get("datetime") or entry.get("time")
            if not isinstance(iso, str):
                continue
            dt = _parse_iso(iso, tz)
            if dt is not None:
                candidates.append(dt)
    if not candidates and state:
        dt = _parse_iso(state, tz)
        if dt is not None:
            candidates.append(dt)
    horizon = now + timedelta(hours=24)
    valid = [dt for dt in candidates if now < dt <= horizon]
    if not valid:
        return None
    return min(valid)


class SonosSunriseCoordinator:
    """Coordinate Sonos alarm based sunrise sync."""

    def __init__(
        self,
        hass: HomeAssistant,
        event_bus,
        zone_manager,
        config: SonosConfig,
        debug: bool,
        on_skip_updated: Callable[[bool], None] | None = None,
    ) -> None:
        self._hass = hass
        self._event_bus = event_bus
        self._zone_manager = zone_manager
        self._config = config
        self._debug = debug
        self._anchor: Optional[datetime] = None
        self._skip_next = config.skip_next_alarm
        self._on_skip_updated = on_skip_updated
        self._sensor_listener = None
        self._timer = async_track_time_interval(
            hass, self._check_anchor, timedelta(minutes=1)
        )

    def start(self) -> None:
        self._evaluate()
        if not self._config.sensor:
            return
        self._sensor_listener = async_track_state_change_event(
            self._hass, [self._config.sensor], self._handle_sensor
        )
        self._evaluate()

    @property
    def skip_next(self) -> bool:
        return self._skip_next

    def set_skip_next(self, skip: bool) -> None:
        if self._skip_next == skip:
            return
        self._skip_next = skip
        self._config.skip_next_alarm = skip
        if self._on_skip_updated:
            self._on_skip_updated(skip)
        self._evaluate()

    def stop(self) -> None:
        if self._sensor_listener:
            self._sensor_listener()
            self._sensor_listener = None
        if self._timer:
            self._timer()
            self._timer = None

    def refresh(self) -> None:
        """Re-evaluate the active anchor after configuration changes."""

        self._evaluate()

    async def _handle_sensor(self, event: Event) -> None:
        self._evaluate()

    def _evaluate(self) -> None:
        tz = ZoneInfo(str(self._hass.config.time_zone))
        now = datetime.now(tz)
        anchor: Optional[datetime] = None
        if self._config.sensor and not self._skip_next:
            state = self._hass.states.get(self._config.sensor)
            if state:
                anchor = find_next_alarm(
                    now=now,
                    tz=tz,
                    state=state.state if state.state != "unknown" else None,
                    attributes=state.attributes,
                )
        sun_anchor = self._sun_anchor(now, tz)
        if self._skip_next and sun_anchor:
            anchor = sun_anchor
        if anchor is None:
            anchor = sun_anchor
        if anchor:
            log_debug(self._debug, "Sonos anchor updated %s", anchor)
        self._anchor = anchor

    def _sun_anchor(self, now: datetime, tz: ZoneInfo) -> Optional[datetime]:
        sun = self._hass.states.get("sun.sun")
        if not sun:
            return None
        next_rising = sun.attributes.get("next_rising")
        if not next_rising:
            return None
        parsed = _parse_iso(str(next_rising), tz)
        if parsed is None:
            return None
        if parsed <= now:
            parsed = parsed + timedelta(days=1)
        return parsed

    async def _check_anchor(self, now: datetime) -> None:
        tz = ZoneInfo(str(self._hass.config.time_zone))
        if not self._anchor:
            self._evaluate()
            if not self._anchor:
                return
        current = now.astimezone(tz)
        if abs((current - self._anchor).total_seconds()) <= SONOS_SYNC_WINDOW.total_seconds():
            self._event_bus.post(EVENT_SYNC_REQUIRED, reason="sonos_anchor")
            for zone in self._zone_manager.zones():
                offset = timedelta(minutes=zone.sunrise_offset_min)
                target = self._anchor + offset
                if abs((current - target).total_seconds()) <= SONOS_SYNC_WINDOW.total_seconds():
                    self._event_bus.post(
                        EVENT_SYNC_REQUIRED,
                        reason="sonos_zone_offset",
                        zone=zone.zone_id,
                    )
        if self._skip_next and current > self._anchor:
            self._skip_next = False
            self._config.skip_next_alarm = False
            if self._on_skip_updated:
                self._on_skip_updated(False)
            self._evaluate()
