"""Manual control detection observers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, List

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from ..const import EVENT_MANUAL_DETECTED, MANUAL_DEBOUNCE_MS
from ..utils.logger import log_debug


@dataclass
class ManualControlConfig:
    debug: bool


class ManualControlObserver:
    """Detect manual changes to lights within a zone."""

    def __init__(
        self,
        hass: HomeAssistant,
        event_bus,
        timer_manager,
        zone_manager,
        config: ManualControlConfig,
    ) -> None:
        self._hass = hass
        self._event_bus = event_bus
        self._timer_manager = timer_manager
        self._zone_manager = zone_manager
        self._config = config
        self._listeners: List = []
        self._pending: Dict[str, asyncio.Task] = {}

    def start(self) -> None:
        for zone in self._zone_manager.zones():
            lights = zone.lights
            if not lights:
                continue

            async def _handle(event: Event, zone_id: str = zone.zone_id) -> None:
                await self._schedule(zone_id)

            listener = async_track_state_change_event(
                self._hass, lights, _handle
            )
            self._listeners.append(listener)

    def stop(self) -> None:
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()
        for task in self._pending.values():
            task.cancel()
        self._pending.clear()

    async def _schedule(self, zone_id: str) -> None:
        log_debug(self._config.debug, "Manual change detected for %s", zone_id)
        task = self._pending.get(zone_id)
        if task:
            task.cancel()

        async def _fire() -> None:
            await asyncio.sleep(MANUAL_DEBOUNCE_MS / 1000)
            duration = self._timer_manager.compute_duration_seconds(zone_id)
            self._event_bus.post(
                EVENT_MANUAL_DETECTED, zone=zone_id, duration_s=duration
            )

        self._pending[zone_id] = self._hass.async_create_task(_fire())
