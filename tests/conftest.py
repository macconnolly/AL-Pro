"""Shared pytest fixtures."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_components.al_layer_manager import LayerManagerIntegration
from custom_components.al_layer_manager.models import (
    EnvironmentProfile,
    ManualBehaviorProfile,
    ModeProfile,
    ZoneModel,
)


@pytest.fixture
def sample_zone() -> ZoneModel:
    return ZoneModel(
        zone_id="office",
        name="Office",
        lights=["light.office_lamp"],
        helpers={"override_timer": "input_datetime.office_override"},
        default_brightness=0.35,
        default_kelvin=4000,
        manual=ManualBehaviorProfile(default_duration=25, respect_manual_minutes=35),
        environment=EnvironmentProfile(
            foggy_boost=0.3,
            cloudy_boost=0.2,
            sad_boost=0.4,
            boost_cap=0.45,
            kelvin_floor=2500,
            kelvin_ceiling=6000,
        ),
        modes={
            "focus": ModeProfile(brightness_multiplier=1.2, kelvin_adjustment=500, transition_seconds=2),
            "relax": ModeProfile(brightness_multiplier=0.7, kelvin_adjustment=-600, transition_seconds=3),
            "late_night": ModeProfile(brightness_multiplier=0.4, kelvin_adjustment=-800, transition_seconds=5),
        },
        asymmetric_floor=0.05,
        asymmetric_ceiling=1.0,
    )


@pytest.fixture
def integration(sample_zone: ZoneModel) -> LayerManagerIntegration:
    return LayerManagerIntegration(zones={sample_zone.zone_id: sample_zone})


@pytest.fixture
def now() -> datetime:
    return datetime.fromisoformat("2024-02-01T06:00:00")


@pytest.fixture
def fixture_dir() -> Path:
    return Path(__file__).parent / "fixtures"
