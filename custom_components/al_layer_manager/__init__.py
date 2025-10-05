"""Orchestration runtime for Adaptive Layer Manager."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Tuple

from .analytics import AnalyticsSuite
from .bridge import LayerCommand, LayerManagerBridge
from .environment import EnvironmentManager, SensorReading
from .manual import ManualIntentManager
from .mode import ModeManager
from .models import ModeProfile, ZoneComputation, ZoneModel
from .sync import SyncCoordinator


class LayerManagerIntegration:
    """High-level orchestrator bridging managers and layer_manager."""

    def __init__(self, zones: Dict[str, ZoneModel], layer_domain: str = "layer_manager") -> None:
        self.zones = zones
        self.analytics = AnalyticsSuite()
        self.manual = ManualIntentManager()
        self.environment = EnvironmentManager()
        self.mode = ModeManager()
        self.bridge = LayerManagerBridge(layer_domain=layer_domain)
        self.sync = SyncCoordinator(self.manual, self.environment, self.mode, self.analytics)

    def compute_zone(self, zone_id: str, now: datetime) -> Tuple[ZoneComputation, List[LayerCommand]]:
        zone = self.zones[zone_id]
        computation = self.sync.compute(zone, now)
        commands = self.bridge.sync_zone(zone, computation.layers)
        return computation, commands

    def apply_mode(self, mode: str, profile: ModeProfile) -> ZoneComputation:
        return self.sync.apply_mode(mode, profile)

    def clear_mode(self, mode: str) -> None:
        self.sync.clear_mode(mode)

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
