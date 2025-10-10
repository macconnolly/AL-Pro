"""Mode manager handles prioritized scenes."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional

from .const import DEFAULT_MODE_PRIORITY
from .models import ModeProfile, ModeState


@dataclass(slots=True)
class ModeMetrics:
    activations: Dict[str, int]

    @classmethod
    def empty(cls) -> "ModeMetrics":
        return cls(activations={})

    def record(self, mode: str) -> None:
        self.activations[mode] = self.activations.get(mode, 0) + 1


class ModeManager:
    """Prioritized mode stack tracked per zone."""

    def __init__(self, priorities: Optional[Dict[str, int]] = None) -> None:
        self._priorities = priorities or dict(DEFAULT_MODE_PRIORITY)
        self._active: Dict[str, Dict[str, ModeProfile]] = defaultdict(dict)
        self._metrics: Dict[str, ModeMetrics] = defaultdict(ModeMetrics.empty)

    def set_mode(self, zone_id: str, mode: str, profile: ModeProfile) -> ModeState:
        zone_modes = self._active[zone_id]
        zone_modes[mode] = profile
        self._metrics[zone_id].record(mode)
        return self._resolve(zone_id)

    def clear_mode(self, zone_id: str, mode: str) -> ModeState:
        zone_modes = self._active.get(zone_id)
        if not zone_modes:
            return self._resolve(zone_id)
        zone_modes.pop(mode, None)
        if not zone_modes:
            self._active.pop(zone_id, None)
        return self._resolve(zone_id)

    def get_state(self, zone_id: str) -> ModeState:
        return self._resolve(zone_id)

    def _resolve(self, zone_id: str) -> ModeState:
        zone_modes = self._active.get(zone_id)
        if not zone_modes:
            return ModeState(active_mode=None, profile=ModeProfile())
        sorted_modes = sorted(
            zone_modes.items(),
            key=lambda item: self._priorities.get(item[0], 0),
            reverse=True,
        )
        name, profile = sorted_modes[0]
        return ModeState(active_mode=name, profile=profile)

    def metrics_for_zone(self, zone_id: str) -> ModeMetrics:
        return self._metrics[zone_id]
