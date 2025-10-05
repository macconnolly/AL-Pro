"""Datamodels for AL Layer Manager orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .const import DEFAULT_MANUAL_DURATION


@dataclass(slots=True)
class ManualBehaviorProfile:
    """Manual override configuration."""

    default_duration: int = DEFAULT_MANUAL_DURATION
    respect_manual_minutes: int = 30
    decay_rate: float = 0.1
    max_extra_brightness: float = 0.4
    min_brightness: float = 0.05
    max_brightness: float = 1.0

    def clamp_brightness(self, value: float) -> float:
        return max(self.min_brightness, min(self.max_brightness, value))


@dataclass(slots=True)
class EnvironmentProfile:
    """Environmental boost configuration."""

    foggy_boost: float = 0.25
    cloudy_boost: float = 0.15
    sad_boost: float = 0.35
    boost_cap: float = 0.4
    kelvin_floor: int = 2200
    kelvin_ceiling: int = 6500

    def apply_bounds(self, kelvin: int) -> int:
        return max(self.kelvin_floor, min(self.kelvin_ceiling, kelvin))


@dataclass(slots=True)
class ModeProfile:
    """Mode adjustments for brightness/kelvin."""

    brightness_multiplier: float = 1.0
    kelvin_adjustment: int = 0
    transition_seconds: int = 2


@dataclass(slots=True)
class ZoneModel:
    """Complete zone definition."""

    zone_id: str
    name: str
    lights: List[str]
    helpers: Dict[str, str]
    default_brightness: float
    default_kelvin: int
    manual: ManualBehaviorProfile = field(default_factory=ManualBehaviorProfile)
    environment: EnvironmentProfile = field(default_factory=EnvironmentProfile)
    modes: Dict[str, ModeProfile] = field(default_factory=dict)
    asymmetric_floor: float = 0.05
    asymmetric_ceiling: float = 1.0

    def clamp(self, brightness: float) -> float:
        return max(self.asymmetric_floor, min(self.asymmetric_ceiling, brightness))


@dataclass(slots=True)
class OverrideState:
    zone_id: str
    brightness: float
    kelvin: int
    reason: str
    expires_at: datetime

    def remaining_seconds(self, now: datetime) -> float:
        return max(0.0, (self.expires_at - now).total_seconds())


@dataclass(slots=True)
class EnvironmentState:
    zone_id: str
    brightness_offset: float = 0.0
    kelvin_offset: int = 0
    active_profiles: List[str] = field(default_factory=list)
    available: bool = True


@dataclass(slots=True)
class ModeState:
    active_mode: Optional[str]
    profile: ModeProfile


@dataclass(slots=True)
class LayerUpdate:
    """Represents a single layer_manager.insert_state call."""

    layer_id: str
    priority: int
    brightness: float
    kelvin: int
    transition: int
    state: str = "on"
    reason: Optional[str] = None

    def key(self) -> str:
        return self.layer_id

    def payload_hash(self) -> tuple:
        return (
            round(self.brightness, 4),
            self.kelvin,
            self.transition,
            self.state,
            self.reason,
            self.priority,
        )


@dataclass(slots=True)
class ZoneComputation:
    zone_id: str
    brightness: float
    kelvin: int
    source: str
    transition: int
    layers: List[LayerUpdate] = field(default_factory=list)
    details: Dict[str, float] = field(default_factory=dict)
