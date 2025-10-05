"""Tests for timer expiry clearing manual adjustments.

This verifies the YAML-like behavior where:
- Button presses start timers (temporary overrides)
- When ALL zone timers expire, manual adjustments are cleared
- Slider adjustments persist (they don't start timers)

Follows patterns from TESTING_PATTERNS.md:
- Architectural tests verify coordinator API contracts
- Behavioral tests verify actual outcomes
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta, UTC

from custom_components.adaptive_lighting_pro.coordinator import ALPDataUpdateCoordinator
from custom_components.adaptive_lighting_pro.const import DOMAIN


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock()
    hass.data = {}  # Needs to be a real dict
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    hass.states = Mock()
    hass.states.get = Mock(return_value=None)
    hass.bus = Mock()
    hass.bus.async_fire = Mock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create mock config entry."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.data = {
        "zones": [
            {
                "id": "main_living",
                "zone_id": "main_living",
                "name": "Main Living",
                "lights": ["light.living_room"],
                "adaptive_lighting_switch": "switch.adaptive_lighting_main",
                "brightness_min": 45,
                "brightness_max": 100,
                "color_temp_min": 2000,
                "color_temp_max": 6500,
                "enabled": True,
            },
            {
                "id": "bedroom",
                "zone_id": "bedroom",
                "name": "Bedroom",
                "lights": ["light.bedroom"],
                "adaptive_lighting_switch": "switch.adaptive_lighting_bedroom",
                "brightness_min": 20,
                "brightness_max": 40,
                "color_temp_min": 2000,
                "color_temp_max": 4000,
                "enabled": True,
            },
        ],
        "environmental": {
            "lux_sensor": "sensor.outdoor_lux",
            "weather_entity": "weather.home",
            "enabled": False,
        },
        "global_settings": {},
    }
    return entry


@pytest.mark.asyncio
class TestTimerExpiryBehavior:
    """Test timer expiry clearing manual adjustments."""

    async def test_button_adjustment_cleared_when_all_timers_expire(
        self, mock_hass, mock_config_entry
    ):
        """SCENARIO: User presses Brighter button, timer expires after 2 hours

        GIVEN: User pressed Brighter button (+20% adjustment, timer started)
        WHEN: Timer expires for all zones
        THEN: Manual adjustment cleared to 0

        This matches YAML behavior (implementation_1.yaml:2054-2060)
        """
        # Create coordinator
        coordinator = ALPDataUpdateCoordinator(mock_hass, mock_config_entry)
        await coordinator.async_initialize()

        # Simulate button press: +20% brightness, starts timers
        await coordinator.set_brightness_adjustment(20, start_timers=True)

        # Verify adjustment is active
        assert coordinator.get_brightness_adjustment() == 20

        # Verify timers are active
        assert coordinator.zone_manager.any_manual_timers_active()

        # Simulate timer expiry for first zone
        zone_states = coordinator.zone_manager.get_all_zone_states()
        first_zone_id = list(zone_states.keys())[0]

        # Manually expire the timer
        zone_states[first_zone_id].manual_control_active = False
        zone_states[first_zone_id].timer_expiry = None

        # Call restore for first zone - should NOT clear yet (other zones still active)
        await coordinator._restore_adaptive_control(first_zone_id)

        # Adjustment should still be active (other zone timer still running)
        assert coordinator.get_brightness_adjustment() == 20

        # Now expire second zone timer
        second_zone_id = list(zone_states.keys())[1]
        zone_states[second_zone_id].manual_control_active = False
        zone_states[second_zone_id].timer_expiry = None

        # Call restore for second zone - should clear now (all timers expired)
        await coordinator._restore_adaptive_control(second_zone_id)

        # Adjustment should be cleared
        assert coordinator.get_brightness_adjustment() == 0
        assert coordinator.get_warmth_adjustment() == 0

    async def test_slider_adjustment_persists_no_timer(
        self, mock_hass, mock_config_entry
    ):
        """SCENARIO: User sets slider to +30%, no timer started

        GIVEN: User adjusted slider to +30% (start_timers=False)
        WHEN: No timer exists to expire
        THEN: Adjustment persists indefinitely

        This proves sliders are for persistent preferences.
        """
        # Create coordinator
        coordinator = ALPDataUpdateCoordinator(mock_hass, mock_config_entry)
        await coordinator.async_initialize()

        # Simulate slider adjustment: +30% brightness, NO timer
        await coordinator.set_brightness_adjustment(30, start_timers=False)

        # Verify adjustment is active
        assert coordinator.get_brightness_adjustment() == 30

        # Verify NO timers are active
        assert not coordinator.zone_manager.any_manual_timers_active()

        # Even if we call restore (shouldn't happen, but test defensive code)
        # The adjustment should persist because no timer was ever started
        for zone_id in coordinator.zones:
            await coordinator._restore_adaptive_control(zone_id)

        # Adjustment should STILL be active (slider = persistent)
        assert coordinator.get_brightness_adjustment() == 30

    async def test_mixed_button_then_slider_behavior(
        self, mock_hass, mock_config_entry
    ):
        """SCENARIO: Button press starts timer, then user adjusts slider

        GIVEN: User pressed button (+20%, timer started)
        WHEN: User then adjusts slider to +30% (overwrites value)
        THEN: Timer expiry clears the adjustment (timer was started by button)

        NOTE: This matches YAML behavior - timer expiry always clears,
        regardless of how value was last modified.
        """
        # Create coordinator
        coordinator = ALPDataUpdateCoordinator(mock_hass, mock_config_entry)
        await coordinator.async_initialize()

        # Step 1: Button press - starts timer
        await coordinator.set_brightness_adjustment(20, start_timers=True)
        assert coordinator.get_brightness_adjustment() == 20
        assert coordinator.zone_manager.any_manual_timers_active()

        # Step 2: Slider adjustment - overwrites value, timer keeps running
        await coordinator.set_brightness_adjustment(30, start_timers=False)
        assert coordinator.get_brightness_adjustment() == 30
        assert coordinator.zone_manager.any_manual_timers_active()  # Timer still active!

        # Step 3: Expire all timers
        zone_states = coordinator.zone_manager.get_all_zone_states()
        for zone_id, state in zone_states.items():
            state.manual_control_active = False
            state.timer_expiry = None
            await coordinator._restore_adaptive_control(zone_id)

        # Value cleared even though slider set it
        # This is YAML-like: timer expiry = end of session, clear adjustments
        assert coordinator.get_brightness_adjustment() == 0

    async def test_warmth_adjustment_also_cleared_on_expiry(
        self, mock_hass, mock_config_entry
    ):
        """SCENARIO: Both brightness and warmth adjustments cleared on expiry

        GIVEN: User adjusted both brightness (+20%) and warmth (+500K) via buttons
        WHEN: All timers expire
        THEN: BOTH adjustments cleared to 0

        Ensures comprehensive cleanup.
        """
        # Create coordinator
        coordinator = ALPDataUpdateCoordinator(mock_hass, mock_config_entry)
        await coordinator.async_initialize()

        # Set both adjustments via buttons (starts timers)
        await coordinator.set_brightness_adjustment(20, start_timers=True)
        await coordinator.set_warmth_adjustment(500, start_timers=True)

        assert coordinator.get_brightness_adjustment() == 20
        assert coordinator.get_warmth_adjustment() == 500

        # Expire all timers
        zone_states = coordinator.zone_manager.get_all_zone_states()
        for zone_id, state in zone_states.items():
            state.manual_control_active = False
            state.timer_expiry = None
            await coordinator._restore_adaptive_control(zone_id)

        # Both cleared
        assert coordinator.get_brightness_adjustment() == 0
        assert coordinator.get_warmth_adjustment() == 0

    async def test_partial_expiry_preserves_adjustments(
        self, mock_hass, mock_config_entry
    ):
        """SCENARIO: Only some zone timers expire

        GIVEN: 2 zones with active timers and +20% adjustment
        WHEN: Only 1 zone timer expires
        THEN: Adjustment preserved (at least 1 timer still active)

        Ensures we only clear when ALL timers expire.
        """
        # Create coordinator
        coordinator = ALPDataUpdateCoordinator(mock_hass, mock_config_entry)
        await coordinator.async_initialize()

        # Button press starts timers for all zones
        await coordinator.set_brightness_adjustment(20, start_timers=True)
        assert coordinator.get_brightness_adjustment() == 20

        # Expire only first zone's timer
        zone_states = coordinator.zone_manager.get_all_zone_states()
        first_zone_id = list(zone_states.keys())[0]
        zone_states[first_zone_id].manual_control_active = False
        zone_states[first_zone_id].timer_expiry = None

        # Restore first zone
        await coordinator._restore_adaptive_control(first_zone_id)

        # Adjustment should PERSIST (other zone timer still active)
        assert coordinator.get_brightness_adjustment() == 20
        assert coordinator.zone_manager.any_manual_timers_active()  # Second zone still has timer


@pytest.mark.asyncio
class TestAnyManualTimersActive:
    """Test zone_manager.any_manual_timers_active() helper method."""

    async def test_returns_true_when_timers_active(
        self, mock_hass, mock_config_entry
    ):
        """Verify method returns True when at least one timer is active."""
        coordinator = ALPDataUpdateCoordinator(mock_hass, mock_config_entry)
        await coordinator.async_initialize()

        # Start timer
        await coordinator.set_brightness_adjustment(20, start_timers=True)

        # Should return True
        assert coordinator.zone_manager.any_manual_timers_active() is True

    async def test_returns_false_when_no_timers(
        self, mock_hass, mock_config_entry
    ):
        """Verify method returns False when no timers are active."""
        coordinator = ALPDataUpdateCoordinator(mock_hass, mock_config_entry)
        await coordinator.async_initialize()

        # No timers started
        assert coordinator.zone_manager.any_manual_timers_active() is False

    async def test_returns_false_after_all_timers_expire(
        self, mock_hass, mock_config_entry
    ):
        """Verify method returns False after all timers expire."""
        coordinator = ALPDataUpdateCoordinator(mock_hass, mock_config_entry)
        await coordinator.async_initialize()

        # Start timers
        await coordinator.set_brightness_adjustment(20, start_timers=True)
        assert coordinator.zone_manager.any_manual_timers_active() is True

        # Expire all timers
        zone_states = coordinator.zone_manager.get_all_zone_states()
        for state in zone_states.values():
            state.manual_control_active = False
            state.timer_expiry = None

        # Should return False now
        assert coordinator.zone_manager.any_manual_timers_active() is False
