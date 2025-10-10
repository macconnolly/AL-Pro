"""Manual override manager."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from .models import ManualBehaviorProfile, OverrideState


@dataclass(slots=True)
class ManualMetrics:
    overrides_started: int = 0
    overrides_extended: int = 0
    overrides_cleared: int = 0


class ManualIntentManager:
    """Manages manual override lifecycle for zones."""

    def __init__(self) -> None:
        self._overrides: Dict[str, OverrideState] = {}
        self.metrics = ManualMetrics()

    def start_override(
        self,
        zone_id: str,
        profile: ManualBehaviorProfile,
        brightness: float,
        kelvin: int,
        reason: str,
        now: datetime,
        duration: Optional[int] = None,
    ) -> OverrideState:
        minutes = duration or profile.default_duration
        brightness = profile.clamp_brightness(brightness)
        expires_at = now + timedelta(minutes=minutes)
        state = OverrideState(zone_id, brightness, kelvin, reason, expires_at)
        self._overrides[zone_id] = state
        self.metrics.overrides_started += 1
        return state

    def extend_override(self, zone_id: str, additional_minutes: int) -> OverrideState:
        if zone_id not in self._overrides:
            raise KeyError(f"Zone {zone_id} has no override to extend")
        state = self._overrides[zone_id]
        state.expires_at += timedelta(minutes=additional_minutes)
        self.metrics.overrides_extended += 1
        return state

    def clear_override(self, zone_id: str) -> None:
        self._overrides.pop(zone_id, None)
        self.metrics.overrides_cleared += 1

    def get_override(self, zone_id: str, now: datetime) -> Optional[OverrideState]:
        state = self._overrides.get(zone_id)
        if not state:
            return None
        if state.expires_at <= now:
            self._overrides.pop(zone_id, None)
            return None
        return state

    def decay_brightness(self, zone_id: str, now: datetime, target: float) -> Optional[OverrideState]:
        state = self.get_override(zone_id, now)
        if not state:
            return None
        if target >= state.brightness:
            return state
        decayed = max(target, state.brightness - 0.1)
        new_state = OverrideState(zone_id, decayed, state.kelvin, state.reason, state.expires_at)
        self._overrides[zone_id] = new_state
        return new_state

    def snapshot(self) -> Dict[str, OverrideState]:
        return dict(self._overrides)
