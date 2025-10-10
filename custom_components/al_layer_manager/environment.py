"""Environment manager for adaptive boosts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, Optional

from .const import ENVIRONMENT_PROFILES
from .models import EnvironmentProfile, EnvironmentState


@dataclass(slots=True)
class SensorReading:
    name: str
    value: float
    last_updated: datetime
    available: bool = True


class EnvironmentManager:
    """Aggregates sensor inputs and computes boosts."""

    def __init__(self) -> None:
        self._states: Dict[str, EnvironmentState] = {}
        self._sensor_cache: Dict[str, SensorReading] = {}

    def update_sensor(self, reading: SensorReading) -> None:
        self._sensor_cache[reading.name] = reading

    def compute_state(
        self,
        zone_id: str,
        profile: EnvironmentProfile,
        now: datetime,
    ) -> EnvironmentState:
        active: list[str] = []
        brightness_offset = 0.0
        kelvin_offset = 0
        available = True
        for name, payload in ENVIRONMENT_PROFILES.items():
            reading = self._sensor_cache.get(name)
            if reading is None or not reading.available:
                available = False
                continue
            if now - reading.last_updated > timedelta(minutes=30):
                available = False
                continue
            if reading.value >= 1:
                active.append(name)
                brightness_offset += payload["brightness"]
                kelvin_offset += payload["kelvin"]
        brightness_offset = min(profile.boost_cap, brightness_offset)
        kelvin_offset = max(-600, min(600, kelvin_offset))
        state = EnvironmentState(
            zone_id=zone_id,
            brightness_offset=brightness_offset,
            kelvin_offset=kelvin_offset,
            active_profiles=active,
            available=available,
        )
        self._states[zone_id] = state
        return state

    def get_state(self, zone_id: str) -> Optional[EnvironmentState]:
        return self._states.get(zone_id)

    def snapshot(self) -> Dict[str, EnvironmentState]:
        return dict(self._states)

    def drop_sensor(self, name: str) -> None:
        self._sensor_cache.pop(name, None)
