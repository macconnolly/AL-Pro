"""Watchdog for monitoring stale observers."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Callable, Dict

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from ..const import WATCHDOG_EVENT
from ..utils.logger import log_debug


class Watchdog:
    """Schedule watchdog ticks and track heartbeats."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        interval: timedelta,
        on_reset: Callable[[str], None],
        debug: bool,
    ) -> None:
        self._hass = hass
        self._interval = interval
        self._on_reset = on_reset
        self._debug = debug
        self._unsub: CALLBACK_TYPE | None = None
        self._last_seen: Dict[str, datetime] = {}

    def start(self) -> None:
        """Begin watchdog timer."""
        if self._unsub is not None:
            return

        @callback
        def _tick(now: datetime) -> None:
            log_debug(self._debug, "Watchdog tick at %s", now)
            self._hass.bus.async_fire(WATCHDOG_EVENT, {})
            for name, seen in list(self._last_seen.items()):
                if now - seen > self._interval:
                    log_debug(self._debug, "Watchdog resetting %s", name)
                    self._on_reset(name)

        self._unsub = async_track_time_interval(
            self._hass, _tick, self._interval
        )

    def stop(self) -> None:
        """Stop watchdog."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    def beat(self, name: str) -> None:
        """Record heartbeat."""
        self._last_seen[name] = datetime.now(UTC)
