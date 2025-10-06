"""Shared pytest fixtures."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import sys
import types

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if "homeassistant" not in sys.modules:
    ha_module = types.ModuleType("homeassistant")
    sys.modules["homeassistant"] = ha_module

    const_module = types.ModuleType("homeassistant.const")
    const_module.STATE_ON = "on"
    const_module.STATE_UNAVAILABLE = "unavailable"
    const_module.STATE_UNKNOWN = "unknown"
    sys.modules["homeassistant.const"] = const_module

    class _Event:
        def __init__(self, entity_id: str, new_state: "_State") -> None:
            self.data = {"entity_id": entity_id, "new_state": new_state}

    class _State:
        def __init__(self, entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None) -> None:
            self.entity_id = entity_id
            self.state = state
            self.attributes = attributes or {}
            self.last_changed = datetime.utcnow()

    def _callback(func: Callable) -> Callable:
        return func

    class _Services:
        def __init__(self) -> None:
            self.calls: List[Dict[str, Any]] = []
            self.registered: List[tuple] = []

        async def async_call(self, domain: str, service: str, data: Dict[str, Any], blocking: bool = False) -> None:
            self.calls.append({"domain": domain, "service": service, "data": data, "blocking": blocking})

        def async_register(self, domain: str, service: str, handler: Callable) -> None:
            self.registered.append((domain, service, handler))

    class _HomeAssistant:
        def __init__(self) -> None:
            self.data: Dict[str, Any] = {}
            self.services = _Services()
            self._listeners: List[tuple] = []

    core_module = types.ModuleType("homeassistant.core")
    core_module.CALLBACK_TYPE = Callable[[], None]
    core_module.Event = _Event
    core_module.HomeAssistant = _HomeAssistant
    core_module.State = _State
    core_module.callback = _callback
    sys.modules["homeassistant.core"] = core_module

    def _track_state_change_event(hass: _HomeAssistant, entity_ids: List[str], action: Callable) -> Callable[[], None]:
        hass._listeners.append((entity_ids, action))

        def _unsub() -> None:
            hass._listeners = [item for item in hass._listeners if item[1] is not action]

        return _unsub

    helpers_event = types.ModuleType("homeassistant.helpers.event")
    helpers_event.async_track_state_change_event = _track_state_change_event
    sys.modules["homeassistant.helpers.event"] = helpers_event

    class _DTUtil(types.ModuleType):
        @staticmethod
        def utcnow() -> datetime:
            return datetime.utcnow()

    dt_module = _DTUtil("homeassistant.util.dt")
    util_package = types.ModuleType("homeassistant.util")
    util_package.dt = dt_module
    sys.modules["homeassistant.util"] = util_package
    sys.modules["homeassistant.util.dt"] = dt_module

    exceptions_module = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    exceptions_module.HomeAssistantError = HomeAssistantError
    sys.modules["homeassistant.exceptions"] = exceptions_module

from custom_components.al_layer_manager.engine import LayerManagerIntegration
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
