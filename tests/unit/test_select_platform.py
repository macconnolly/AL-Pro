"""Tests for select platform - scene selector dropdown.

Following claude.md standards: "This is YOUR home. You live here."

Test Philosophy:
- Test real scenarios, not edge cases
- Every test represents something you'll actually do
- Scene selection should be instant, predictable, one-click comfort

Real Scenarios:
- Evening wind-down → Select "Evening Comfort" from dropdown → Instant cozy lighting
- Movie night → Select "Ultra Dim" → Perfect ambient glow without menus
- Reading session → Select "No Spotlights" → Focus lighting without distraction
- DEFAULT scene → Shows "All Lights" in UI (user-friendly, no internal states)
"""
from unittest.mock import MagicMock, AsyncMock

import pytest

from custom_components.adaptive_lighting_pro.select import (
    ALPSceneSelect,
    async_setup_entry,
)
from custom_components.adaptive_lighting_pro.const import Scene, DOMAIN


@pytest.mark.unit
@pytest.mark.select
class TestSceneSelect:
    """Test the scene selector dropdown."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator with scene support."""
        coordinator = MagicMock()
        coordinator.get_current_scene = MagicMock(return_value=Scene.DEFAULT)
        coordinator.apply_scene = AsyncMock(return_value=True)
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    def test_dropdown_shows_four_practical_scenes(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Open scene selector dropdown in UI

        EXPECTED: See 4 practical scenes, no confusing "default" option
        WHY: claude.md says scenes are "dead simple, not confusing"
             DEFAULT is internal state, users don't need to see it
        """
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        # Verify options exclude DEFAULT
        assert len(select.options) == 4
        assert "all_lights" in select.options
        assert "no_spotlights" in select.options
        assert "evening_comfort" in select.options
        assert "ultra_dim" in select.options
        assert "default" not in select.options  # Internal state hidden from users

    def test_evening_relaxation_one_dropdown_selection(self, mock_coordinator, mock_config_entry):
        """SCENARIO: End of workday, exhausted, want instant comfort

        EXPECTED: Select "Evening Comfort" → -30% brightness, -500K warmth, cozy glow
        WHY: claude.md says "Relaxation is one button press"
             (or one dropdown selection in this case)

        This is THE MOST IMPORTANT scene.
        """
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        # User selects "evening_comfort" from dropdown
        await_result = select.async_select_option("evening_comfort")
        # Run the async function
        import asyncio
        asyncio.run(await_result) if asyncio.iscoroutine(await_result) else None

        # Verify coordinator called with correct scene
        mock_coordinator.apply_scene.assert_called_once_with(Scene.EVENING_COMFORT)

    @pytest.mark.asyncio
    async def test_movie_night_ultra_dim(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Netflix starting, lights too bright, remote is buried in couch

        EXPECTED: Quick dropdown select "Ultra Dim" → minimal ambient light
        WHY: Faster than slider, no fumbling with phone keyboard
        """
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        await select.async_select_option("ultra_dim")

        mock_coordinator.apply_scene.assert_called_once_with(Scene.ULTRA_DIM)

    @pytest.mark.asyncio
    async def test_reading_mode_no_distractions(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Reading in bed, spotlights creating glare

        EXPECTED: Select "No Spotlights" → ambient zones only, perfect focus
        WHY: Dedicated reading mode without manual zone fiddling
        """
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        await select.async_select_option("no_spotlights")

        mock_coordinator.apply_scene.assert_called_once_with(Scene.NO_SPOTLIGHTS)

    @pytest.mark.asyncio
    async def test_all_lights_for_cleaning_day(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Saturday morning cleaning, need every light on

        EXPECTED: Select "All Lights" → maximum visibility
        WHY: Quick way to restore everything to normal
        """
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        await select.async_select_option("all_lights")

        mock_coordinator.apply_scene.assert_called_once_with(Scene.ALL_LIGHTS)

    @pytest.mark.asyncio
    async def test_current_scene_tracking(self, mock_coordinator, mock_config_entry):
        """SCENARIO: User opens dropdown to see what scene is active

        EXPECTED: Current scene shown as selected
        WHY: Users need to know current state before changing
        """
        # Set current scene to evening comfort
        mock_coordinator.get_current_scene.return_value = Scene.EVENING_COMFORT
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        current = select.current_option

        assert current == "evening_comfort"
        mock_coordinator.get_current_scene.assert_called_once()

    def test_default_scene_shows_all_lights_in_ui(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Integration just started, scene is DEFAULT (internal state)

        EXPECTED: Dropdown shows "All Lights" instead of confusing "default"
        WHY: DEFAULT is internal initialization state, users don't need to see it
             All Lights is the practical equivalent
        """
        mock_coordinator.get_current_scene.return_value = Scene.DEFAULT
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        current = select.current_option

        # DEFAULT mapped to ALL_LIGHTS for user display
        assert current == "all_lights"

    @pytest.mark.asyncio
    async def test_invalid_scene_handled_gracefully(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Automation passes invalid scene value (typo, old config)

        EXPECTED: Error logged, no crash, coordinator not called
        WHY: Robustness against config mistakes
        """
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        # This should not crash
        await select.async_select_option("invalid_scene_name")

        # Coordinator should NOT be called with bad data
        mock_coordinator.apply_scene.assert_not_called()

    @pytest.mark.asyncio
    async def test_scene_selection_triggers_state_update(self, mock_coordinator, mock_config_entry):
        """SCENARIO: User selects scene, UI needs to reflect new state

        EXPECTED: Entity state written to HA after scene applied (when hass is available)
        WHY: Immediate UI feedback without waiting for next coordinator poll
        """
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)
        select.hass = MagicMock()  # Mock hass so state update is called
        select.async_write_ha_state = MagicMock()

        await select.async_select_option("evening_comfort")

        # Verify state update triggered
        select.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_scene_application_handled(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Coordinator fails to apply scene (zone offline, etc)

        EXPECTED: Error logged, no crash
        WHY: Graceful degradation when things go wrong
        """
        mock_coordinator.apply_scene.return_value = False  # Simulate failure
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        # Should not crash
        await select.async_select_option("evening_comfort")

        # Coordinator was called (it just failed)
        mock_coordinator.apply_scene.assert_called_once_with(Scene.EVENING_COMFORT)


@pytest.mark.unit
@pytest.mark.select
class TestSceneSelectInitialization:
    """Test select entity initialization and attributes."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator."""
        coordinator = MagicMock()
        coordinator.get_current_scene = MagicMock(return_value=Scene.DEFAULT)
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    def test_select_initialization(self, mock_coordinator, mock_config_entry):
        """Test select entity initializes with correct attributes."""
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        assert select.unique_id == "adaptive_lighting_pro_test_entry_select_scene"
        assert select.name == "Scene"
        assert select.icon == "mdi:palette-outline"

    def test_select_options_are_strings(self, mock_coordinator, mock_config_entry):
        """SCENARIO: HA expects select options to be strings

        EXPECTED: Options are Scene.value strings, not enum objects
        WHY: HA SelectEntity API requires string options
        """
        select = ALPSceneSelect(mock_coordinator, mock_config_entry)

        # All options should be strings
        assert all(isinstance(opt, str) for opt in select.options)
        # Verify they match Scene enum values
        assert set(select.options) == {
            Scene.ALL_LIGHTS.value,
            Scene.NO_SPOTLIGHTS.value,
            Scene.EVENING_COMFORT.value,
            Scene.ULTRA_DIM.value,
        }


@pytest.mark.unit
@pytest.mark.select
class TestSelectPlatformSetup:
    """Test select platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_select(self):
        """SCENARIO: Integration loaded, platforms being setup

        EXPECTED: Scene select entity created and added
        WHY: Users need the dropdown in UI
        """
        mock_hass = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"
        mock_async_add_entities = MagicMock()

        # Setup mock coordinator in hass.data
        mock_coordinator = MagicMock()
        mock_coordinator.get_current_scene = MagicMock(return_value=Scene.DEFAULT)
        mock_hass.data = {
            DOMAIN: {
                "test_entry": {"coordinator": mock_coordinator}
            }
        }

        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)

        # Verify entity added
        assert mock_async_add_entities.called
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], ALPSceneSelect)

    @pytest.mark.asyncio
    async def test_async_setup_entry_handles_legacy_storage(self):
        """SCENARIO: Integration uses legacy direct coordinator storage

        EXPECTED: Platform handles both dict and direct storage
        WHY: Backward compatibility during migration
        """
        mock_hass = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "test_entry"
        mock_async_add_entities = MagicMock()

        # Setup mock coordinator in legacy direct storage format
        mock_coordinator = MagicMock()
        mock_coordinator.get_current_scene = MagicMock(return_value=Scene.DEFAULT)
        mock_hass.data = {
            DOMAIN: {
                "test_entry": mock_coordinator  # Direct coordinator, not dict
            }
        }

        await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)

        # Should still work
        assert mock_async_add_entities.called
        entities = mock_async_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], ALPSceneSelect)
