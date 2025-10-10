"""Manual control detection observers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, Iterable, List, TYPE_CHECKING

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from ..const import (
    EVENT_MANUAL_DETECTED,
    EVENT_MANUAL_RELEASED,
    MANUAL_DEBOUNCE_MS,
)
from ..utils.logger import log_debug

if TYPE_CHECKING:
    from homeassistant.core import State


@dataclass
class ManualControlConfig:
    debug: bool


class ManualControlObserver:
    """Detect manual changes to lights and adaptive lighting switches."""

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
        self._zone_switch_map: Dict[str, str] = {}
        self._light_to_zone: Dict[str, str] = {}

    def start(self) -> None:
        self.stop()
        for zone in self._zone_manager.zones():
            self._zone_switch_map[zone.al_switch] = zone.zone_id
            self._register_switch_listener(zone.al_switch, zone.zone_id)
            if not zone.lights:
                continue
            self._register_light_listeners(zone.zone_id, zone.lights)

    def stop(self) -> None:
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()
        for task in self._pending.values():
            task.cancel()
        self._pending.clear()
        self._zone_switch_map.clear()
        self._light_to_zone.clear()

    def _register_light_listeners(self, zone_id: str, lights: Iterable[str]) -> None:
        tracked = list(lights)
        if not tracked:
            return
        for entity_id in tracked:
            self._light_to_zone[entity_id] = zone_id

        async def _handle(event: Event, zone: str = zone_id) -> None:
            if not self._should_consider_light(event):
                return
            await self._schedule(zone, source="light", lights=[event.data["entity_id"]])

        listener = async_track_state_change_event(self._hass, tracked, _handle)
        self._listeners.append(listener)

    def _register_switch_listener(self, switch: str, zone_id: str) -> None:
        async def _handle(event: Event, zone: str = zone_id) -> None:
            await self._process_switch_event(zone, event)

        listener = async_track_state_change_event(self._hass, [switch], _handle)
        self._listeners.append(listener)

    async def _process_switch_event(self, zone_id: str, event: Event) -> None:
        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")
        new_manual = self._extract_manual_list(new_state)
        old_manual = self._extract_manual_list(old_state)
        new_active = bool(new_manual)
        old_active = bool(old_manual)
        if new_active and not old_active:
            if self._zone_manager.manual_active(zone_id):
                return
            log_debug(
                self._config.debug,
                "Manual control reported by switch for %s -> %s",
                zone_id,
                new_manual,
            )
            await self._schedule(zone_id, source="al_switch", lights=new_manual)
            return
        if not new_active and old_active:
            log_debug(
                self._config.debug,
                "Manual control cleared for %s",
                zone_id,
            )
            if (
                not self._zone_manager.manual_active(zone_id)
                and self._timer_manager.remaining(zone_id) <= 0
            ):
                return
            self._event_bus.post(
                EVENT_MANUAL_RELEASED,
                zone=zone_id,
                source="al_switch",
                previous_lights=old_manual,
            )

    def _should_consider_light(self, event: Event) -> bool:
        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")
        if new_state is None or old_state is None:
            return False
        if new_state.state != old_state.state:
            return True
        tracked_keys = ("brightness", "color_temp", "color_temp_kelvin", "color_temp_mired")
        for key in tracked_keys:
            if new_state.attributes.get(key) != old_state.attributes.get(key):
                return True
        return False

    async def _schedule(
        self,
        zone_id: str,
        *,
        source: str = "unknown",
        lights: Iterable[str] | None = None,
    ) -> None:
        log_debug(
            self._config.debug,
            "Manual change detected for %s via %s",
            zone_id,
            source,
        )
        task = self._pending.get(zone_id)
        if task:
            task.cancel()

        async def _fire() -> None:
            await asyncio.sleep(MANUAL_DEBOUNCE_MS / 1000)
            duration = self._timer_manager.compute_duration_seconds(zone_id)
            self._event_bus.post(
                EVENT_MANUAL_DETECTED,
                zone=zone_id,
                duration_s=duration,
            )

        self._pending[zone_id] = self._hass.async_create_task(_fire())

    @staticmethod
    def _extract_manual_list(state: State | None) -> List[str]:
        if state is None:
            return []
        manual = state.attributes.get("manual_control")
        if isinstance(manual, list):
            return manual
        if isinstance(manual, tuple):
            return list(manual)
        return []
