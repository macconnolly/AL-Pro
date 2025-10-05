"""Simple state machine helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class SystemState:
    mode: str = "adaptive"
    scene: str = "default"
    environment: Dict[str, float] | None = None

    def as_dict(self) -> Dict[str, str]:
        return {
            "mode": self.mode,
            "scene": self.scene,
        }
