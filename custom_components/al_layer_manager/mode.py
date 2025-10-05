"""Mode manager handles prioritized scenes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

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
    """Prioritized mode stack."""

    def __init__(self, priorities: Optional[Dict[str, int]] = None) -> None:
        self._priorities = priorities or dict(DEFAULT_MODE_PRIORITY)
        self._active: Dict[str, ModeProfile] = {}
        self._metrics = ModeMetrics.empty()

    def set_mode(self, mode: str, profile: ModeProfile) -> ModeState:
        self._active[mode] = profile
        self._metrics.record(mode)
        name, active_profile = self._resolve()
        return ModeState(active_mode=name, profile=active_profile)

    def clear_mode(self, mode: str) -> ModeState:
        self._active.pop(mode, None)
        name, active_profile = self._resolve()
        return ModeState(active_mode=name, profile=active_profile)

    def get_state(self) -> ModeState:
        name, profile = self._resolve()
        return ModeState(active_mode=name, profile=profile)

    def _resolve(self) -> Tuple[Optional[str], ModeProfile]:
        if not self._active:
            return None, ModeProfile()
        sorted_modes = sorted(
            self._active.items(),
            key=lambda item: self._priorities.get(item[0], 0),
            reverse=True,
        )
        name, profile = sorted_modes[0]
        return name, profile

    @property
    def metrics(self) -> ModeMetrics:
        return self._metrics
