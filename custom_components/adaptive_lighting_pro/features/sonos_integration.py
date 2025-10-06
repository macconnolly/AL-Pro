"""Sonos sunrise integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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


@dataclass
class SonosAnchorSnapshot:
    """Stateful snapshot describing the current sunrise anchor."""

    anchor: Optional[datetime]
    anchor_source: str
    next_alarm: Optional[datetime]
    sun_anchor: Optional[datetime]
    skip_next: bool
    updated: datetime


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
        on_anchor_updated: Callable[[], None] | None = None,
    ) -> None:
        self._hass = hass
        self._event_bus = event_bus
        self._zone_manager = zone_manager
        self._config = config
        self._debug = debug
        self._anchor: Optional[datetime] = None
        self._skip_next = config.skip_next_alarm
        self._on_skip_updated = on_skip_updated
        self._on_anchor_updated = on_anchor_updated
        self._sensor_listener = None
        self._anchor_source: str = "unavailable"
        self._next_alarm: Optional[datetime] = None
        self._sun_anchor_cached: Optional[datetime] = None
        self._last_update: datetime = datetime.now(UTC)
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

    def anchor_snapshot(self) -> SonosAnchorSnapshot:
        """Return structured information about the current anchor state."""

        return SonosAnchorSnapshot(
            anchor=self._anchor,
            anchor_source=self._anchor_source,
            next_alarm=self._next_alarm,
            sun_anchor=self._sun_anchor_cached,
            skip_next=self._skip_next,
            updated=self._last_update,
        )

    async def _handle_sensor(self, event: Event) -> None:
        self._evaluate()

    def _evaluate(self) -> None:
        tz = ZoneInfo(str(self._hass.config.time_zone))
        now = datetime.now(tz)
        anchor: Optional[datetime] = None
        anchor_source = "unavailable"
        next_alarm: Optional[datetime] = None
        if self._config.sensor and not self._skip_next:
            state = self._hass.states.get(self._config.sensor)
            if state:
                next_alarm = find_next_alarm(
                    now=now,
                    tz=tz,
                    state=state.state if state.state != "unknown" else None,
                    attributes=state.attributes,
                )
                if next_alarm is not None:
                    anchor = next_alarm
                    anchor_source = "alarm"
        sun_anchor = self._sun_anchor(now, tz)
        if self._skip_next and sun_anchor:
            anchor = sun_anchor
            anchor_source = "sun_skip" if anchor_source != "alarm" else "alarm"
        if anchor is None:
            anchor = sun_anchor
            anchor_source = "sun" if sun_anchor else anchor_source
        previous_anchor = self._anchor
        previous_source = self._anchor_source
        previous_alarm = self._next_alarm
        previous_sun = self._sun_anchor_cached
        self._anchor = anchor
        self._anchor_source = anchor_source if anchor else "unavailable"
        self._next_alarm = next_alarm
        self._sun_anchor_cached = sun_anchor
        self._last_update = now.astimezone(UTC)
        if anchor:
            log_debug(self._debug, "Sonos anchor updated %s", anchor)
        if (
            previous_anchor != self._anchor
            or previous_source != self._anchor_source
            or previous_alarm != self._next_alarm
            or previous_sun != self._sun_anchor_cached
        ) and self._on_anchor_updated:
            self._on_anchor_updated()

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
            if self._on_anchor_updated:
                self._on_anchor_updated()
