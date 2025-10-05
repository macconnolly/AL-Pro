"""Tests for button platform - quick action buttons.

Following claude.md standards: "This is YOUR home. You live here."

Test Philosophy:
- Test real scenarios, not edge cases
- Every test represents something you'll actually do
- Button presses should be instant, predictable, idempotent

Real Scenarios:
- Video call starting → Tap "Brighter" 3x → Perfect lighting in 5 seconds
- Evening wind-down → Tap "Evening Comfort" → Instant relaxation
- Kids broke lights → Tap "Reset" → Back to normal, crisis averted
- Automation spam → Pressing "Brighter" at max is safe, no errors
"""
from datetime import datetime, UTC
from unittest.mock import MagicMock, AsyncMock, call

import pytest

from custom_components.adaptive_lighting_pro.platforms.button import (
    ALPBrighterButton,
    ALPDimmerButton,
    ALPWarmerButton,
    ALPCoolerButton,
    ALPResetButton,
    ALPSceneButton,
)
from custom_components.adaptive_lighting_pro.const import Scene, DOMAIN


@pytest.mark.unit
@pytest.mark.button
class TestAdjustmentButtons:
    """Test brightness and warmth adjustment buttons."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator with adjustment getters/setters."""
        coordinator = MagicMock()
        coordinator.get_brightness_adjustment = MagicMock(return_value=0)
        coordinator.set_brightness_adjustment = AsyncMock()
        coordinator.get_warmth_adjustment = MagicMock(return_value=0)
        coordinator.set_warmth_adjustment = AsyncMock()
        coordinator.get_brightness_increment = MagicMock(return_value=10)
        coordinator.get_color_temp_increment = MagicMock(return_value=500)
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.mark.asyncio
    async def test_video_call_brightness_boost(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Video call in 30 seconds, need more light NOW

        EXPECTED: 3 quick taps = +30% brightness in 5 seconds
        WHY: Faster than slider, critical for work-from-home
        """
        button = ALPBrighterButton(mock_coordinator, mock_config_entry)

        # Simulate 3 quick taps with state updates
        await button.async_press()  # 0 → +10%
        mock_coordinator.get_brightness_adjustment.return_value = 10

        await button.async_press()  # +10% → +20%
        mock_coordinator.get_brightness_adjustment.return_value = 20

        await button.async_press()  # +20% → +30%

        # Verify called with increasing values AND start_timers=True (temp override)
        assert mock_coordinator.set_brightness_adjustment.call_count == 3
        calls = mock_coordinator.set_brightness_adjustment.call_args_list
        assert calls[0] == call(10, start_timers=True)
        assert calls[1] == call(20, start_timers=True)
        assert calls[2] == call(30, start_timers=True)

    @pytest.mark.asyncio
    async def test_brighter_at_max_is_safe(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Automation spams 'brighter' button

        EXPECTED: No errors, gracefully caps at +50%
        WHY: Physical buttons + automations will spam these, must be idempotent
        """
        mock_coordinator.get_brightness_adjustment.return_value = 50  # Already at max
        button = ALPBrighterButton(mock_coordinator, mock_config_entry)

        # Press button at max → should stay at 50
        await button.async_press()

        mock_coordinator.set_brightness_adjustment.assert_called_once_with(50, start_timers=True)
        # No error thrown, idempotent behavior

    @pytest.mark.asyncio
    async def test_dimmer_for_tv_watching(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Lights too bright for TV, hands full of popcorn

        EXPECTED: Quick taps dim lights without navigating sliders
        WHY: Convenience over precision when relaxing
        """
        mock_coordinator.get_brightness_adjustment.return_value = 20  # Start at +20%
        button = ALPDimmerButton(mock_coordinator, mock_config_entry)

        # Tap twice to get to comfortable level
        await button.async_press()  # +20% → +10%
        mock_coordinator.get_brightness_adjustment.return_value = 10
        await button.async_press()  # +10% → 0%

        calls = mock_coordinator.set_brightness_adjustment.call_args_list
        assert calls[0] == call(10, start_timers=True)
        assert calls[1] == call(0, start_timers=True)

    @pytest.mark.asyncio
    async def test_dimmer_at_min_is_safe(self, mock_coordinator, mock_config_entry):
        """SCENARIO: User keeps pressing dimmer at minimum

        EXPECTED: Caps at -50%, no errors
        WHY: Idempotent at boundaries
        """
        mock_coordinator.get_brightness_adjustment.return_value = -50  # Already at min
        button = ALPDimmerButton(mock_coordinator, mock_config_entry)

        await button.async_press()

        mock_coordinator.set_brightness_adjustment.assert_called_once_with(-50, start_timers=True)

    @pytest.mark.asyncio
    async def test_evening_warmth_adjustment(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Evening wind-down, lights feel too blue/cool

        EXPECTED: Press 'Warmer' 2x → -1000K, cozy warmth
        WHY: Natural warmth promotes relaxation
        """
        button = ALPWarmerButton(mock_coordinator, mock_config_entry)

        # Press warmer twice
        await button.async_press()  # 0 → -500K
        mock_coordinator.get_warmth_adjustment.return_value = -500
        await button.async_press()  # -500K → -1000K

        calls = mock_coordinator.set_warmth_adjustment.call_args_list
        assert calls[0] == call(-500, start_timers=True)
        assert calls[1] == call(-1000, start_timers=True)

    @pytest.mark.asyncio
    async def test_warmer_at_max_is_safe(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Already at warmest, keep pressing

        EXPECTED: Caps at -3000K, idempotent
        WHY: Physical buttons need safe boundaries
        """
        mock_coordinator.get_warmth_adjustment.return_value = -3000
        button = ALPWarmerButton(mock_coordinator, mock_config_entry)

        await button.async_press()

        mock_coordinator.set_warmth_adjustment.assert_called_once_with(-3000, start_timers=True)

    @pytest.mark.asyncio
    async def test_morning_alertness_cool_white(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Morning alertness, need crisp white light

        EXPECTED: Press 'Cooler' → +500K, energizing
        WHY: Cool light promotes focus
        """
        button = ALPCoolerButton(mock_coordinator, mock_config_entry)

        await button.async_press()

        mock_coordinator.set_warmth_adjustment.assert_called_once_with(500, start_timers=True)

    @pytest.mark.asyncio
    async def test_cooler_at_max_is_safe(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Already at coolest, automation keeps triggering

        EXPECTED: Caps at +3000K, no errors
        WHY: Automation-safe idempotency
        """
        mock_coordinator.get_warmth_adjustment.return_value = 3000
        button = ALPCoolerButton(mock_coordinator, mock_config_entry)

        await button.async_press()

        mock_coordinator.set_warmth_adjustment.assert_called_once_with(3000, start_timers=True)

    @pytest.mark.asyncio
    async def test_refresh_triggered_after_adjustment(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Button pressed, changes need to apply immediately

        EXPECTED: Coordinator setter handles refresh internally
        WHY: Architectural improvement - coordinator owns refresh logic

        NOTE: Button calls coordinator.set_brightness_adjustment(), which
        internally calls async_request_refresh(). We test the public API
        contract (button calls setter), not internal implementation details.
        """
        button = ALPBrighterButton(mock_coordinator, mock_config_entry)

        await button.async_press()

        # Verify button called the setter (which handles refresh internally)
        mock_coordinator.set_brightness_adjustment.assert_called_once_with(10, start_timers=True)


@pytest.mark.unit
@pytest.mark.button
class TestResetButton:
    """Test the reset button - the 'I broke it, fix it' button."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator."""
        coordinator = MagicMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass with services."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        return hass

    @pytest.mark.asyncio
    async def test_kid_broke_the_lights_recovery(self, mock_coordinator, mock_config_entry, mock_hass):
        """SCENARIO: 5-year-old mashed all the buttons, lights are chaos

        EXPECTED: Press 'Reset' → back to adaptive baseline, crisis averted
        WHY: Non-technical users (and panicked parents) need a "fix it" button

        This button saves marriages.
        """
        button = ALPResetButton(mock_coordinator, mock_config_entry, mock_hass)

        await button.async_press()

        # Verify service called (logic lives in services.py, not duplicated here)
        mock_hass.services.async_call.assert_called_once_with(
            DOMAIN,
            "reset_manual_adjustments",
            blocking=True,
        )

    @pytest.mark.asyncio
    async def test_reset_uses_existing_service(self, mock_coordinator, mock_config_entry, mock_hass):
        """SCENARIO: Reset button pressed

        EXPECTED: Calls existing service, doesn't duplicate logic
        WHY: DRY principle - service already handles:
             - Setting brightness to 0
             - Setting warmth to 0
             - Logging
             - Error handling
        """
        button = ALPResetButton(mock_coordinator, mock_config_entry, mock_hass)

        await button.async_press()

        # Button is just a UI trigger for the service
        assert mock_hass.services.async_call.called
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][0] == DOMAIN  # Domain
        assert call_args[0][1] == "reset_manual_adjustments"  # Service
        assert call_args[1]["blocking"] == True  # Wait for completion


@pytest.mark.unit
@pytest.mark.button
class TestSceneButtons:
    """Test scene trigger buttons."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator with scene support."""
        coordinator = MagicMock()
        coordinator.apply_scene = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.mark.asyncio
    async def test_evening_wind_down_one_button(self, mock_coordinator, mock_config_entry):
        """SCENARIO: End of workday, exhausted, want relaxation

        EXPECTED: Press 'Evening Comfort' → instant cozy lighting
        WHY: claude.md says "Relaxation is one button press"

        This is THE MOST IMPORTANT scene button.
        """
        button = ALPSceneButton(
            mock_coordinator,
            mock_config_entry,
            Scene.EVENING_COMFORT,
            "Evening Comfort",
            "mdi:weather-sunset-down"
        )

        await button.async_press()

        # Verify scene applied
        mock_coordinator.apply_scene.assert_called_once_with(Scene.EVENING_COMFORT)

    @pytest.mark.asyncio
    async def test_movie_mode_ultra_dim(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Netflix starting, need minimal light

        EXPECTED: Press 'Ultra Dim' → perfect movie lighting
        WHY: One button for the whole experience
        """
        button = ALPSceneButton(
            mock_coordinator,
            mock_config_entry,
            Scene.ULTRA_DIM,
            "Ultra Dim",
            "mdi:movie-open"
        )

        await button.async_press()

        mock_coordinator.apply_scene.assert_called_once_with(Scene.ULTRA_DIM)

    @pytest.mark.asyncio
    async def test_all_lights_scene(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Need to see everything (cleaning, searching for keys)

        EXPECTED: Press 'All Lights' → every zone active
        WHY: Maximum visibility when needed
        """
        button = ALPSceneButton(
            mock_coordinator,
            mock_config_entry,
            Scene.ALL_LIGHTS,
            "All Lights",
            "mdi:lightbulb-group"
        )

        await button.async_press()

        mock_coordinator.apply_scene.assert_called_once_with(Scene.ALL_LIGHTS)

    @pytest.mark.asyncio
    async def test_reading_mode_no_spotlights(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Reading in bed, spotlights too distracting

        EXPECTED: Press 'No Spotlights' → ambient light only
        WHY: Focus mode for reading
        """
        button = ALPSceneButton(
            mock_coordinator,
            mock_config_entry,
            Scene.NO_SPOTLIGHTS,
            "No Spotlights",
            "mdi:book-open-variant"
        )

        await button.async_press()

        mock_coordinator.apply_scene.assert_called_once_with(Scene.NO_SPOTLIGHTS)


@pytest.mark.unit
@pytest.mark.button
class TestButtonInitialization:
    """Test button entity initialization and attributes."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator."""
        return MagicMock()

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    def test_brighter_button_initialization(self, mock_coordinator, mock_config_entry):
        """Test brighter button initializes with correct attributes."""
        button = ALPBrighterButton(mock_coordinator, mock_config_entry)

        assert button.unique_id == "adaptive_lighting_pro_test_entry_button_brighter"
        assert button.name == "Brighter"
        assert button.icon == "mdi:brightness-plus"

    def test_dimmer_button_initialization(self, mock_coordinator, mock_config_entry):
        """Test dimmer button initializes with correct attributes."""
        button = ALPDimmerButton(mock_coordinator, mock_config_entry)

        assert button.unique_id == "adaptive_lighting_pro_test_entry_button_dimmer"
        assert button.name == "Dimmer"
        assert button.icon == "mdi:brightness-minus"

    def test_warmer_button_initialization(self, mock_coordinator, mock_config_entry):
        """Test warmer button initializes with correct attributes."""
        button = ALPWarmerButton(mock_coordinator, mock_config_entry)

        assert button.unique_id == "adaptive_lighting_pro_test_entry_button_warmer"
        assert button.name == "Warmer"
        assert button.icon == "mdi:thermometer-minus"

    def test_cooler_button_initialization(self, mock_coordinator, mock_config_entry):
        """Test cooler button initializes with correct attributes."""
        button = ALPCoolerButton(mock_coordinator, mock_config_entry)

        assert button.unique_id == "adaptive_lighting_pro_test_entry_button_cooler"
        assert button.name == "Cooler"
        assert button.icon == "mdi:thermometer-plus"

    def test_reset_button_initialization(self, mock_coordinator, mock_config_entry):
        """Test reset button initializes with correct attributes."""
        hass = MagicMock()
        button = ALPResetButton(mock_coordinator, mock_config_entry, hass)

        assert button.unique_id == "adaptive_lighting_pro_test_entry_button_reset"
        assert button.name == "Reset"
        assert button.icon == "mdi:refresh"

    def test_scene_button_initialization(self, mock_coordinator, mock_config_entry):
        """Test scene button initializes with correct attributes."""
        button = ALPSceneButton(
            mock_coordinator,
            mock_config_entry,
            Scene.EVENING_COMFORT,
            "Evening Comfort",
            "mdi:weather-sunset-down"
        )

        assert button.unique_id == "adaptive_lighting_pro_test_entry_button_scene_evening_comfort"
        assert button.name == "Scene: Evening Comfort"
        assert button.icon == "mdi:weather-sunset-down"
