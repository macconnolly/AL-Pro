"""Tests for Zen32 scene controller integration.

REAL SCENARIO TESTING (claude.md):
- Test like YOU are using the physical Zen32 controller
- Simulate button presses, holds, rapid presses
- Verify debouncing prevents duplicate actions
- Test graceful degradation (missing entities, service failures)

Phase 3.1 Implementation - Physical Button Control
"""

import pytest
import time
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, patch, call

from custom_components.adaptive_lighting_pro.integrations.zen32 import Zen32Integration


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def mock_coordinator():
    """Create mock coordinator with test data."""
    coordinator = Mock()
    coordinator.get_brightness_adjustment = Mock(return_value=0)
    coordinator.get_warmth_adjustment = Mock(return_value=0)
    coordinator.data = {
        "global": {
            "brightness_increment": 10,
            "color_temp_increment": 500,
        }
    }
    return coordinator


@pytest.fixture
def zen32_integration(mock_hass, mock_coordinator):
    """Create Zen32Integration instance for testing."""
    integration = Zen32Integration(mock_hass, mock_coordinator)
    return integration


class TestZen32Setup:
    """Test Zen32 integration setup and lifecycle."""

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_setup_with_all_buttons_configured_succeeds(
        self, zen32_integration, mock_hass
    ):
        """Zen32 setup with all 5 buttons configured should succeed.

        REAL SCENARIO: Initial setup with all event entities available
        EXPECTED: All 5 event listeners registered successfully
        WHY CRITICAL: Full button functionality requires all listeners active
        BUG WOULD CAUSE: Some buttons not responding to presses
        """
        # Mock all button entities as available
        def mock_states_get(entity_id):
            return Mock(state="2025-10-01T10:00:00")

        mock_hass.states.get = mock_states_get

        # Configure with all 5 buttons
        zen32_integration.configure(
            enabled=True,
            button_entities={
                "button_1": "event.scene_controller_scene_001",
                "button_2": "event.scene_controller_scene_002",
                "button_3": "event.scene_controller_scene_003",
                "button_4": "event.scene_controller_scene_004",
                "button_5": "event.scene_controller_scene_005",
            },
            button_actions={
                "button_1": "cycle_scene",
                "button_2": "brighter",
                "button_3": "reset_manual",
                "button_4": "dimmer",
                "button_5": "none",
            },
            debounce_duration=0.5,
        )

        # Mock async_track_state_change_event
        with patch("custom_components.adaptive_lighting_pro.integrations.zen32.async_track_state_change_event") as mock_track:
            mock_track.return_value = Mock()  # Mock listener removal function

            result = await zen32_integration.async_setup()

        assert result is True
        assert len(zen32_integration._listeners) == 5
        assert mock_track.call_count == 5

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_setup_with_missing_entity_fails_gracefully(
        self, zen32_integration, mock_hass
    ):
        """Zen32 setup should fail gracefully when button entity missing.

        REAL SCENARIO: Z-Wave device not paired or entity renamed
        EXPECTED: Setup fails with clear error message
        WHY CRITICAL: Prevents silent failures and confusing behavior
        BUG WOULD CAUSE: Integration appears to work but buttons don't respond
        """
        # Mock some entities missing
        def mock_states_get(entity_id):
            if entity_id == "event.scene_controller_scene_003":
                return None  # Button 3 missing
            return Mock(state="2025-10-01T10:00:00")

        mock_hass.states.get = mock_states_get

        zen32_integration.configure(
            enabled=True,
            button_entities={
                "button_1": "event.scene_controller_scene_001",
                "button_2": "event.scene_controller_scene_002",
                "button_3": "event.scene_controller_scene_003",  # This one missing
            },
            button_actions={
                "button_1": "cycle_scene",
                "button_2": "brighter",
                "button_3": "reset_manual",
            },
        )

        result = await zen32_integration.async_setup()

        assert result is False
        assert len(zen32_integration._listeners) == 0

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_shutdown_removes_all_listeners(
        self, zen32_integration, mock_hass
    ):
        """Zen32 shutdown should remove all event listeners.

        REAL SCENARIO: Integration reload or Home Assistant shutdown
        EXPECTED: All listeners cleanly removed, no orphaned listeners
        WHY CRITICAL: Prevents memory leaks and duplicate event handling
        BUG WOULD CAUSE: Events processed multiple times after reload
        """
        # Setup integration first
        mock_hass.states.get = lambda x: Mock(state="2025-10-01T10:00:00")

        zen32_integration.configure(
            enabled=True,
            button_entities={"button_1": "event.scene_controller_scene_001"},
            button_actions={"button_1": "cycle_scene"},
        )

        # Mock listener removal functions
        mock_remove_1 = Mock()
        mock_remove_2 = Mock()

        with patch("custom_components.adaptive_lighting_pro.integrations.zen32.async_track_state_change_event") as mock_track:
            mock_track.return_value = mock_remove_1
            await zen32_integration.async_setup()

        # Add a second listener manually for testing
        zen32_integration._listeners.append(mock_remove_2)

        # Shutdown
        await zen32_integration.async_shutdown()

        # Verify all listeners called
        mock_remove_1.assert_called_once()
        mock_remove_2.assert_called_once()
        assert len(zen32_integration._listeners) == 0


