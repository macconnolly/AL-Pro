"""Tests for service handlers - core user interactions.

Following claude.md standards: "This is YOUR home. You live here."

Test Philosophy:
- Services are the control panel of your smart home
- Every service represents a real action you'll take daily
- Services must be bulletproof - they're called by automations

Real Scenarios:
- Sonos alarm at 6 AM → set_wake_alarm service → Wake sequence starts
- Video call in 30 seconds → adjust_brightness service → Instant boost
- Evening wind-down → apply_scene service → Ultra dim for relaxation
- Kids broke everything → reset_all service → Nuclear reset, back to normal
- Automation cleared alarm → clear_wake_alarm service → Wake sequence stops
"""
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock, AsyncMock, call, patch
from typing import Any

import pytest
import voluptuous as vol

from custom_components.adaptive_lighting_pro.services import (
    _get_coordinator,
    async_register_services,
    async_unregister_services,
    ADJUST_BRIGHTNESS_SCHEMA,
    ADJUST_COLOR_TEMP_SCHEMA,
    APPLY_SCENE_SCHEMA,
    SET_WAKE_ALARM_SCHEMA,
)
from custom_components.adaptive_lighting_pro.const import (
    DOMAIN,
    Scene,
    SERVICE_ADJUST_BRIGHTNESS,
    SERVICE_ADJUST_COLOR_TEMP,
    SERVICE_RESET_MANUAL_ADJUSTMENTS,
    SERVICE_RESET_ALL,
    SERVICE_CLEAR_MANUAL_CONTROL,
    SERVICE_APPLY_SCENE,
    SERVICE_SET_WAKE_ALARM,
    SERVICE_CLEAR_WAKE_ALARM,
)


@pytest.mark.unit
@pytest.mark.services
class TestGetCoordinator:
    """Test _get_coordinator() helper function."""

    def test_get_coordinator_dict_storage(self):
        """SCENARIO: Integration uses dict-based storage (current pattern)

        EXPECTED: Returns coordinator from dict entry
        WHY: Standard Home Assistant pattern for coordinator storage
        """
        # Setup hass.data with dict-based storage
        coordinator = MagicMock()
        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "coordinator": coordinator,
                    "other_data": "ignored",
                }
            }
        }

        result = _get_coordinator(hass)

        assert result is coordinator

    def test_get_coordinator_direct_storage(self):
        """SCENARIO: Legacy integration uses direct coordinator storage

        EXPECTED: Returns coordinator directly
        WHY: Backward compatibility with old storage pattern
        """
        coordinator = MagicMock()
        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                "test_entry_id": coordinator,  # Direct storage (legacy)
            }
        }

        result = _get_coordinator(hass)

        assert result is coordinator

    def test_get_coordinator_missing_domain(self):
        """SCENARIO: Integration not loaded yet

        EXPECTED: Returns None, logs error
        WHY: Service called before integration loaded (race condition)
        """
        hass = MagicMock()
        hass.data = {}  # No DOMAIN entry

        result = _get_coordinator(hass)

        assert result is None

    def test_get_coordinator_empty_domain(self):
        """SCENARIO: Domain exists but no entries

        EXPECTED: Returns None, logs error
        WHY: Service called after integration unloaded
        """
        hass = MagicMock()
        hass.data = {DOMAIN: {}}  # Empty domain

        result = _get_coordinator(hass)

        assert result is None


