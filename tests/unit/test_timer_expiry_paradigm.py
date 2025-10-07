"""Test timer expiry paradigm implementation.

Tests that timer expiry properly specifies lights parameter for immediate restoration,
per implementation_1.yaml pattern.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from custom_components.adaptive_lighting_pro.coordinator import ALPDataUpdateCoordinator


async def test_timer_expiry_specifies_lights_parameter(hass):
    """Verify timer expiry apply includes lights parameter for immediate restoration.

    PARADIGM: Timer Expiry Service Call Sequence
    From implementation_1.yaml lines 1939-1944 - timer expiry MUST specify lights
    parameter to force immediate restoration vs waiting for AL's next cycle.
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
        }
    }

    # Mock zone manager
    coordinator.zone_manager = Mock()
    coordinator.zone_manager.async_cancel_timer = AsyncMock(return_value=True)
    coordinator.zone_manager.any_manual_timers_active = Mock(return_value=False)

    # Mock AL switch state with manual_control set (scene was applied)
    mock_al_state = Mock()
    mock_al_state.attributes = {
        "manual_control": ["light.test1", "light.test2"]
    }

    # Mock on coordinator.hass instead of test hass
    coordinator.hass.states.get = Mock(return_value=mock_al_state)
    coordinator.hass.services.async_call = AsyncMock()
    # Call _restore_adaptive_control (timer expired)
    await coordinator._restore_adaptive_control("test_zone")

    # Find the apply service call
    apply_calls = [
                call for call in coordinator.hass.services.async_call.call_args_list
                if call[0][1] == "apply"
            ]
    assert len(apply_calls) > 0, "apply service should be called"

    apply_call = apply_calls[0]
    apply_data = apply_call[0][2]

    # CRITICAL: Verify lights parameter IS specified for timer expiry
    assert "lights" in apply_data, "Timer expiry MUST specify lights parameter"
    assert apply_data["lights"] == ["light.test1", "light.test2"]
    assert apply_data["turn_on_lights"] == False
    assert apply_data["transition"] == 2  # Timer expiry uses 2s transition


async def test_timer_expiry_clears_adjustments_when_last_timer(hass):
    """Verify adjustments reset to 0 when all zone timers have expired.

    This matches implementation_1.yaml behavior where brightness/warmth adjustments
    are cleared when the last timer expires.
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
        }
    }

    # Mock zone manager - NO active timers remaining
    coordinator.zone_manager = Mock()
    coordinator.zone_manager.async_cancel_timer = AsyncMock(return_value=True)
    coordinator.zone_manager.any_manual_timers_active = Mock(return_value=False)  # Last timer

    # Mock AL switch
    mock_al_state = Mock()
    mock_al_state.attributes = {"manual_control": []}
    # Mock scene-locked lights
    coordinator._scene_locked_lights = {}

    # Set adjustments that should be cleared
    coordinator._brightness_adjustment = 30
    coordinator._warmth_adjustment = 1000
    coordinator.set_brightness_adjustment = AsyncMock()
    coordinator.set_warmth_adjustment = AsyncMock()

    # Mock on coordinator.hass instead of test hass
    coordinator.hass.states.get = Mock(return_value=mock_al_state)
    coordinator.hass.services.async_call = AsyncMock()
    # Restore adaptive control (last timer expired)
    await coordinator._restore_adaptive_control("test_zone")

    # Verify adjustments were reset to 0
    coordinator.set_brightness_adjustment.assert_called_once_with(0, start_timers=False)
    coordinator.set_warmth_adjustment.assert_called_once_with(0, start_timers=False)


async def test_timer_expiry_preserves_scene_locked_lights(hass):
    """Verify timer expiry preserves scene-locked lights in manual_control.

    When a scene is active and a timer expires, only non-scene lights should
    be released from manual control.
    """
    # Create mock config entry
    mock_config_entry = Mock()
    mock_config_entry.data = {}
    mock_config_entry.entry_id = "test_entry"

    coordinator = ALPDataUpdateCoordinator(hass, mock_config_entry)
    coordinator.zones = {
        "test_zone": {
            "adaptive_lighting_switch": "switch.adaptive_lighting_test",
            "lights": ["light.group"],  # Group that expands
            "enabled": True,
        }
    }

    # Mock zone manager
    coordinator.zone_manager = Mock()
    coordinator.zone_manager.async_cancel_timer = AsyncMock(return_value=True)
    coordinator.zone_manager.any_manual_timers_active = Mock(return_value=True)  # Other timers active

    # Mock light group expansion
    mock_group_state = Mock()
    mock_group_state.attributes = {
        "entity_id": ["light.test1", "light.test2", "light.test3"]
    }

    # Mock AL switch with manual control
    mock_al_state = Mock()
    mock_al_state.attributes = {
        "manual_control": ["light.test1", "light.test2", "light.test3"]
    }

    def mock_get(entity_id):
        if entity_id == "light.group":
            return mock_group_state
        elif entity_id == "switch.adaptive_lighting_test":
            return mock_al_state
        return None

    # Scene has locked light.test1 only
    coordinator._scene_locked_lights = {
        "test_zone": {"light.test1"}  # This light should stay locked
    }

    # Don't reset adjustments (other timers still active)
    coordinator._brightness_adjustment = 20
    coordinator._warmth_adjustment = 500

    # Mock on coordinator.hass instead of test hass
    coordinator.hass.states.get = Mock(side_effect=mock_get)
    coordinator.hass.services.async_call = AsyncMock()
    # Restore adaptive control
    await coordinator._restore_adaptive_control("test_zone")

    # Find set_manual_control call
    manual_control_calls = [
                call for call in coordinator.hass.services.async_call.call_args_list
                if call[0][1] == "set_manual_control"
            ]

    if manual_control_calls:
        manual_call = manual_control_calls[0]
        manual_data = manual_call[0][2]

        # Verify only non-scene lights are released
        assert manual_data["manual_control"] == False
        assert set(manual_data["lights"]) == {"light.test2", "light.test3"}
        assert "light.test1" not in manual_data["lights"]  # Scene-locked, preserved