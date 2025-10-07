"""Test manual control paradigm implementation.

Tests that _apply_adjustments_to_zone properly checks AL's manual_control
attribute and skips zones that have manual control set, per implementation_1.yaml.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, UTC

from custom_components.adaptive_lighting_pro.coordinator import ALPDataUpdateCoordinator


async def test_apply_skips_zones_with_manual_control(hass):
    """Verify _apply_adjustments_to_zone skips when AL has manual_control set.

    PARADIGM: Manual-Aware Application Engine
    From implementation_1.yaml - always check manual_control before applying changes.
    """
    # Create mock config entry
    mock_config_entry = Mock()
    mock_config_entry.data = {}
    mock_config_entry.entry_id = "test_entry"

    # Create coordinator with test zone
    coordinator = ALPDataUpdateCoordinator(hass, mock_config_entry)
    coordinator.zones = {
        "test_zone": {
            "adaptive_lighting_switch": "switch.adaptive_lighting_test",
            "lights": ["light.test1", "light.test2"],
            "enabled": True,
            "brightness_min": 20,
            "brightness_max": 80,
        }
    }

    # Mock environmental and sunset adapters
    coordinator._env_adapter = Mock()
    coordinator._env_adapter.calculate_boost = Mock(return_value=10)
    coordinator._sunset_adapter = Mock()
    coordinator._sunset_adapter.calculate_boost = Mock(return_value=5)

    # Set some adjustments
    coordinator._brightness_adjustment = 20
    coordinator._warmth_adjustment = 500

    # Mock AL switch state WITH manual_control
    mock_al_state = Mock()
    mock_al_state.attributes = {
        "manual_control": ["light.test1", "light.test2"]  # Lights are manually controlled
    }

    # Mock on coordinator.hass instead of test hass
    coordinator.hass.states.get = Mock(return_value=mock_al_state)
    coordinator.hass.services.async_call = AsyncMock()
    # Apply adjustments - should skip due to manual_control
    await coordinator._apply_adjustments_to_zone(
        "test_zone",
        coordinator.zones["test_zone"]
    )

    # CRITICAL: Verify NO service calls were made
    coordinator.hass.services.async_call.assert_not_called()


async def test_apply_proceeds_when_no_manual_control(hass):
    """Verify _apply_adjustments_to_zone proceeds when manual_control is empty.

    This is the normal case - AL doesn't have manual control, so we apply changes.
    """
    # Create mock config entry
    mock_config_entry = Mock()
    mock_config_entry.data = {}
    mock_config_entry.entry_id = "test_entry"

    # Create coordinator with test zone
    coordinator = ALPDataUpdateCoordinator(hass, mock_config_entry)
    coordinator.zones = {
        "test_zone": {
            "adaptive_lighting_switch": "switch.adaptive_lighting_test",
            "lights": ["light.test1", "light.test2"],
            "enabled": True,
            "brightness_min": 20,
            "brightness_max": 80,
        }
    }

    # Mock environmental and sunset adapters
    coordinator._env_adapter = Mock()
    coordinator._env_adapter.calculate_boost = Mock(return_value=10)
    coordinator._sunset_adapter = Mock()
    coordinator._sunset_adapter.calculate_boost = Mock(return_value=5)

    # Set some adjustments
    coordinator._brightness_adjustment = 20
    coordinator._warmth_adjustment = 0

    # Mock scene offsets
    coordinator._scene_offsets_by_zone = {}
    coordinator._scene_brightness_offset = 0
    coordinator._scene_warmth_offset = 0

    # Mock AL switch state WITHOUT manual_control (empty list)
    mock_al_state = Mock()
    mock_al_state.attributes = {
        "manual_control": []  # No manual control
    }

    # Mock on coordinator.hass instead of test hass
    coordinator.hass.states.get = Mock(return_value=mock_al_state)
    coordinator.hass.services.async_call = AsyncMock()
    # Apply adjustments - should proceed
    await coordinator._apply_adjustments_to_zone(
        "test_zone",
        coordinator.zones["test_zone"]
    )

    # Verify service calls WERE made
    assert coordinator.hass.services.async_call.call_count == 2  # change_switch_settings + apply

    # Verify change_switch_settings was called with correct parameters
    change_call = coordinator.hass.services.async_call.call_args_list[0]
    assert change_call[0][0] == "adaptive_lighting"
    assert change_call[0][1] == "change_switch_settings"
    assert change_call[0][2]["entity_id"] == "switch.adaptive_lighting_test"
    assert change_call[0][2]["use_defaults"] == "configuration"  # Required parameter
    assert "min_brightness" in change_call[0][2]
    assert "max_brightness" in change_call[0][2]

    # Verify apply was called with correct parameters
    apply_call = coordinator.hass.services.async_call.call_args_list[1]
    assert apply_call[0][0] == "adaptive_lighting"
    assert apply_call[0][1] == "apply"
    assert apply_call[0][2]["entity_id"] == "switch.adaptive_lighting_test"
    assert apply_call[0][2]["turn_on_lights"] == False
    assert apply_call[0][2]["transition"] == 1
    assert "lights" not in apply_call[0][2]  # Should NOT specify lights for normal apply


async def test_service_call_parameters_consistency(hass):
    """Verify all AL service calls use consistent parameters.

    PARADIGM: Service Call Patterns
    - Always use use_defaults: configuration
    - Always use turn_on_lights: False
    - Always include transition (1 or 2 seconds)
    """
    # Create mock config entry
    mock_config_entry = Mock()
    mock_config_entry.data = {}
    mock_config_entry.entry_id = "test_entry"

    coordinator = ALPDataUpdateCoordinator(hass, mock_config_entry)
    coordinator.zones = {
        "test_zone": {
            "adaptive_lighting_switch": "switch.adaptive_lighting_test",
            "lights": ["light.test1"],
            "enabled": True,
            "brightness_min": 20,
            "brightness_max": 80,
        }
    }

    # Mock dependencies
    coordinator._env_adapter = Mock()
    coordinator._env_adapter.calculate_boost = Mock(return_value=0)
    coordinator._sunset_adapter = Mock()
    coordinator._sunset_adapter.calculate_boost = Mock(return_value=0)
    coordinator._brightness_adjustment = 10
    coordinator._warmth_adjustment = 0
    coordinator._scene_offsets_by_zone = {}
    coordinator._scene_brightness_offset = 0
    coordinator._scene_warmth_offset = 0

    # Mock AL switch without manual control
    mock_al_state = Mock()
    mock_al_state.attributes = {"manual_control": []}

    # Mock on coordinator.hass instead of test hass
    coordinator.hass.states.get = Mock(return_value=mock_al_state)
    coordinator.hass.services.async_call = AsyncMock()
    # Apply adjustments
    await coordinator._apply_adjustments_to_zone(
        "test_zone",
        coordinator.zones["test_zone"]
    )

    # Check change_switch_settings parameters
    change_call = coordinator.hass.services.async_call.call_args_list[0][0][2]
    assert change_call["use_defaults"] == "configuration", "Missing required use_defaults"

    # Check apply parameters
    apply_call = coordinator.hass.services.async_call.call_args_list[1][0][2]
    assert apply_call["turn_on_lights"] == False, "Should not turn on lights"
    assert apply_call["transition"] == 1, "Should have transition"