@pytest.mark.unit
@pytest.mark.services
class TestServiceSchemas:
    """Test service parameter schemas for validation."""

    def test_adjust_brightness_schema_valid(self):
        """Valid brightness adjustment parameters."""
        # Test all valid ranges
        assert ADJUST_BRIGHTNESS_SCHEMA({"value": 0}) == {"value": 0, "temporary": True}
        assert ADJUST_BRIGHTNESS_SCHEMA({"value": 50}) == {"value": 50, "temporary": True}
        assert ADJUST_BRIGHTNESS_SCHEMA({"value": -50}) == {"value": -50, "temporary": True}
        assert ADJUST_BRIGHTNESS_SCHEMA({"value": 100}) == {"value": 100, "temporary": True}
        assert ADJUST_BRIGHTNESS_SCHEMA({"value": -100}) == {"value": -100, "temporary": True}

        # Test temporary flag
        assert ADJUST_BRIGHTNESS_SCHEMA({"value": 25, "temporary": False}) == {
            "value": 25,
            "temporary": False,
        }

    def test_adjust_brightness_schema_invalid(self):
        """Invalid brightness adjustment parameters."""
        with pytest.raises(vol.Invalid):
            ADJUST_BRIGHTNESS_SCHEMA({"value": 101})  # Over max

        with pytest.raises(vol.Invalid):
            ADJUST_BRIGHTNESS_SCHEMA({"value": -101})  # Under min

        with pytest.raises(vol.Invalid):
            ADJUST_BRIGHTNESS_SCHEMA({})  # Missing required value

    def test_adjust_color_temp_schema_valid(self):
        """Valid color temp adjustment parameters."""
        assert ADJUST_COLOR_TEMP_SCHEMA({"value": 0}) == {"value": 0, "temporary": True}
        assert ADJUST_COLOR_TEMP_SCHEMA({"value": 1000}) == {"value": 1000, "temporary": True}
        assert ADJUST_COLOR_TEMP_SCHEMA({"value": -1000}) == {"value": -1000, "temporary": True}
        assert ADJUST_COLOR_TEMP_SCHEMA({"value": 2500}) == {"value": 2500, "temporary": True}
        assert ADJUST_COLOR_TEMP_SCHEMA({"value": -2500}) == {"value": -2500, "temporary": True}

    def test_apply_scene_schema_valid(self):
        """Valid scene parameters."""
        for scene in Scene:
            result = APPLY_SCENE_SCHEMA({"scene": scene.value})
            assert result == {"scene": scene.value}

    def test_apply_scene_schema_invalid(self):
        """Invalid scene parameters."""
        with pytest.raises(vol.Invalid):
            APPLY_SCENE_SCHEMA({"scene": "invalid_scene"})

    def test_set_wake_alarm_schema_valid(self):
        """Valid wake alarm parameters."""
        alarm_time = datetime(2025, 10, 6, 7, 0, 0, tzinfo=UTC)
        result = SET_WAKE_ALARM_SCHEMA({"alarm_time": alarm_time})
        assert result["alarm_time"] == alarm_time


