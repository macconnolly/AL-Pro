"""Test Scene.AUTO functionality."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from custom_components.adaptive_lighting_pro.const import Scene, SCENE_CONFIGS
from custom_components.adaptive_lighting_pro.coordinator import ALPDataUpdateCoordinator


def test_scene_auto_exists():
    """Test Scene.AUTO is defined."""
    assert Scene.AUTO.value == "auto"
    assert Scene.AUTO in SCENE_CONFIGS


def test_scene_auto_config():
    """Test Scene.AUTO configuration."""
    config = SCENE_CONFIGS[Scene.AUTO]
    assert config["brightness_offset"] == 0
    assert config["warmth_offset"] == 0
    assert config["duration_minutes"] is None
    assert config["zones"] == {}
    assert "auto" in config["description"].lower()


@pytest.mark.asyncio
async def test_apply_scene_auto_clears_manual():
    """Test applying Scene.AUTO clears manual control."""
    # Create mock coordinator with required attributes
    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.data = {}

    coordinator = ALPDataUpdateCoordinator(mock_hass, mock_config_entry)

    # Initialize required attributes
    coordinator._manual_control = {"main_living", "kitchen"}
    coordinator._current_scene = Scene.EVENING_COMFORT
    coordinator.zones = {
        "main_living": {"name": "Main Living"},
        "kitchen": {"name": "Kitchen"}
    }
    coordinator.data = {}

    # Mock the methods we'll call
    coordinator.set_brightness_adjustment = AsyncMock(return_value=None)
    coordinator.set_warmth_adjustment = AsyncMock(return_value=None)
    coordinator.async_request_refresh = AsyncMock(return_value=None)
    coordinator._clear_zone_manual_control = MagicMock()

    # Apply auto scene
    result = await coordinator.apply_scene(Scene.AUTO)

    # Verify the scene was applied
    assert result is True

    # Verify manual control was cleared for all zones
    assert coordinator._clear_zone_manual_control.call_count == 2
    coordinator._clear_zone_manual_control.assert_any_call("main_living")
    coordinator._clear_zone_manual_control.assert_any_call("kitchen")

    # Verify scene is set to AUTO
    assert coordinator._current_scene == Scene.AUTO
    assert coordinator.data["current_scene"] == Scene.AUTO

    # Verify adjustments were reset
    coordinator.set_brightness_adjustment.assert_called_once_with(0, start_timers=False)
    coordinator.set_warmth_adjustment.assert_called_once_with(0)

    # Verify refresh was called
    coordinator.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_clear_zone_manual_control():
    """Test _clear_zone_manual_control method."""
    # Create mock coordinator
    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.data = {}

    coordinator = ALPDataUpdateCoordinator(mock_hass, mock_config_entry)

    # Setup test data
    coordinator.zones = {
        "main_living": {"name": "Main Living"},
        "kitchen": {"name": "Kitchen"}
    }
    coordinator._manual_control = {"main_living", "kitchen"}

    # Mock Home Assistant states
    mock_timer_state = MagicMock()
    mock_hass.states.get.return_value = mock_timer_state
    mock_hass.async_create_task = MagicMock()

    # Clear manual control for one zone
    coordinator._clear_zone_manual_control("main_living")

    # Verify manual control was removed
    assert "main_living" not in coordinator._manual_control
    assert "kitchen" in coordinator._manual_control  # Other zone unchanged

    # Verify timer cancel was scheduled
    mock_hass.states.get.assert_called_with("timer.alp_manual_main_living")
    mock_hass.async_create_task.assert_called_once()