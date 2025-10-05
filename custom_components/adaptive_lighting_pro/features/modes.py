"""Mode management."""
from __future__ import annotations

from dataclasses import dataclass

from ..const import EVENT_MODE_CHANGED


@dataclass
class ModeConfig:
    default_mode: str = "adaptive"


class ModeManager:
    def __init__(self, event_bus, timer_manager) -> None:
        self._event_bus = event_bus
        self._timer_manager = timer_manager
        self._mode = "adaptive"

    @property
    def mode(self) -> str:
        return self._mode

    def available_modes(self) -> list[str]:
        """Return the modes currently supported by the timer manager."""

        return self._timer_manager.available_modes()

    def select(self, mode: str) -> None:
        if mode not in self.available_modes():
            raise ValueError(f"Unknown mode {mode}")
        self._mode = mode
        self._timer_manager.set_mode(mode)
        self._event_bus.post(EVENT_MODE_CHANGED, mode=mode)

    def ensure_valid_mode(self) -> None:
        """Ensure the current mode is still supported after option changes."""

        if self._mode not in self.available_modes():
            self._mode = "adaptive"
            self._timer_manager.set_mode(self._mode)
            self._event_bus.post(EVENT_MODE_CHANGED, mode=self._mode)
