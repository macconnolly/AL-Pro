"""Pytest configuration for Adaptive Lighting Pro tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import CONF_NAME
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.adaptive_lighting_pro.const import (
    DOMAIN,
    CONF_ZONES,
)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Adaptive Lighting Pro Test",
        data={
            CONF_NAME: "Test Instance",
            "zones": [
                {
                    "zone_id": "main_living",
                    "id": "main_living",
                    "name": "Main Living",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_main_living",
                    "lights": ["light.living_room_lamp", "light.living_room_floor"],
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "color_temp_min": 2500,
                    "color_temp_max": 5500,
                    "enabled": True,
                    "environmental_enabled": True,
                    "sunset_enabled": True,
                },
                {
                    "zone_id": "bedroom",
                    "id": "bedroom",
                    "name": "Bedroom",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_bedroom",
                    "lights": ["light.bedroom_lamp"],
                    "brightness_min": 20,
                    "brightness_max": 60,
                    "color_temp_min": 2200,
                    "color_temp_max": 4000,
                    "enabled": True,
                    "environmental_enabled": True,
                    "sunset_enabled": True,
                },
                {
                    "zone_id": "kitchen",
                    "id": "kitchen",
                    "name": "Kitchen",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_kitchen",
                    "lights": ["light.kitchen_pendant"],
                    "brightness_min": 60,
                    "brightness_max": 100,
                    "color_temp_min": 3000,
                    "color_temp_max": 6500,
                    "enabled": True,
                    "environmental_enabled": False,  # Disabled for testing
                    "sunset_enabled": False,
                },
            ],
            "global_settings": {
                "brightness_increment": 5,
                "warmth_increment": 250,
                "manual_timer_duration": 3600,
            },
            "environmental": {
                "lux_sensor": "sensor.outdoor_illuminance",
                "weather_entity": "weather.home",
                "enabled": True,
            },
            "integrations": {},
        },
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_hass() -> HomeAssistant:
    """Return a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.services = MagicMock()
    hass.bus = MagicMock()
    hass.config = MagicMock()
    hass.config.time_zone = "America/New_York"

    # Setup states mock with default sensor values
    def get_state(entity_id):
        state = MagicMock()
        if entity_id == "sensor.outdoor_illuminance":
            state.state = "500"  # Medium lux
            state.attributes = {}
        elif entity_id == "weather.home":
            state.state = "sunny"
            state.attributes = {}
        elif entity_id == "sun.sun":
            state.state = "above_horizon"
            state.attributes = {"elevation": 45.0}
        else:
            return None
        return state

    states_mock = MagicMock()
    states_mock.get = MagicMock(side_effect=get_state)
    hass.states = states_mock
    return hass


@pytest.fixture
def mock_lux_sensor():
    """Mock lux sensor state."""
    state = MagicMock()
    state.state = "500"  # Medium brightness
    state.attributes = {}
    return state


@pytest.fixture
def mock_weather_entity():
    """Mock weather entity state."""
    state = MagicMock()
    state.state = "cloudy"
    state.attributes = {
        "temperature": 15,
        "humidity": 75,
    }
    return state


@pytest.fixture
def mock_sun_entity():
    """Mock sun.sun entity state."""
    state = MagicMock()
    state.state = "above_horizon"
    state.attributes = {
        "elevation": 45.0,
        "azimuth": 180.0,
        "rising": False,
        "next_rising": "2025-10-02T06:30:00+00:00",
        "next_setting": "2025-10-01T18:45:00+00:00",
    }
    return state


@pytest.fixture
def mock_al_switch():
    """Mock Adaptive Lighting switch state."""
    state = MagicMock()
    state.state = "on"
    state.attributes = {
        "manual_control": [],  # No lights manually controlled
        "min_brightness": 45,
        "max_brightness": 100,
        "min_color_temp": 2500,
        "max_color_temp": 5500,
    }
    return state


@pytest.fixture
def mock_al_switch_with_manual():
    """Mock AL switch with manual control active."""
    state = MagicMock()
    state.state = "on"
    state.attributes = {
        "manual_control": ["light.living_room_lamp", "light.living_room_floor"],
        "min_brightness": 45,
        "max_brightness": 100,
        "min_color_temp": 2500,
        "max_color_temp": 5500,
    }
    return state


@pytest.fixture
def mock_datetime_winter_morning():
    """Mock datetime for winter morning (dark conditions)."""
    # January 15, 2025, 7:00 AM
    return datetime(2025, 1, 15, 7, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_datetime_summer_afternoon():
    """Mock datetime for summer afternoon (bright conditions)."""
    # July 15, 2025, 2:00 PM
    return datetime(2025, 7, 15, 14, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_datetime_night():
    """Mock datetime for night (time multiplier = 0)."""
    # Any date, 11:00 PM
    return datetime(2025, 10, 1, 23, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_datetime_dawn():
    """Mock datetime for dawn (time multiplier = 0.7)."""
    # Any date, 7:00 AM
    return datetime(2025, 10, 1, 7, 0, 0, tzinfo=UTC)


@pytest.fixture
def setup_hass_states(
    mock_hass,
    mock_lux_sensor,
    mock_weather_entity,
    mock_sun_entity,
    mock_al_switch,
):
    """Setup common hass state mocks."""
    def get_state(entity_id):
        if entity_id == "sensor.outdoor_illuminance":
            return mock_lux_sensor
        elif entity_id == "weather.home":
            return mock_weather_entity
        elif entity_id == "sun.sun":
            return mock_sun_entity
        elif entity_id.startswith("switch.adaptive_lighting_"):
            return mock_al_switch
        return None

    mock_hass.states.get.side_effect = get_state
    return mock_hass
