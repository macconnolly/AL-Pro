"""Runtime wiring between LayerManagerEngine and Home Assistant."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .bridge import LayerCommand
from .engine import LayerManagerEngine
from .environment import SensorReading
from .models import ModeProfile, ZoneModel


ENVIRONMENT_PREFIX = "environment_"


class LayerManagerRuntime:
    """High-level runtime owning engine, service dispatch, and listeners."""

    def __init__(
        self,
        hass: HomeAssistant,
        zones: Dict[str, ZoneModel],
        layer_domain: str = "layer_manager",
        coordinator: Optional[object] = None,
    ) -> None:
        self.hass = hass
        self.zones = zones
        self.coordinator = coordinator
        self.engine = LayerManagerEngine(zones, layer_domain=layer_domain, command_executor=self._execute_command)
        self._env_entity_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self._unsubscribers: List[CALLBACK_TYPE] = []
        self._build_environment_index()

    async def async_start(self) -> None:
        """Attach entity listeners for environment signals."""

        for entity_id in self._env_entity_index.keys():
            unsub = async_track_state_change_event(self.hass, [entity_id], self._handle_environment_event)
            self._unsubscribers.append(unsub)

    async def async_stop(self) -> None:
        """Detach listeners and cleanup."""

        while self._unsubscribers:
            unsub = self._unsubscribers.pop()
            unsub()

    def handles_zone(self, zone_id: str) -> bool:
        return zone_id in self.zones

    async def async_sync_zone(self, zone_id: str, now: Optional[datetime] = None) -> None:
        now = now or dt_util.utcnow()
        computation = await self.engine.async_dispatch_zone(zone_id, now)
        self._publish_mode_telemetry(zone_id, computation)

    async def async_start_manual(
        self,
        zone_id: str,
        brightness: float,
        kelvin: int,
        reason: str,
        duration: Optional[int] = None,
    ) -> None:
        now = dt_util.utcnow()
        self.engine.start_manual_override(zone_id, brightness, kelvin, reason, now, duration)
        await self.async_sync_zone(zone_id, now)

    async def async_extend_manual(self, zone_id: str, minutes: int) -> None:
        self.engine.extend_manual_override(zone_id, minutes)
        await self.async_sync_zone(zone_id)

    async def async_clear_manual(self, zone_id: str) -> None:
        self.engine.clear_manual_override(zone_id)
        await self.async_sync_zone(zone_id)

    async def async_set_mode(self, zone_id: str, mode: str, profile: ModeProfile) -> None:
        self.engine.apply_mode(zone_id, mode, profile)
        await self.async_sync_zone(zone_id)

    async def async_clear_mode(self, zone_id: str, mode: str) -> None:
        self.engine.clear_mode(zone_id, mode)
        await self.async_sync_zone(zone_id)

    async def async_reload_zones(self, zones: Dict[str, ZoneModel]) -> None:
        await self.async_stop()
        self.zones = zones
        self.engine = LayerManagerEngine(zones, command_executor=self._execute_command)
        self._env_entity_index.clear()
        self._build_environment_index()
        await self.async_start()

    async def _execute_command(self, command: LayerCommand) -> None:
        domain, service = command.service.split(".", 1)
        await self.hass.services.async_call(domain, service, command.data, blocking=True)

    def _build_environment_index(self) -> None:
        for zone in self.zones.values():
            for helper_key, entity_id in zone.helpers.items():
                if not helper_key.startswith(ENVIRONMENT_PREFIX):
                    continue
                profile = helper_key[len(ENVIRONMENT_PREFIX) :]
                self._env_entity_index[entity_id].append((zone.zone_id, profile))

    @callback
    def _handle_environment_event(self, event: Event) -> None:
        new_state: Optional[State] = event.data.get("new_state")
        entity_id: str = event.data.get("entity_id")
        if entity_id not in self._env_entity_index:
            return

        for zone_id, profile in self._env_entity_index[entity_id]:
            reading = self._state_to_reading(new_state, profile)
            if not reading:
                continue
            self.engine.environment.update_sensor(reading)
            zone = self.zones[zone_id]
            self.engine.environment.compute_state(zone.zone_id, zone.environment, dt_util.utcnow())

    def _state_to_reading(self, state: Optional[State], profile: str) -> Optional[SensorReading]:
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return SensorReading(profile, 0, dt_util.utcnow(), available=False)

        try:
            value = float(state.state)
        except (ValueError, TypeError):
            value = 1.0 if state.state in (STATE_ON, "home", "occupied", "True", "true") else 0.0

        available = state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        return SensorReading(profile, value, state.last_changed, available=available)

    def _publish_mode_telemetry(self, zone_id: str, computation) -> None:
        if not self.coordinator or not hasattr(self.coordinator, "register_external_summary"):
            return

        payload = {
            "zone_id": zone_id,
            "timestamp": dt_util.utcnow().isoformat(),
        }
        if computation:
            payload.update(
                {
                    "source": computation.source,
                    "transition": computation.transition,
                    "layers": [layer.layer_id for layer in computation.layers],
                    "details": computation.details,
                }
            )

        self.coordinator.register_external_summary("al_layer_manager", payload)

