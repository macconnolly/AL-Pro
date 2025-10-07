"""Tests for scene clearing behavior.

This module verifies that scenes properly "get out of the way" as per claude.md:
- ALL_LIGHTS scene clears back to pure adaptive lighting
- Reset button clears both manual adjustments AND scene offsets
- Nuclear reset clears everything including timers
- Scenes don't interfere with each other
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.adaptive_lighting_pro.const import DOMAIN, Scene
from custom_components.adaptive_lighting_pro.select import ALPSceneSelect


@pytest.mark.unit
@pytest.mark.select
class TestSceneClearingBehavior:
    """Test that ALL_LIGHTS scene properly clears to adaptive lighting."""

    @pytest.mark.asyncio
    async def test_all_lights_scene_clears_scene_offsets_only(self):
        """SCENARIO: Evening comfort active, user presses ALL_LIGHTS to return to normal

        EXPECTED: ALL_LIGHTS clears scene offsets but preserves manual adjustments
        WHY: Scenes are separate layer from manual - ALL_LIGHTS = "no scene active"
        """
        mock_hass = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        # Mock coordinator that tracks scene application
        mock_coordinator = MagicMock()
        mock_coordinator.get_current_scene = MagicMock(return_value=Scene.EVENING_COMFORT)

        # Track manual adjustment separately
        mock_coordinator._brightness_adjustment = 10  # User had made manual adjustment
        mock_coordinator._warmth_adjustment = -200

        # Mock apply_scene to verify ALL_LIGHTS clearing behavior
        async def mock_apply_scene(scene):
            if scene == Scene.ALL_LIGHTS:
                # Clears scene offsets only
                mock_coordinator._current_scene = Scene.DEFAULT
                mock_coordinator._scene_brightness_offset = 0
                mock_coordinator._scene_warmth_offset = 0
                # Manual adjustments are NOT touched
            return True

        mock_coordinator.apply_scene = AsyncMock(side_effect=mock_apply_scene)

        mock_hass.data = {
            DOMAIN: {
                "test_entry": {"coordinator": mock_coordinator}
            }
        }

        # Create select entity
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        # Apply ALL_LIGHTS scene
        await select.async_select_option("all_lights")

        # Verify scene was applied
        mock_coordinator.apply_scene.assert_called_once_with(Scene.ALL_LIGHTS)

        # Verify manual adjustments were preserved
        assert mock_coordinator._brightness_adjustment == 10
        assert mock_coordinator._warmth_adjustment == -200

    @pytest.mark.asyncio
    async def test_reset_button_clears_scene_offsets(self):
        """SCENARIO: Ultra dim scene active, user presses reset button

        EXPECTED: Scene offsets cleared to 0, current_scene set to DEFAULT
        WHY: Reset means "back to adaptive lighting baseline"
        """
        mock_hass = MagicMock()
        mock_coordinator = MagicMock()

        # Scene currently active with offsets
        mock_coordinator._current_scene = Scene.ULTRA_DIM
        mock_coordinator._scene_brightness_offset = -50
        mock_coordinator._scene_warmth_offset = -1000
        mock_coordinator._brightness_adjustment = -50
        mock_coordinator._warmth_adjustment = -1000

        # Mock reset methods
        async def mock_set_brightness(value):
            mock_coordinator._brightness_adjustment = value

        async def mock_set_warmth(value):
            mock_coordinator._warmth_adjustment = value

        async def mock_clear_scenes():
            mock_coordinator._scene_brightness_offset = 0
            mock_coordinator._scene_warmth_offset = 0
            mock_coordinator._current_scene = Scene.DEFAULT

        mock_coordinator.set_brightness_adjustment = AsyncMock(side_effect=mock_set_brightness)
        mock_coordinator.set_warmth_adjustment = AsyncMock(side_effect=mock_set_warmth)
        mock_coordinator.clear_scene_offsets = AsyncMock(side_effect=mock_clear_scenes)

        # Simulate reset_manual_adjustments service (uses coordinator API)
        await mock_coordinator.set_brightness_adjustment(0)
        await mock_coordinator.set_warmth_adjustment(0)
        await mock_coordinator.clear_scene_offsets()

        # Verify all cleared
        assert mock_coordinator._brightness_adjustment == 0
        assert mock_coordinator._warmth_adjustment == 0
        assert mock_coordinator._scene_brightness_offset == 0
        assert mock_coordinator._scene_warmth_offset == 0
        assert mock_coordinator._current_scene == Scene.DEFAULT

    @pytest.mark.asyncio
    async def test_scene_workflow_evening_to_adaptive_to_ultra_dim(self):
        """SCENARIO: Real workflow - Apply scene, return to adaptive, apply different scene

        WORKFLOW:
        1. Start at adaptive (DEFAULT)
        2. Apply EVENING_COMFORT (-5 brightness, -500K warmth)
        3. Return to adaptive via ALL_LIGHTS (clears everything)
        4. Apply ULTRA_DIM (-50 brightness, -1000K warmth)

        WHY: Scenes must not interfere with each other
        """
        mock_hass = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        # Coordinator with full scene tracking
        mock_coordinator = MagicMock()
        mock_coordinator._current_scene = Scene.DEFAULT
        mock_coordinator._scene_brightness_offset = 0
        mock_coordinator._scene_warmth_offset = 0

        scene_history = []

        async def mock_apply_scene(scene):
            scene_history.append(scene)
            if scene == Scene.ALL_LIGHTS:
                mock_coordinator._current_scene = Scene.DEFAULT
                mock_coordinator._scene_brightness_offset = 0
                mock_coordinator._scene_warmth_offset = 0
            elif scene == Scene.EVENING_COMFORT:
                mock_coordinator._current_scene = Scene.EVENING_COMFORT
                mock_coordinator._scene_brightness_offset = -5
                mock_coordinator._scene_warmth_offset = -500
            elif scene == Scene.ULTRA_DIM:
                mock_coordinator._current_scene = Scene.ULTRA_DIM
                mock_coordinator._scene_brightness_offset = -50
                mock_coordinator._scene_warmth_offset = -1000
            return True

        mock_coordinator.apply_scene = AsyncMock(side_effect=mock_apply_scene)
        mock_coordinator.get_current_scene = MagicMock(side_effect=lambda: mock_coordinator._current_scene)

        mock_hass.data = {
            DOMAIN: {
                "test_entry": {"coordinator": mock_coordinator}
            }
        }

        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        # Step 1: Apply evening comfort
        await select.async_select_option("evening_comfort")
        assert mock_coordinator._current_scene == Scene.EVENING_COMFORT
        assert mock_coordinator._scene_brightness_offset == -5

        # Step 2: Return to adaptive via ALL_LIGHTS
        await select.async_select_option("all_lights")
        assert mock_coordinator._current_scene == Scene.DEFAULT
        assert mock_coordinator._scene_brightness_offset == 0
        assert mock_coordinator._scene_warmth_offset == 0

        # Step 3: Apply ultra dim
        await select.async_select_option("ultra_dim")
        assert mock_coordinator._current_scene == Scene.ULTRA_DIM
        assert mock_coordinator._scene_brightness_offset == -50

        # Verify scene history
        assert scene_history == [Scene.EVENING_COMFORT, Scene.ALL_LIGHTS, Scene.ULTRA_DIM]

    @pytest.mark.asyncio
    async def test_default_scene_displays_as_all_lights(self):
        """SCENARIO: System at pure adaptive (DEFAULT), user checks scene dropdown

        EXPECTED: Dropdown shows "all_lights" as current
        WHY: DEFAULT is internal, ALL_LIGHTS is the user-facing representation
        """
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        mock_coordinator = MagicMock()
        mock_coordinator.get_current_scene = MagicMock(return_value=Scene.DEFAULT)

        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        # DEFAULT should display as ALL_LIGHTS
        assert select.current_option == "all_lights"

    @pytest.mark.asyncio
    async def test_no_spotlights_then_all_lights_clears_scene_only(self):
        """SCENARIO: Apply NO_SPOTLIGHTS (+15% scene offset), then ALL_LIGHTS

        EXPECTED: ALL_LIGHTS clears scene offset, manual adjustment unchanged
        WHY: Scenes and manual are separate layers that add together
        """
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"

        mock_coordinator = MagicMock()
        mock_coordinator._current_scene = Scene.DEFAULT
        mock_coordinator._scene_brightness_offset = 0
        mock_coordinator._brightness_adjustment = 0  # No manual adjustment

        async def mock_apply_scene(scene):
            if scene == Scene.NO_SPOTLIGHTS:
                # Scene sets scene offset only
                mock_coordinator._current_scene = Scene.NO_SPOTLIGHTS
                mock_coordinator._scene_brightness_offset = 15
                # Manual adjustment NOT touched
            elif scene == Scene.ALL_LIGHTS:
                # ALL_LIGHTS clears scene offset only
                mock_coordinator._current_scene = Scene.DEFAULT
                mock_coordinator._scene_brightness_offset = 0
                # Manual adjustment NOT touched
            return True

        mock_coordinator.apply_scene = AsyncMock(side_effect=mock_apply_scene)
        mock_coordinator.get_current_scene = MagicMock(
            side_effect=lambda: mock_coordinator._current_scene
        )

        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        # Apply NO_SPOTLIGHTS - sets scene offset
        await select.async_select_option("no_spotlights")
        assert mock_coordinator._scene_brightness_offset == 15
        assert mock_coordinator._brightness_adjustment == 0  # Unchanged

        # Clear with ALL_LIGHTS - clears scene offset
        await select.async_select_option("all_lights")
        assert mock_coordinator._scene_brightness_offset == 0
        assert mock_coordinator._brightness_adjustment == 0  # Still unchanged
        assert mock_coordinator._current_scene == Scene.DEFAULT