class TestZen32Debouncing:
    """Test button debouncing logic."""

    @pytest.mark.unit
    @pytest.mark.zen32
    def test_rapid_button_presses_debounced(self, zen32_integration):
        """Rapid button presses should be debounced (ignored if < 0.5s apart).

        REAL SCENARIO: Accidentally double-pressing button
        EXPECTED: Second press ignored, only one action executed
        WHY CRITICAL: Prevents unintended double-brightness adjustments
        BUG WOULD CAUSE: Lights jumping 2 increments on single button press
        """
        zen32_integration.configure(
            enabled=True,
            button_entities={},
            button_actions={},
            debounce_duration=0.1,  # Use shorter duration for faster tests
        )

        # First press - should NOT be debounced
        is_debounced_1 = zen32_integration._is_debounced("button_1")
        assert is_debounced_1 is False

        # Second press immediately after - should be debounced
        is_debounced_2 = zen32_integration._is_debounced("button_1")
        assert is_debounced_2 is True

        # Wait 0.15 seconds (longer than 0.1s debounce)
        time.sleep(0.15)

        # Third press after wait - should NOT be debounced
        is_debounced_3 = zen32_integration._is_debounced("button_1")
        assert is_debounced_3 is False

    @pytest.mark.unit
    @pytest.mark.zen32
    def test_different_buttons_not_debounced_together(self, zen32_integration):
        """Different buttons should have independent debounce tracking.

        REAL SCENARIO: Pressing Button 1, then immediately Button 2
        EXPECTED: Both actions execute (different buttons)
        WHY CRITICAL: User may want to cycle scene then adjust brightness quickly
        BUG WOULD CAUSE: Second button press ignored even though it's different button
        """
        zen32_integration.configure(
            enabled=True,
            button_entities={},
            button_actions={},
            debounce_duration=0.5,
        )

        # Press button 1
        is_debounced_btn1 = zen32_integration._is_debounced("button_1")
        assert is_debounced_btn1 is False

        # Immediately press button 2 - should NOT be debounced
        is_debounced_btn2 = zen32_integration._is_debounced("button_2")
        assert is_debounced_btn2 is False