@pytest.mark.unit
@pytest.mark.services
class TestAdjustBrightnessService:
    """Test adjust_brightness service handler."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with brightness methods."""
        coordinator = MagicMock()
        coordinator.set_brightness_adjustment = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_hass(self, mock_coordinator):
        """Mock Home Assistant with coordinator."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"coordinator": mock_coordinator}}}
        hass.services = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_video_call_brightness_boost(self, mock_hass, mock_coordinator):
        """SCENARIO: Video call in 30 seconds, need instant +25% brightness

        EXPECTED: Service calls coordinator, starts timers (temporary override)
        WHY: Fastest way to boost brightness from automation
        """
        # Register services
        async_register_services(mock_hass)

        # Get the registered handler
        adjust_brightness_handler = mock_hass.services.async_register.call_args_list[0][0][2]

        # Call service with +25% boost
        call_data = MagicMock()
        call_data.data = {"value": 25, "temporary": True}

        await adjust_brightness_handler(call_data)

        # Verify coordinator called with correct parameters
        mock_coordinator.set_brightness_adjustment.assert_called_once_with(25, start_timers=True)

    @pytest.mark.asyncio
    async def test_permanent_brightness_adjustment(self, mock_hass, mock_coordinator):
        """SCENARIO: User wants -15% dimmer until they manually change it

        EXPECTED: Service calls coordinator WITHOUT starting timers
        WHY: Permanent adjustment that shouldn't auto-expire
        """
        async_register_services(mock_hass)
        adjust_brightness_handler = mock_hass.services.async_register.call_args_list[0][0][2]

        call_data = MagicMock()
        call_data.data = {"value": -15, "temporary": False}

        await adjust_brightness_handler(call_data)

        # Verify NO timers started (permanent adjustment)
        mock_coordinator.set_brightness_adjustment.assert_called_once_with(-15, start_timers=False)

    @pytest.mark.asyncio
    async def test_brightness_service_missing_coordinator(self, mock_hass):
        """SCENARIO: Service called but coordinator not loaded

        EXPECTED: Service handles gracefully, logs error
        WHY: Automation might trigger during startup race condition
        """
        # Remove coordinator
        mock_hass.data = {}

        async_register_services(mock_hass)
        adjust_brightness_handler = mock_hass.services.async_register.call_args_list[0][0][2]

        call_data = MagicMock()
        call_data.data = {"value": 20, "temporary": True}

        # Should not raise exception
        await adjust_brightness_handler(call_data)

    @pytest.mark.asyncio
    async def test_brightness_service_coordinator_error(self, mock_hass, mock_coordinator):
        """SCENARIO: Coordinator method raises exception

        EXPECTED: Service catches error, logs, continues
        WHY: Service errors shouldn't crash Home Assistant
        """
        # Make coordinator raise error
        mock_coordinator.set_brightness_adjustment.side_effect = RuntimeError("Test error")

        async_register_services(mock_hass)
        adjust_brightness_handler = mock_hass.services.async_register.call_args_list[0][0][2]

        call_data = MagicMock()
        call_data.data = {"value": 30, "temporary": True}

        # Should not raise exception (caught and logged)
        await adjust_brightness_handler(call_data)


@pytest.mark.unit
@pytest.mark.services
class TestAdjustColorTempService:
    """Test adjust_color_temp service handler."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with warmth methods."""
        coordinator = MagicMock()
        coordinator.set_warmth_adjustment = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_hass(self, mock_coordinator):
        """Mock Home Assistant with coordinator."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"coordinator": mock_coordinator}}}
        hass.services = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_cooler_for_focus_work(self, mock_hass, mock_coordinator):
        """SCENARIO: Deep work session, want cooler (bluer) light for focus

        EXPECTED: Service calls coordinator with +1000K (cooler), starts timers
        WHY: Automation triggers cooler light when calendar shows "Focus Time"
        """
        async_register_services(mock_hass)
        adjust_color_temp_handler = mock_hass.services.async_register.call_args_list[1][0][2]

        call_data = MagicMock()
        call_data.data = {"value": 1000, "temporary": True}  # Cooler

        await adjust_color_temp_handler(call_data)

        mock_coordinator.set_warmth_adjustment.assert_called_once_with(1000, start_timers=True)

    @pytest.mark.asyncio
    async def test_warmer_for_evening_wind_down(self, mock_hass, mock_coordinator):
        """SCENARIO: Evening relaxation, want warmer (yellower) light

        EXPECTED: Service calls coordinator with -1500K (warmer), starts timers
        WHY: Automation triggers warmer light at 8 PM for wind-down
        """
        async_register_services(mock_hass)
        adjust_color_temp_handler = mock_hass.services.async_register.call_args_list[1][0][2]

        call_data = MagicMock()
        call_data.data = {"value": -1500, "temporary": True}  # Warmer

        await adjust_color_temp_handler(call_data)

        mock_coordinator.set_warmth_adjustment.assert_called_once_with(-1500, start_timers=True)

    @pytest.mark.asyncio
    async def test_permanent_warmth_adjustment(self, mock_hass, mock_coordinator):
        """SCENARIO: User always wants warmer lights, no timer expiry

        EXPECTED: Service calls coordinator WITHOUT starting timers
        WHY: Permanent preference adjustment
        """
        async_register_services(mock_hass)
        adjust_color_temp_handler = mock_hass.services.async_register.call_args_list[1][0][2]

        call_data = MagicMock()
        call_data.data = {"value": -800, "temporary": False}

        await adjust_color_temp_handler(call_data)

        mock_coordinator.set_warmth_adjustment.assert_called_once_with(-800, start_timers=False)


@pytest.mark.unit
@pytest.mark.services
class TestResetServices:
    """Test reset service handlers."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with reset methods."""
        coordinator = MagicMock()
        coordinator.set_brightness_adjustment = AsyncMock()
        coordinator.set_warmth_adjustment = AsyncMock()
        coordinator.clear_scene_offsets = AsyncMock()
        coordinator.cancel_all_timers = AsyncMock(return_value=3)  # 3 zones cleared
        return coordinator

    @pytest.fixture
    def mock_hass(self, mock_coordinator):
        """Mock Home Assistant with coordinator."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"coordinator": mock_coordinator}}}
        hass.services = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_reset_manual_adjustments_after_party(self, mock_hass, mock_coordinator):
        """SCENARIO: Party over, had +40% brightness and Ultra Dim scene active

        EXPECTED: Resets adjustments to 0, clears scene offsets, keeps timers
        WHY: Return to automatic but let timers continue (might still be manual)
        """
        async_register_services(mock_hass)
        reset_manual_handler = mock_hass.services.async_register.call_args_list[2][0][2]

        call_data = MagicMock()
        call_data.data = {}

        await reset_manual_handler(call_data)

        # Verify all adjustments reset
        mock_coordinator.set_brightness_adjustment.assert_called_once_with(0)
        mock_coordinator.set_warmth_adjustment.assert_called_once_with(0)
        mock_coordinator.clear_scene_offsets.assert_called_once()

        # Verify timers NOT cancelled (timers stay active)
        mock_coordinator.cancel_all_timers.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_all_nuclear_option(self, mock_hass, mock_coordinator):
        """SCENARIO: Kids broke everything, need total reset NOW

        EXPECTED: Nuclear reset - adjustments, scenes, AND timers all cleared
        WHY: Emergency "fix everything" button for dashboard
        """
        async_register_services(mock_hass)
        reset_all_handler = mock_hass.services.async_register.call_args_list[3][0][2]

        call_data = MagicMock()
        call_data.data = {}

        await reset_all_handler(call_data)

        # Verify complete reset
        mock_coordinator.set_brightness_adjustment.assert_called_once_with(0)
        mock_coordinator.set_warmth_adjustment.assert_called_once_with(0)
        mock_coordinator.clear_scene_offsets.assert_called_once()
        mock_coordinator.cancel_all_timers.assert_called_once()


@pytest.mark.unit
@pytest.mark.services
class TestClearManualControlService:
    """Test clear_manual_control service handler."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with timer methods."""
        coordinator = MagicMock()
        coordinator.cancel_manual_timer = AsyncMock(return_value=True)
        coordinator.cancel_all_timers = AsyncMock(return_value=5)
        return coordinator

    @pytest.fixture
    def mock_hass(self, mock_coordinator):
        """Mock Home Assistant with coordinator."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"coordinator": mock_coordinator}}}
        hass.services = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_clear_specific_zone_after_manual_change(self, mock_hass, mock_coordinator):
        """SCENARIO: Touched bedroom lights for bathroom trip, want AL back

        EXPECTED: Clears manual control timer for bedroom zone only
        WHY: Restore AL to one zone without affecting others
        """
        async_register_services(mock_hass)
        clear_manual_handler = mock_hass.services.async_register.call_args_list[4][0][2]

        call_data = MagicMock()
        call_data.data = {"zone_id": "bedroom"}

        await clear_manual_handler(call_data)

        # Verify only bedroom zone cleared
        mock_coordinator.cancel_manual_timer.assert_called_once_with("bedroom")
        mock_coordinator.cancel_all_timers.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_all_zones_overnight_reset(self, mock_hass, mock_coordinator):
        """SCENARIO: 2 AM overnight reset automation, clear all manual overrides

        EXPECTED: Clears manual control for ALL zones
        WHY: Daily reset to ensure AL resumes everywhere
        """
        async_register_services(mock_hass)
        clear_manual_handler = mock_hass.services.async_register.call_args_list[4][0][2]

        call_data = MagicMock()
        call_data.data = {}  # No zone_id = all zones

        await clear_manual_handler(call_data)

        # Verify all zones cleared
        mock_coordinator.cancel_all_timers.assert_called_once()
        mock_coordinator.cancel_manual_timer.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_manual_control_zone_not_found(self, mock_hass, mock_coordinator):
        """SCENARIO: Automation tries to clear non-existent zone

        EXPECTED: Service handles gracefully, logs warning
        WHY: Zone might be renamed/removed, automation outdated
        """
        # Make cancel return False (zone not found)
        mock_coordinator.cancel_manual_timer.return_value = False

        async_register_services(mock_hass)
        clear_manual_handler = mock_hass.services.async_register.call_args_list[4][0][2]

        call_data = MagicMock()
        call_data.data = {"zone_id": "nonexistent"}

        # Should not raise exception
        await clear_manual_handler(call_data)


@pytest.mark.unit
@pytest.mark.services
class TestApplySceneService:
    """Test apply_scene service handler."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with scene methods."""
        coordinator = MagicMock()
        coordinator.apply_scene = AsyncMock(return_value=True)
        return coordinator

    @pytest.fixture
    def mock_hass(self, mock_coordinator):
        """Mock Home Assistant with coordinator."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"coordinator": mock_coordinator}}}
        hass.services = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_ultra_dim_for_tv_watching(self, mock_hass, mock_coordinator):
        """SCENARIO: Movie night, need ultra dim lights (5% brightness)

        EXPECTED: Service applies Ultra Dim scene via coordinator
        WHY: Fastest way to set perfect movie lighting
        """
        async_register_services(mock_hass)
        apply_scene_handler = mock_hass.services.async_register.call_args_list[6][0][2]

        call_data = MagicMock()
        call_data.data = {"scene": "ultra_dim"}

        await apply_scene_handler(call_data)

        # Verify scene applied
        mock_coordinator.apply_scene.assert_called_once()
        applied_scene = mock_coordinator.apply_scene.call_args[0][0]
        assert applied_scene == Scene.ULTRA_DIM

    @pytest.mark.asyncio
    async def test_evening_comfort_wind_down(self, mock_hass, mock_coordinator):
        """SCENARIO: 8 PM wind-down, want warmer dimmer lights

        EXPECTED: Service applies Evening Comfort scene
        WHY: Automation triggers perfect evening ambiance
        """
        async_register_services(mock_hass)
        apply_scene_handler = mock_hass.services.async_register.call_args_list[6][0][2]

        call_data = MagicMock()
        call_data.data = {"scene": "evening_comfort"}

        await apply_scene_handler(call_data)

        applied_scene = mock_coordinator.apply_scene.call_args[0][0]
        assert applied_scene == Scene.EVENING_COMFORT

    @pytest.mark.asyncio
    async def test_all_lights_return_to_auto(self, mock_hass, mock_coordinator):
        """SCENARIO: Party over, want all lights back to automatic

        EXPECTED: Service applies ALL_LIGHTS scene (clears overrides)
        WHY: Quick return to normal automatic operation
        """
        async_register_services(mock_hass)
        apply_scene_handler = mock_hass.services.async_register.call_args_list[6][0][2]

        call_data = MagicMock()
        call_data.data = {"scene": "all_lights"}

        await apply_scene_handler(call_data)

        applied_scene = mock_coordinator.apply_scene.call_args[0][0]
        assert applied_scene == Scene.ALL_LIGHTS

    @pytest.mark.asyncio
    async def test_invalid_scene_name(self, mock_hass, mock_coordinator):
        """SCENARIO: Automation has typo in scene name

        EXPECTED: Service handles ValueError gracefully, logs error
        WHY: Bad automation shouldn't crash integration
        """
        async_register_services(mock_hass)
        apply_scene_handler = mock_hass.services.async_register.call_args_list[6][0][2]

        call_data = MagicMock()
        call_data.data = {"scene": "invalid_scene_name"}

        # Should not raise exception (caught and logged)
        await apply_scene_handler(call_data)


@pytest.mark.unit
@pytest.mark.services
class TestCycleSceneService:
    """Test cycle_scene service handler."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with cycle_scene method."""
        coordinator = MagicMock()
        coordinator.cycle_scene = AsyncMock(return_value=Scene.EVENING_COMFORT)
        return coordinator

    @pytest.fixture
    def mock_hass(self, mock_coordinator):
        """Mock Home Assistant with coordinator."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"coordinator": mock_coordinator}}}
        hass.services = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_cycle_scene_from_dashboard_button(self, mock_hass, mock_coordinator):
        """SCENARIO: Dashboard button cycles through scenes

        EXPECTED: Service calls coordinator cycle_scene method
        WHY: Single button to cycle through all scene options
        """
        async_register_services(mock_hass)
        cycle_scene_handler = mock_hass.services.async_register.call_args_list[7][0][2]

        call_data = MagicMock()
        call_data.data = {}

        await cycle_scene_handler(call_data)

        mock_coordinator.cycle_scene.assert_called_once()


@pytest.mark.unit
@pytest.mark.services
class TestWakeAlarmServices:
    """Test wake alarm service handlers."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with wake alarm methods."""
        coordinator = MagicMock()
        coordinator.set_wake_alarm = AsyncMock()
        coordinator.clear_wake_alarm = AsyncMock()
        coordinator.get_wake_start_time = MagicMock(
            return_value=datetime(2025, 10, 6, 6, 45, 0, tzinfo=UTC)
        )
        return coordinator

    @pytest.fixture
    def mock_hass(self, mock_coordinator):
        """Mock Home Assistant with coordinator."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"coordinator": mock_coordinator}}}
        hass.services = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_set_wake_alarm_for_manual_alarm(self, mock_hass, mock_coordinator):
        """SCENARIO: User sets manual wake alarm for 7 AM wake-up

        EXPECTED: Service calls coordinator, wake sequence starts 15min before
        WHY: Testing wake sequence without Sonos integration
        """
        async_register_services(mock_hass)
        set_wake_alarm_handler = mock_hass.services.async_register.call_args_list[8][0][2]

        alarm_time = datetime(2025, 10, 6, 7, 0, 0, tzinfo=UTC)
        call_data = MagicMock()
        call_data.data = {"alarm_time": alarm_time}

        await set_wake_alarm_handler(call_data)

        # Verify wake alarm set
        mock_coordinator.set_wake_alarm.assert_called_once_with(alarm_time)

        # Verify wake start time retrieved (for logging)
        mock_coordinator.get_wake_start_time.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_wake_alarm_past_time_rejected(self, mock_hass, mock_coordinator):
        """SCENARIO: Automation tries to set alarm in the past

        EXPECTED: Coordinator raises ValueError, service catches and logs
        WHY: Can't trigger wake sequence for past time
        """
        # Make coordinator raise ValueError for past alarm
        mock_coordinator.set_wake_alarm.side_effect = ValueError("Alarm time cannot be in the past")

        async_register_services(mock_hass)
        set_wake_alarm_handler = mock_hass.services.async_register.call_args_list[8][0][2]

        past_time = datetime(2024, 1, 1, 7, 0, 0, tzinfo=UTC)
        call_data = MagicMock()
        call_data.data = {"alarm_time": past_time}

        # Should not raise exception (caught and logged)
        await set_wake_alarm_handler(call_data)

    @pytest.mark.asyncio
    async def test_clear_wake_alarm_after_sonos_alarm_cancelled(self, mock_hass, mock_coordinator):
        """SCENARIO: Sonos alarm cancelled, need to stop wake sequence

        EXPECTED: Service clears wake alarm via coordinator
        WHY: Automation monitors Sonos alarms, clears wake when alarm removed
        """
        async_register_services(mock_hass)
        clear_wake_alarm_handler = mock_hass.services.async_register.call_args_list[9][0][2]

        call_data = MagicMock()
        call_data.data = {}

        await clear_wake_alarm_handler(call_data)

        # Verify wake alarm cleared
        mock_coordinator.clear_wake_alarm.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_wake_alarm_when_none_active(self, mock_hass, mock_coordinator):
        """SCENARIO: Service called but no wake alarm active

        EXPECTED: Service handles gracefully (idempotent)
        WHY: Automation might call clear even when nothing to clear
        """
        async_register_services(mock_hass)
        clear_wake_alarm_handler = mock_hass.services.async_register.call_args_list[9][0][2]

        call_data = MagicMock()
        call_data.data = {}

        # Should not raise exception (idempotent operation)
        await clear_wake_alarm_handler(call_data)

        mock_coordinator.clear_wake_alarm.assert_called_once()


@pytest.mark.unit
@pytest.mark.services
class TestServiceRegistration:
    """Test service registration and unregistration."""

    def test_register_services_creates_all_handlers(self):
        """SCENARIO: Integration loads, needs to register services

        EXPECTED: All 10 services registered with Home Assistant
        WHY: Services are the user's control panel
        """
        hass = MagicMock()
        hass.services = MagicMock()

        async_register_services(hass)

        # Verify all services registered
        assert hass.services.async_register.call_count == 10

        # Verify service names
        registered_services = [
            call_args[0][1]  # Second arg is service name
            for call_args in hass.services.async_register.call_args_list
        ]

        expected_services = [
            SERVICE_ADJUST_BRIGHTNESS,
            SERVICE_ADJUST_COLOR_TEMP,
            SERVICE_RESET_MANUAL_ADJUSTMENTS,
            SERVICE_RESET_ALL,
            SERVICE_CLEAR_MANUAL_CONTROL,
            "set_mode",  # Deprecated but still registered
            SERVICE_APPLY_SCENE,
            "cycle_scene",
            SERVICE_SET_WAKE_ALARM,
            SERVICE_CLEAR_WAKE_ALARM,
        ]

        assert registered_services == expected_services

    def test_unregister_services_removes_all_handlers(self):
        """SCENARIO: Integration unloaded, must clean up services

        EXPECTED: All services unregistered from Home Assistant
        WHY: Clean shutdown, prevent service calls to dead integration
        """
        hass = MagicMock()
        hass.services = MagicMock()

        async_unregister_services(hass)

        # Verify all services unregistered
        assert hass.services.async_remove.call_count == 10


@pytest.mark.unit
@pytest.mark.services
class TestSetModeDeprecatedService:
    """Test set_mode deprecated service handler."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"coordinator": MagicMock()}}}
        hass.services = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_set_mode_logs_deprecation_warning(self, mock_hass):
        """SCENARIO: Old automation still uses set_mode service

        EXPECTED: Service logs warning about deprecation
        WHY: Backward compatibility during migration to scenes
        """
        async_register_services(mock_hass)
        set_mode_handler = mock_hass.services.async_register.call_args_list[5][0][2]

        call_data = MagicMock()
        call_data.data = {"mode": "evening"}

        # Should not raise exception, just log warning
        await set_mode_handler(call_data)


