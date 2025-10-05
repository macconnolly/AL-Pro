"""Tests for scene/manual layering architecture.

This module verifies that scenes and manual adjustments are SEPARATE LAYERS that ADD together:
- ARCHITECTURAL tests: Enforce coordinator API contract (apply_scene never calls set_brightness_adjustment)
- BEHAVIORAL tests: Verify calculations actually include scene offsets

These tests exist to prevent regression of BUG #1, BUG #2, BUG #3:
- BUG #1: Scenes were calling set_brightness_adjustment, overwriting manual
- BUG #2: Scene offsets stored but never used in calculations
- BUG #3: ALL_LIGHTS called cancel_all_timers affecting ALL rooms
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.adaptive_lighting_pro.const import Scene
from custom_components.adaptive_lighting_pro.coordinator import ALPDataUpdateCoordinator


@pytest.mark.unit
@pytest.mark.coordinator
class TestSceneArchitecture:
    """ARCHITECTURAL tests: Verify apply_scene() follows coordinator API contract."""

    @pytest.mark.asyncio
    async def test_apply_scene_never_calls_set_brightness_adjustment(
        self, mock_hass, mock_config_entry
    ):
        """ARCHITECTURAL TEST: apply_scene must ONLY set scene offset, never call set_brightness_adjustment.

        WHY: BUG #1 was scenes calling set_brightness_adjustment, overwriting manual adjustments.
        This test FAILS if that regression happens.
        """
        coordinator = ALPDataUpdateCoordinator(
            hass=mock_hass, config_entry=mock_config_entry
        )
        await coordinator.async_initialize()

        # Mock the method that should NEVER be called
        coordinator.set_brightness_adjustment = AsyncMock()

        # Mock service calls that apply_scene makes
        with patch.object(coordinator.hass.services, "async_call", new=AsyncMock()):
            # Apply a scene
            await coordinator.apply_scene(Scene.EVENING_COMFORT)

        # ARCHITECTURAL ASSERTION: set_brightness_adjustment was NEVER called
        coordinator.set_brightness_adjustment.assert_not_called()

        # Verify scene offset WAS set (correct behavior)
        assert coordinator._scene_brightness_offset == -5

    @pytest.mark.asyncio
    async def test_apply_scene_never_calls_set_warmth_adjustment(
        self, mock_hass, mock_config_entry
    ):
        """ARCHITECTURAL TEST: apply_scene must ONLY set scene offset, never call set_warmth_adjustment.

        WHY: Same as brightness - scenes are separate layer, must not touch manual.
        """
        coordinator = ALPDataUpdateCoordinator(
            hass=mock_hass, config_entry=mock_config_entry
        )
        await coordinator.async_initialize()

        # Mock the method that should NEVER be called
        coordinator.set_warmth_adjustment = AsyncMock()

        # Mock service calls
        with patch.object(coordinator.hass.services, "async_call", new=AsyncMock()):
            await coordinator.apply_scene(Scene.EVENING_COMFORT)

        # ARCHITECTURAL ASSERTION: set_warmth_adjustment was NEVER called
        coordinator.set_warmth_adjustment.assert_not_called()

        # Verify scene offset WAS set (correct behavior)
        assert coordinator._scene_warmth_offset == -500

    @pytest.mark.asyncio
    async def test_apply_scene_never_calls_cancel_all_timers(
        self, mock_hass, mock_config_entry
    ):
        """ARCHITECTURAL TEST: apply_scene must NEVER call cancel_all_timers.

        WHY: BUG #3 was ALL_LIGHTS calling cancel_all_timers() which affected ALL rooms,
        not just the current room. Scenes should not touch timers at all.
        """
        coordinator = ALPDataUpdateCoordinator(
            hass=mock_hass, config_entry=mock_config_entry
        )
        await coordinator.async_initialize()

        # Mock the method that should NEVER be called
        coordinator.cancel_all_timers = AsyncMock()

        # Mock service calls
        with patch.object(coordinator.hass.services, "async_call", new=AsyncMock()):
            # Apply ALL_LIGHTS scene (this was the buggy one)
            await coordinator.apply_scene(Scene.ALL_LIGHTS)

        # ARCHITECTURAL ASSERTION: cancel_all_timers was NEVER called
        coordinator.cancel_all_timers.assert_not_called()

        # Verify scene offsets cleared (ALL_LIGHTS has 0 offsets)
        assert coordinator._scene_brightness_offset == 0
        assert coordinator._scene_warmth_offset == 0


@pytest.mark.unit
@pytest.mark.coordinator
class TestSceneBehavior:
    """BEHAVIORAL tests: Verify scene offsets actually affect calculations."""

    @pytest.mark.asyncio
    async def test_scene_offset_included_in_brightness_calculation(
        self, mock_hass, mock_config_entry
    ):
        """BEHAVIORAL TEST: Scene offset must be included in brightness calculation.

        WHY: BUG #2 was scene offsets stored but NEVER used in calculation.
        This test verifies coordinator.py:440-442 actually uses scene offset.

        SCENARIO: Apply EVENING_COMFORT (-5% brightness), verify boundaries affected.
        """
        coordinator = ALPDataUpdateCoordinator(
            hass=mock_hass, config_entry=mock_config_entry
        )
        await coordinator.async_initialize()

        # Apply scene using public API
        with patch.object(coordinator.hass.services, "async_call", new=AsyncMock()):
            await coordinator.apply_scene(Scene.EVENING_COMFORT)

        # Verify scene offset set
        assert coordinator._scene_brightness_offset == -5

        # Mock AL switch to be available (prevents zone skip)
        al_switch_state = MagicMock()
        al_switch_state.state = "on"
        al_switch_state.attributes = {
            "manual_control": [],
            "brightness_pct": 100,
            "color_temp_kelvin": 4000,
        }
        coordinator.hass.states.get = MagicMock(return_value=al_switch_state)

        # Capture service calls to verify adjusted boundaries
        service_calls = []
        async def capture_service_call(domain, service, data, **kwargs):
            service_calls.append((domain, service, data))

        # Trigger calculation with all boosts at 0 to isolate scene effect
        with patch.object(coordinator.hass.services, "async_call", side_effect=capture_service_call):
            with patch.object(
                coordinator._env_adapter, "calculate_boost", return_value=0
            ):
                with patch.object(
                    coordinator._sunset_boost, "calculate_boost", return_value=(0, 0)
                ):
                    with patch.object(
                        coordinator._wake_sequence, "calculate_boost", return_value=0
                    ):
                        await coordinator._async_update_data()

        # BEHAVIORAL ASSERTION: Scene offset affected brightness boundaries
        # With -5% scene offset and 0 other boosts, max should be lowered by 5
        # Find the service call for main_living zone
        main_living_calls = [
            call for call in service_calls
            if call[2].get("entity_id") == "switch.adaptive_lighting_main_living"
        ]
        assert len(main_living_calls) > 0, "Main living zone should have received service call"

        call_data = main_living_calls[0][2]
        # Original max is 100, with -5 scene offset, max should be 95
        assert (
            call_data["max_brightness"] == 95
        ), f"Scene offset -5 should lower max from 100 to 95, got {call_data['max_brightness']}"

    @pytest.mark.asyncio
    async def test_manual_and_scene_both_affect_brightness_boundaries(
        self, mock_hass, mock_config_entry
    ):
        """BEHAVIORAL TEST: Manual and scene layers must BOTH affect calculation.

        WHY: Verifies the core fix - both layers ADD together in calculation.

        SCENARIO: Manual +10%, Scene -5%, verify result is +5% total effect.
        """
        coordinator = ALPDataUpdateCoordinator(
            hass=mock_hass, config_entry=mock_config_entry
        )
        await coordinator.async_initialize()

        # Set manual adjustment (direct for test setup - coordinator's own test)
        coordinator._brightness_adjustment = 10

        # Apply scene using public API
        with patch.object(coordinator.hass.services, "async_call", new=AsyncMock()):
            await coordinator.apply_scene(Scene.EVENING_COMFORT)  # -5 offset

        # Mock AL switch to be available
        al_switch_state = MagicMock()
        al_switch_state.state = "on"
        al_switch_state.attributes = {"manual_control": [], "brightness_pct": 100, "color_temp_kelvin": 4000}
        coordinator.hass.states.get = MagicMock(return_value=al_switch_state)

        # Capture service calls
        service_calls = []
        async def capture_service_call(domain, service, data, **kwargs):
            service_calls.append((domain, service, data))

        # Trigger calculation
        with patch.object(coordinator.hass.services, "async_call", side_effect=capture_service_call):
            with patch.object(
                coordinator._env_adapter, "calculate_boost", return_value=0
            ):
                with patch.object(
                    coordinator._sunset_boost, "calculate_boost", return_value=(0, 0)
                ):
                    with patch.object(
                        coordinator._wake_sequence, "calculate_boost", return_value=0
                    ):
                        await coordinator._async_update_data()

        # BEHAVIORAL ASSERTION: Both layers combined
        # Manual +10 + Scene -5 = +5 total
        # This raises min by 5 (positive adjustment)
        main_living_calls = [
            call for call in service_calls
            if call[2].get("entity_id") == "switch.adaptive_lighting_main_living"
        ]
        assert len(main_living_calls) > 0, "Main living zone should have received service call"

        call_data = main_living_calls[0][2]
        # Original min is 45, with +5 total boost, min should be 50
        assert (
            call_data["min_brightness"] == 50
        ), f"Manual +10 + Scene -5 should raise min from 45 to 50, got {call_data['min_brightness']}"

    @pytest.mark.asyncio
    async def test_warmth_calculation_includes_scene_offset(
        self, mock_hass, mock_config_entry
    ):
        """BEHAVIORAL TEST: Scene offset must affect warmth calculation.

        WHY: BUG #2 also affected warmth - scene offset was stored but not used.

        SCENARIO: Apply EVENING_COMFORT (-500K warmth), verify warmth affected.
        """
        coordinator = ALPDataUpdateCoordinator(
            hass=mock_hass, config_entry=mock_config_entry
        )
        await coordinator.async_initialize()

        # Apply scene
        with patch.object(coordinator.hass.services, "async_call", new=AsyncMock()):
            await coordinator.apply_scene(Scene.EVENING_COMFORT)  # -500K

        # Verify scene offset set
        assert coordinator._scene_warmth_offset == -500

        # Mock AL switch to be available
        al_switch_state = MagicMock()
        al_switch_state.state = "on"
        al_switch_state.attributes = {"manual_control": [], "brightness_pct": 100, "color_temp_kelvin": 4000}
        coordinator.hass.states.get = MagicMock(return_value=al_switch_state)

        # Capture service calls
        service_calls = []
        async def capture_service_call(domain, service, data, **kwargs):
            service_calls.append((domain, service, data))

        # Trigger calculation
        with patch.object(coordinator.hass.services, "async_call", side_effect=capture_service_call):
            with patch.object(
                coordinator._env_adapter, "calculate_boost", return_value=0
            ):
                with patch.object(
                    coordinator._sunset_boost, "calculate_boost", return_value=(0, 0)
                ):
                    with patch.object(
                        coordinator._wake_sequence, "calculate_boost", return_value=0
                    ):
                        await coordinator._async_update_data()

        # BEHAVIORAL ASSERTION: Scene warmth offset affected color temp
        # With -500K offset, max should be lowered by 500
        main_living_calls = [
            call for call in service_calls
            if call[2].get("entity_id") == "switch.adaptive_lighting_main_living"
        ]
        assert len(main_living_calls) > 0, "Main living zone should have received service call"

        call_data = main_living_calls[0][2]
        # Original max is 5500, with -500 offset, max should be 5000
        assert (
            call_data["max_color_temp"] == 5000
        ), f"Scene offset -500K should lower max from 5500 to 5000, got {call_data['max_color_temp']}"

    @pytest.mark.asyncio
    async def test_all_lights_clears_scene_preserves_manual(
        self, mock_hass, mock_config_entry
    ):
        """BEHAVIORAL TEST: ALL_LIGHTS must clear scene offset but preserve manual.

        WHY: ALL_LIGHTS is just a scene with 0 offsets - it clears scenes, not manual.

        SCENARIO: Manual +20%, Scene -50%, apply ALL_LIGHTS, verify only scene cleared.
        """
        coordinator = ALPDataUpdateCoordinator(
            hass=mock_hass, config_entry=mock_config_entry
        )
        await coordinator.async_initialize()

        # Set manual adjustment
        coordinator._brightness_adjustment = 20

        # Apply a scene
        with patch.object(coordinator.hass.services, "async_call", new=AsyncMock()):
            await coordinator.apply_scene(Scene.ULTRA_DIM)  # -50 offset

        # Verify both layers active
        assert coordinator._brightness_adjustment == 20
        assert coordinator._scene_brightness_offset == -50

        # Now apply ALL_LIGHTS
        with patch.object(coordinator.hass.services, "async_call", new=AsyncMock()):
            await coordinator.apply_scene(Scene.ALL_LIGHTS)  # 0 offset

        # BEHAVIORAL ASSERTION: Manual preserved, scene cleared
        assert coordinator._brightness_adjustment == 20, "Manual should be preserved"
        assert coordinator._scene_brightness_offset == 0, "Scene should be cleared"