class TestZen32ButtonActions:
    """Test button action execution."""

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_button_2_brighter_increments_brightness(
        self, zen32_integration, mock_hass, mock_coordinator
    ):
        """Button 2 (brighter) should increment brightness by configured amount.

        REAL SCENARIO: Press brighter button to increase room brightness
        EXPECTED: Current brightness + increment, service called with new value
        WHY CRITICAL: Core functionality for manual brightness control
        BUG WOULD CAUSE: Button doesn't adjust brightness
        """
        mock_coordinator.get_brightness_adjustment.return_value = 20
        mock_coordinator.get_brightness_increment.return_value = 10

        await zen32_integration._action_brighter()

        # Should call service with 20 + 10 = 30
        mock_hass.services.async_call.assert_called_once_with(
            "adaptive_lighting_pro",
            "adjust_brightness",
            {"value": 30},
        )

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_button_4_dimmer_decrements_brightness(
        self, zen32_integration, mock_hass, mock_coordinator
    ):
        """Button 4 (dimmer) should decrement brightness by configured amount.

        REAL SCENARIO: Press dimmer button to decrease room brightness
        EXPECTED: Current brightness - increment, service called with new value
        WHY CRITICAL: Core functionality for manual brightness control
        BUG WOULD CAUSE: Button doesn't adjust brightness
        """
        mock_coordinator.get_brightness_adjustment.return_value = 20
        mock_coordinator.get_brightness_increment.return_value = 10

        await zen32_integration._action_dimmer()

        # Should call service with 20 - 10 = 10
        mock_hass.services.async_call.assert_called_once_with(
            "adaptive_lighting_pro",
            "adjust_brightness",
            {"value": 10},
        )

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_brighter_at_max_clamps_to_100(
        self, zen32_integration, mock_hass, mock_coordinator
    ):
        """Brighter at +95% should clamp to +100% max.

        REAL SCENARIO: Pressing brighter when already near maximum
        EXPECTED: Value clamped to 100, doesn't overflow
        WHY CRITICAL: Prevents invalid brightness values
        BUG WOULD CAUSE: Brightness adjustment above 100%
        """
        mock_coordinator.get_brightness_adjustment.return_value = 95
        mock_coordinator.get_brightness_increment.return_value = 10

        await zen32_integration._action_brighter()

        # Should clamp at 100
        mock_hass.services.async_call.assert_called_once_with(
            "adaptive_lighting_pro",
            "adjust_brightness",
            {"value": 100},
        )

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_dimmer_at_min_clamps_to_minus_100(
        self, zen32_integration, mock_hass, mock_coordinator
    ):
        """Dimmer at -95% should clamp to -100% min.

        REAL SCENARIO: Pressing dimmer when already near minimum
        EXPECTED: Value clamped to -100, doesn't underflow
        WHY CRITICAL: Prevents invalid brightness values
        BUG WOULD CAUSE: Brightness adjustment below -100%
        """
        mock_coordinator.get_brightness_adjustment.return_value = -95
        mock_coordinator.get_brightness_increment.return_value = 10

        await zen32_integration._action_dimmer()

        # Should clamp at -100
        mock_hass.services.async_call.assert_called_once_with(
            "adaptive_lighting_pro",
            "adjust_brightness",
            {"value": -100},
        )

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_button_1_cycle_scene_calls_service(
        self, zen32_integration, mock_hass
    ):
        """Button 1 (cycle scene) should call cycle_scene service.

        REAL SCENARIO: Press scene button to rotate through lighting scenes
        EXPECTED: cycle_scene service called
        WHY CRITICAL: Quick scene switching without UI
        BUG WOULD CAUSE: Scene button doesn't work
        """
        await zen32_integration._action_cycle_scene()

        mock_hass.services.async_call.assert_called_once_with(
            "adaptive_lighting_pro",
            "cycle_scene",
            {},
        )

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_button_3_press_resets_manual_adjustments(
        self, zen32_integration, mock_hass
    ):
        """Button 3 press (not hold) should reset manual adjustments.

        REAL SCENARIO: Press reset button to clear brightness/warmth offsets
        EXPECTED: reset_manual_adjustments service called
        WHY CRITICAL: Quick reset without using UI
        BUG WOULD CAUSE: Can't easily reset adjustments
        """
        await zen32_integration._action_reset_manual_adjustments()

        mock_hass.services.async_call.assert_called_once_with(
            "adaptive_lighting_pro",
            "reset_manual_adjustments",
            {},
        )

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_button_3_hold_nuclear_reset_all(
        self, zen32_integration, mock_hass
    ):
        """Button 3 hold (KeyHeldDown) should trigger nuclear reset.

        REAL SCENARIO: Hold reset button for complete system reset
        EXPECTED: reset_all service called (clears timers, scenes, everything)
        WHY CRITICAL: Emergency reset when things are confused
        BUG WOULD CAUSE: Can't perform full system reset
        """
        await zen32_integration._action_reset_all()

        mock_hass.services.async_call.assert_called_once_with(
            "adaptive_lighting_pro",
            "reset_all",
            {},
        )


