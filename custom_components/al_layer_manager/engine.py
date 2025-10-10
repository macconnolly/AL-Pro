"""Core orchestration engine for AL Layer Manager."""
from __future__ import annotations

from datetime import datetime
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

from .analytics import AnalyticsSuite
from .bridge import LayerCommand, LayerManagerBridge
from .environment import EnvironmentManager, SensorReading
from .manual import ManualIntentManager
from .mode import ModeManager
from .models import ModeProfile, ZoneComputation, ZoneModel
from .sync import SyncCoordinator


CommandExecutor = Callable[[LayerCommand], Awaitable[None]]


class LayerManagerEngine:
    """Pure orchestration layer combining managers and bridge."""

    def __init__(
        self,
        zones: Dict[str, ZoneModel],
        layer_domain: str = "layer_manager",
        command_executor: Optional[CommandExecutor] = None,
    ) -> None:
        self.zones = zones
        self.analytics = AnalyticsSuite()
        self.manual = ManualIntentManager()
        self.environment = EnvironmentManager()
        self.mode = ModeManager()
        self.bridge = LayerManagerBridge(layer_domain=layer_domain)
        self.sync = SyncCoordinator(self.manual, self.environment, self.mode, self.analytics)
        self._command_executor: Optional[CommandExecutor] = command_executor

    def set_command_executor(self, executor: CommandExecutor) -> None:
        """Register an async executor for layer manager commands."""

        self._command_executor = executor

    def compute_zone(self, zone_id: str, now: datetime) -> Tuple[ZoneComputation, List[LayerCommand]]:
        """Return the latest computation and bridge commands for a zone."""

        zone = self.zones[zone_id]
        computation = self.sync.compute(zone, now)
        commands = self.bridge.sync_zone(zone, computation.layers)
        return computation, commands

    async def async_dispatch_zone(self, zone_id: str, now: datetime) -> ZoneComputation:
        """Compute and dispatch commands for a zone if an executor is registered."""

        computation, commands = self.compute_zone(zone_id, now)
        if self._command_executor and commands:
            # Execute sequentially to maintain deterministic priority application order
            for command in commands:
                await self._command_executor(command)
        return computation

    def apply_mode(self, zone_id: str, mode: str, profile: ModeProfile) -> None:
        self.sync.apply_mode(zone_id, mode, profile)

    def clear_mode(self, zone_id: str, mode: str) -> None:
        self.sync.clear_mode(zone_id, mode)

    def start_manual_override(
        self,
        zone_id: str,
        brightness: float,
        kelvin: int,
        reason: str,
        now: datetime,
        duration: int | None = None,
    ) -> None:
        zone = self.zones[zone_id]
        self.manual.start_override(zone_id, zone.manual, brightness, kelvin, reason, now, duration)

    def clear_manual_override(self, zone_id: str) -> None:
        self.manual.clear_override(zone_id)

    def extend_manual_override(self, zone_id: str, minutes: int) -> None:
        self.manual.extend_override(zone_id, minutes)

    def update_environment(self, readings: Iterable[SensorReading], now: datetime) -> None:
        for reading in readings:
            self.environment.update_sensor(reading)
        for zone in self.zones.values():
            self.environment.compute_state(zone.zone_id, zone.environment, now)

    def snapshot_layers(self) -> Dict[Tuple[str, str], ZoneModel]:
        return {key: self.zones[key[0]] for key in self.bridge.snapshot().keys()}


# Backwards compatibility for tests importing the old symbol
LayerManagerIntegration = LayerManagerEngine