@pytest.mark.unit
@pytest.mark.services
class TestServiceErrorHandling:
    """Test service error handling and edge cases."""

    @pytest.fixture
    def mock_coordinator_with_errors(self):
        """Mock coordinator that raises various errors."""
        coordinator = MagicMock()
        coordinator.set_brightness_adjustment = AsyncMock(side_effect=RuntimeError("Test error"))
        coordinator.apply_scene = AsyncMock(side_effect=ValueError("Invalid scene"))
        return coordinator

    @pytest.fixture
    def mock_hass(self, mock_coordinator_with_errors):
        """Mock Home Assistant with error-prone coordinator."""
        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_id": {"coordinator": mock_coordinator_with_errors}}}
        hass.services = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_services_handle_coordinator_exceptions(self, mock_hass, mock_coordinator_with_errors):
        """SCENARIO: Coordinator methods raise exceptions

        EXPECTED: Services catch exceptions, log errors, don't crash
        WHY: Service errors shouldn't crash Home Assistant core
        """
        async_register_services(mock_hass)

        # Test brightness service with error
        adjust_brightness_handler = mock_hass.services.async_register.call_args_list[0][0][2]
        call_data = MagicMock()
        call_data.data = {"value": 25, "temporary": True}

        # Should not raise exception (caught and logged)
        await adjust_brightness_handler(call_data)

        # Test scene service with error
        apply_scene_handler = mock_hass.services.async_register.call_args_list[6][0][2]
        call_data.data = {"scene": "ultra_dim"}

        # Should not raise exception (caught and logged)
        await apply_scene_handler(call_data)