class TestZen32EventHandling:
    """Test Z-Wave event entity state change handling."""

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_key_pressed_event_triggers_action(
        self, zen32_integration, mock_hass, mock_coordinator
    ):
        """KeyPressed event should trigger configured button action.

        REAL SCENARIO: Single button press on physical Zen32
        EXPECTED: Action executed (e.g., brighter)
        WHY CRITICAL: Core event-to-action mapping
        BUG WOULD CAUSE: Buttons don't respond to presses
        """
        zen32_integration.configure(
            enabled=True,
            button_entities={"button_2": "event.scene_controller_scene_002"},
            button_actions={"button_2": "brighter"},
        )

        # Mock event data
        event = Mock()
        event.data = {
            "entity_id": "event.scene_controller_scene_002",
            "new_state": Mock(
                attributes={"event_type": "KeyPressed"}
            ),
        }

        mock_coordinator.get_brightness_adjustment.return_value = 0
        mock_coordinator.get_brightness_increment.return_value = 10

        # Manually reset debounce to allow immediate processing
        zen32_integration._last_button_press = {}

        await zen32_integration._button_event_handler(event, "button_2")

        # Should have called brighter action
        mock_hass.services.async_call.assert_called_once_with(
            "adaptive_lighting_pro",
            "adjust_brightness",
            {"value": 10},
        )

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_unknown_event_type_ignored(
        self, zen32_integration, mock_hass
    ):
        """Events with unknown event_type should be ignored.

        REAL SCENARIO: Z-Wave sends KeyReleased or other event types
        EXPECTED: Event ignored, no action taken
        WHY CRITICAL: Only respond to press/hold, not release
        BUG WOULD CAUSE: Actions triggered on button release
        """
        zen32_integration.configure(
            enabled=True,
            button_entities={"button_2": "event.scene_controller_scene_002"},
            button_actions={"button_2": "brighter"},
        )

        event = Mock()
        event.data = {
            "entity_id": "event.scene_controller_scene_002",
            "new_state": Mock(
                attributes={"event_type": "KeyReleased"}  # Unknown type
            ),
        }

        await zen32_integration._button_event_handler(event, "button_2")

        # Should NOT have called any service
        mock_hass.services.async_call.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.zen32
    async def test_event_with_no_new_state_ignored(
        self, zen32_integration, mock_hass
    ):
        """Events with no new_state should be ignored.

        REAL SCENARIO: Malformed event or entity unavailable
        EXPECTED: Event ignored gracefully
        WHY CRITICAL: Robust error handling
        BUG WOULD CAUSE: Exception when processing events
        """
        zen32_integration.configure(
            enabled=True,
            button_entities={"button_2": "event.scene_controller_scene_002"},
            button_actions={"button_2": "brighter"},
        )

        event = Mock()
        event.data = {
            "entity_id": "event.scene_controller_scene_002",
            "new_state": None,  # No state
        }

        await zen32_integration._button_event_handler(event, "button_2")

        # Should NOT have called any service
        mock_hass.services.async_call.assert_not_called()


class TestZen32Status:
    """Test status reporting."""

    @pytest.mark.unit
    @pytest.mark.zen32
    def test_get_status_returns_complete_info(self, zen32_integration):
        """get_status() should return comprehensive integration status.

        REAL SCENARIO: Debugging Zen32 integration in production
        EXPECTED: All configuration and state details available
        WHY CRITICAL: Essential for troubleshooting
        BUG WOULD CAUSE: Can't diagnose Zen32 issues
        """
        zen32_integration.configure(
            enabled=True,
            button_entities={
                "button_1": "event.scene_controller_scene_001",
                "button_2": "event.scene_controller_scene_002",
            },
            button_actions={
                "button_1": "cycle_scene",
                "button_2": "brighter",
            },
            debounce_duration=0.5,
        )

        status = zen32_integration.get_status()

        assert status["enabled"] is True
        assert status["buttons_configured"] == 2
        assert status["debounce_duration"] == 0.5
        assert "button_1" in status["button_entities"]
        assert status["button_actions"]["button_2"] == "brighter"
