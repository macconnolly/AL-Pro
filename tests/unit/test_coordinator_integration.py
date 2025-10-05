"""Coordinator integration tests - WHERE BUGS HIDE.

THE CRITICAL COMPONENT: Does the coordinator correctly combine all features?
This is where environmental + sunset + manual + zone settings ALL interact.

WHAT WE'RE TESTING:
1. Zone with environmental_enabled=False should skip environmental boost
2. Combined boost overflow (37%) on narrow zone (35% range) → boundary collapse
3. Manual control active zones should skip ALL adjustments
4. Disabled zones should be completely skipped
5. Timer expiration should restore adaptive control
6. Multiple zones with different states (manual, disabled, normal)
7. Service call failures should not crash coordinator

WHY THIS MATTERS:
- Coordinator is 16% tested (LOWEST COVERAGE)
- This is where ALL features combine - most likely place for bugs
- Environmental boost applied to zones with environmental_enabled=False (SUSPECTED BUG)
- Combined boost could exceed zone range and collapse boundaries
- Timer expiration must reliably restore adaptive control
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from custom_components.adaptive_lighting_pro.coordinator import (
    ALPDataUpdateCoordinator,
)


@pytest.mark.unit
@pytest.mark.coordinator
class TestEnvironmentalBoostPerZone:
    """Test per-zone environmental boost control - SUSPECTED BUG."""

    @pytest.fixture
    def coordinator(self, mock_hass, mock_config_entry):
        """Create coordinator with zones that have different environmental settings."""
        return ALPDataUpdateCoordinator(hass=mock_hass, config_entry=mock_config_entry)

    @pytest.mark.asyncio
    async def test_zone_with_environmental_disabled_should_skip_env_boost(
        self, coordinator
    ):
        """Zone with environmental_enabled=False should NOT get environmental boost.

        REAL SCENARIO: Kitchen (recessed) has environmental_enabled=False
        CONDITIONS: Foggy day, environmental boost = 25%
        EXPECTED: Kitchen gets 0% env boost, only manual adjustments
        BUG SUSPECTED: Coordinator applies env boost to ALL zones regardless of flag

        THIS IS A CRITICAL BUG - user explicitly disabled environmental for this zone.
        """
        # Mock foggy conditions (25% environmental boost)
        with patch.object(
            coordinator._env_adapter, "calculate_boost", return_value=25
        ):
            with patch.object(
                coordinator._sunset_boost, "calculate_boost", return_value=0
            ):
                # Mock AL switch state
                kitchen_state = MagicMock()
                kitchen_state.state = "on"
                kitchen_state.attributes = {
                    "manual_control": False,
                    "brightness_pct": 50,
                    "color_temp_kelvin": 2700,
                }
                coordinator.hass.states.get = MagicMock(return_value=kitchen_state)

                # Mock service call to capture what offset is applied
                service_calls = []

                async def capture_service_call(domain, service, data, **kwargs):
                    service_calls.append((domain, service, data))

                coordinator.hass.services.async_call = AsyncMock(
                    side_effect=capture_service_call
                )

                # Trigger update
                await coordinator._async_update_data()

                # Check if kitchen got service call
                kitchen_calls = [
                    c
                    for c in service_calls
                    if c[2].get("entity_id") == "switch.adaptive_lighting_kitchen"
                ]

                # THE BUG: If kitchen gets adjusted despite environmental_enabled=False
                if kitchen_calls:
                    call_data = kitchen_calls[0][2]
                    # Calculate offset that was applied
                    # Kitchen base: min=60, max=100
                    # If env boost applied: min would be 60+25=85
                    # If env boost skipped: min would be 60
                    applied_offset = call_data["min_brightness"] - 60

                    assert applied_offset == 0, (
                        f"SUSPECTED BUG CONFIRMED: Kitchen has environmental_enabled=False "
                        f"but received {applied_offset}% offset (expected 0%). "
                        f"Zone config flag 'environmental_enabled' is being IGNORED. "
                        f"Full service call: {call_data}"
                    )
                # If no calls, that's also acceptable (0% offset = no adjustment needed)

    @pytest.mark.asyncio
    async def test_zone_with_environmental_enabled_should_get_env_boost(
        self, coordinator
    ):
        """Zone with environmental_enabled=True should GET environmental boost.

        REAL SCENARIO: Living room has environmental_enabled=True
        CONDITIONS: Foggy day, environmental boost = 25%
        EXPECTED: Living room gets 25% env boost applied
        """
        with patch.object(
            coordinator._env_adapter, "calculate_boost", return_value=25
        ):
            with patch.object(
                coordinator._sunset_boost, "calculate_boost", return_value=0
            ):
                living_state = MagicMock()
                living_state.state = "on"
                living_state.attributes = {
                    "manual_control": False,
                    "brightness_pct": 50,
                    "color_temp_kelvin": 2700,
                }
                coordinator.hass.states.get = MagicMock(return_value=living_state)

                service_calls = []

                async def capture_service_call(domain, service, data, **kwargs):
                    service_calls.append((domain, service, data))

                coordinator.hass.services.async_call = AsyncMock(
                    side_effect=capture_service_call
                )

                await coordinator._async_update_data()

                living_calls = [
                    c
                    for c in service_calls
                    if c[2].get("entity_id") == "switch.adaptive_lighting_main_living"
                ]

                assert len(living_calls) > 0, (
                    "Living room should receive adjustment when env boost active"
                )
                call_data = living_calls[0][2]
                # Living room base: min=45, max=100
                # With 25% boost: min should be 45+25=70
                assert call_data["min_brightness"] == 70, (
                    f"Expected min=70 (45+25), got {call_data['min_brightness']}"
                )


@pytest.mark.unit
@pytest.mark.coordinator
class TestCombinedBoostOverflow:
    """Test boundary collapse with extreme combined boosts - THE CRITICAL FAILURE."""

    @pytest.fixture
    def coordinator_narrow_zones(self, mock_hass):
        """Create coordinator with narrow-range zones to test overflow."""
        # Create config with narrow zone (35% range)
        config_entry = MagicMock()
        config_entry.data = {
            "zones": [
                {
                    "id": "narrow_zone",
                    "zone_id": "narrow_zone",
                    "name": "Narrow Zone",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_narrow",
                    "lights": ["light.narrow_1"],
                    "brightness_min": 45,
                    "brightness_max": 80,  # Only 35% range!
                    "color_temp_min": 2250,
                    "color_temp_max": 2950,
                    "environmental_enabled": True,
                    "enabled": True,
                }
            ],
            "environmental": {
                "lux_sensor": "sensor.outdoor_illuminance",
                "weather_entity": "weather.home",
                "enabled": True,
                "sunset_boost_enabled": True,
            },
            "global_settings": {},
        }
        config_entry.entry_id = "test_narrow"
        return ALPDataUpdateCoordinator(hass=mock_hass, config_entry=config_entry)

    @pytest.mark.asyncio
    async def test_extreme_combined_boost_should_collapse_narrow_zone(
        self, coordinator_narrow_zones
    ):
        """Narrow zone (35% range) + extreme boost (37%) → BOUNDARY COLLAPSE.

        REAL SCENARIO: Foggy winter sunset (THE OVERFLOW WE DISCOVERED)
        CONDITIONS:
        - Zone: min=45, max=80 (35% range)
        - Environmental: 25% (foggy)
        - Sunset: 12% (horizon)
        - Combined: 37%

        CALCULATION: new_min = 45 + 37 = 82 > max(80) → COLLAPSE
        RESULT: AL switch gets min=80, max=80 → 0% AL range (lights stuck)

        THE BUG: Coordinator should detect overflow and either:
        1. Cap combined boost at 30% (prevents overflow on 35% zones)
        2. Skip adjustment entirely for zones with insufficient range
        3. Warn user in logs

        Currently: Blindly applies 37% and lets adjustment_engine collapse boundaries
        """
        with patch.object(
            coordinator_narrow_zones._env_adapter, "calculate_boost", return_value=25
        ):
            with patch.object(
                coordinator_narrow_zones._sunset_boost,
                "calculate_boost",
                return_value=12,
            ):
                narrow_state = MagicMock()
                narrow_state.state = "on"
                narrow_state.attributes = {
                    "manual_control": False,
                    "brightness_pct": 60,
                    "color_temp_kelvin": 2700,
                }
                coordinator_narrow_zones.hass.states.get = MagicMock(
                    return_value=narrow_state
                )

                service_calls = []

                async def capture_service_call(domain, service, data, **kwargs):
                    service_calls.append((domain, service, data))

                coordinator_narrow_zones.hass.services.async_call = AsyncMock(
                    side_effect=capture_service_call
                )

                await coordinator_narrow_zones._async_update_data()

                narrow_calls = [
                    c
                    for c in service_calls
                    if c[2].get("entity_id") == "switch.adaptive_lighting_narrow"
                ]

                assert len(narrow_calls) > 0, "Narrow zone should receive adjustment"
                call_data = narrow_calls[0][2]

                # INTELLIGENT CAPPING: Zone range=35%, raw boost=37%, capped to 30%
                # min=45+30=75, max=80, AL has 5% range (prevents total collapse)
                assert call_data["min_brightness"] == 75, (
                    f"Expected min=75 (capped boost), got {call_data['min_brightness']}"
                )
                assert call_data["max_brightness"] == 80, (
                    f"Expected max=80 (unchanged), got {call_data['max_brightness']}"
                )

                # VERIFY INTELLIGENT CAPPING: 5% AL range (minimal but functional)
                al_range = call_data["max_brightness"] - call_data["min_brightness"]
                assert al_range == 5, (
                    f"INTELLIGENT CAPPING VERIFIED: AL range = {al_range}%. "
                    f"Zone configuration (35% range) with 37% raw boost. "
                    f"System capped at 30% to preserve 5% AL variation. "
                    f"This is CORRECT behavior - prevents total collapse."
                )


@pytest.mark.unit
@pytest.mark.coordinator
class TestManualControlSkipsAdjustments:
    """Test that manual control zones are skipped - CRITICAL USER EXPECTATION."""

    @pytest.fixture
    def coordinator(self, mock_hass, mock_config_entry):
        """Create coordinator."""
        return ALPDataUpdateCoordinator(hass=mock_hass, config_entry=mock_config_entry)

    @pytest.mark.asyncio
    async def test_zone_with_manual_control_active_should_skip_all_adjustments(
        self, coordinator
    ):
        """Zone with manual control timer active should skip ALL adjustments.

        REAL SCENARIO: User presses dimmer at 6 PM, timer set for 1 hour
        CONDITIONS: Environmental boost = 20%, Sunset boost = 10%
        EXPECTED: Living room gets ZERO adjustments while timer active
        WHY: User explicitly overrode system, respect their choice
        """
        # Start manual timer for living room
        await coordinator.zone_manager.async_start_manual_timer(
            "main_living", duration=3600
        )

        # Verify timer active
        assert coordinator.zone_manager.is_manual_control_active("main_living") is True

        with patch.object(
            coordinator._env_adapter, "calculate_boost", return_value=20
        ):
            with patch.object(
                coordinator._sunset_boost, "calculate_boost", return_value=10
            ):
                living_state = MagicMock()
                living_state.state = "on"
                living_state.attributes = {
                    "manual_control": False,  # AL integration doesn't know yet
                    "brightness_pct": 50,
                    "color_temp_kelvin": 2700,
                }
                coordinator.hass.states.get = MagicMock(return_value=living_state)

                service_calls = []

                async def capture_service_call(domain, service, data, **kwargs):
                    service_calls.append((domain, service, data))

                coordinator.hass.services.async_call = AsyncMock(
                    side_effect=capture_service_call
                )

                await coordinator._async_update_data()

                # Check living room did NOT get service call
                living_calls = [
                    c
                    for c in service_calls
                    if c[2].get("entity_id") == "switch.adaptive_lighting_main_living"
                ]

                assert len(living_calls) == 0, (
                    f"Living room has manual control timer active but received {len(living_calls)} "
                    f"adjustment calls. Manual control should BLOCK all adjustments. "
                    f"Service calls: {living_calls}"
                )

    @pytest.mark.asyncio
    async def test_other_zones_still_get_adjustments_when_one_has_manual_control(
        self, coordinator
    ):
        """Other zones should continue getting adjustments when one has manual control.

        REAL SCENARIO: User dims living room, but bedroom should still adapt
        EXPECTED: Living room skipped, bedroom gets adjustments
        """
        await coordinator.zone_manager.async_start_manual_timer(
            "main_living", duration=3600
        )

        with patch.object(
            coordinator._env_adapter, "calculate_boost", return_value=15
        ):
            with patch.object(
                coordinator._sunset_boost, "calculate_boost", return_value=0
            ):

                def get_state(entity_id):
                    state = MagicMock()
                    state.state = "on"
                    state.attributes = {
                        "manual_control": False,
                        "brightness_pct": 50,
                        "color_temp_kelvin": 2700,
                    }
                    return state

                coordinator.hass.states.get = MagicMock(side_effect=get_state)

                service_calls = []

                async def capture_service_call(domain, service, data, **kwargs):
                    service_calls.append((domain, service, data))

                coordinator.hass.services.async_call = AsyncMock(
                    side_effect=capture_service_call
                )

                await coordinator._async_update_data()

                # Living room should be skipped
                living_calls = [
                    c
                    for c in service_calls
                    if c[2].get("entity_id") == "switch.adaptive_lighting_main_living"
                ]
                assert len(living_calls) == 0, "Living room should be skipped"

                # Bedroom should get adjustment
                bedroom_calls = [
                    c
                    for c in service_calls
                    if c[2].get("entity_id") == "switch.adaptive_lighting_bedroom"
                ]
                assert len(bedroom_calls) > 0, (
                    "Bedroom should still get adjustments when living room has manual control"
                )


@pytest.mark.unit
@pytest.mark.coordinator
class TestDisabledZones:
    """Test that disabled zones are completely skipped."""

    @pytest.fixture
    def coordinator_with_disabled_zone(self, mock_hass):
        """Create coordinator with one disabled zone."""
        config_entry = MagicMock()
        config_entry.data = {
            "zones": [
                {
                    "id": "enabled_zone",
                    "zone_id": "enabled_zone",
                    "name": "Enabled Zone",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_enabled",
                    "lights": ["light.enabled_1"],
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": True,
                },
                {
                    "id": "disabled_zone",
                    "zone_id": "disabled_zone",
                    "name": "Disabled Zone",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_disabled",
                    "lights": ["light.disabled_1"],
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": False,  # DISABLED
                },
            ],
            "environmental": {
                "lux_sensor": "sensor.outdoor_illuminance",
                "weather_entity": "weather.home",
                "enabled": True,
            },
            "global_settings": {},
        }
        config_entry.entry_id = "test_disabled"
        return ALPDataUpdateCoordinator(hass=mock_hass, config_entry=config_entry)

    @pytest.mark.asyncio
    async def test_disabled_zone_should_not_receive_any_adjustments(
        self, coordinator_with_disabled_zone
    ):
        """Disabled zone should be completely ignored.

        REAL SCENARIO: User temporarily disabled a zone in config
        EXPECTED: Disabled zone gets NO service calls, enabled zone works normally
        """
        with patch.object(
            coordinator_with_disabled_zone._env_adapter,
            "calculate_boost",
            return_value=20,
        ):
            with patch.object(
                coordinator_with_disabled_zone._sunset_boost,
                "calculate_boost",
                return_value=0,
            ):

                def get_state(entity_id):
                    state = MagicMock()
                    state.state = "on"
                    state.attributes = {
                        "manual_control": False,
                        "brightness_pct": 50,
                        "color_temp_kelvin": 2700,
                    }
                    return state

                coordinator_with_disabled_zone.hass.states.get = MagicMock(
                    side_effect=get_state
                )

                service_calls = []

                async def capture_service_call(domain, service, data, **kwargs):
                    service_calls.append((domain, service, data))

                coordinator_with_disabled_zone.hass.services.async_call = AsyncMock(
                    side_effect=capture_service_call
                )

                await coordinator_with_disabled_zone._async_update_data()

                # Disabled zone should get NO calls
                disabled_calls = [
                    c
                    for c in service_calls
                    if c[2].get("entity_id") == "switch.adaptive_lighting_disabled"
                ]
                assert len(disabled_calls) == 0, (
                    f"Disabled zone received {len(disabled_calls)} service calls. "
                    f"Disabled zones should be COMPLETELY ignored. Calls: {disabled_calls}"
                )

                # Enabled zone should get calls
                enabled_calls = [
                    c
                    for c in service_calls
                    if c[2].get("entity_id") == "switch.adaptive_lighting_enabled"
                ]
                assert len(enabled_calls) > 0, (
                    "Enabled zone should receive adjustments"
                )


@pytest.mark.unit
@pytest.mark.coordinator
class TestTimerExpiration:
    """Test timer expiration and restoration of adaptive control."""

    @pytest.fixture
    def coordinator(self, mock_hass, mock_config_entry):
        """Create coordinator."""
        return ALPDataUpdateCoordinator(hass=mock_hass, config_entry=mock_config_entry)

    @pytest.mark.asyncio
    async def test_expired_timer_should_restore_adaptive_control(self, coordinator):
        """Expired timer should restore adaptive control and resume adjustments.

        REAL SCENARIO: User pressed dimmer at 6 PM with 1s timer, now 6:00:02 PM
        EXPECTED: Timer expires, zone returns to adaptive, gets adjustments again
        """
        from datetime import UTC, datetime, timedelta

        with patch(
            "custom_components.adaptive_lighting_pro.features.zone_manager.datetime"
        ) as mock_dt:
            start_time = datetime(2025, 1, 15, 18, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = start_time
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Start timer
            await coordinator.zone_manager.async_start_manual_timer(
                "main_living", duration=1
            )

            # Advance time past expiration
            mock_dt.now.return_value = start_time + timedelta(seconds=2)

            with patch.object(
                coordinator._env_adapter, "calculate_boost", return_value=15
            ):
                with patch.object(
                    coordinator._sunset_boost, "calculate_boost", return_value=0
                ):
                    living_state = MagicMock()
                    living_state.state = "on"
                    living_state.attributes = {
                        "manual_control": False,
                        "brightness_pct": 50,
                        "color_temp_kelvin": 2700,
                    }
                    coordinator.hass.states.get = MagicMock(return_value=living_state)

                    service_calls = []

                    async def capture_service_call(domain, service, data, **kwargs):
                        service_calls.append((domain, service, data))

                    coordinator.hass.services.async_call = AsyncMock(
                        side_effect=capture_service_call
                    )

                    # Trigger coordinator update (expires timer internally)
                    await coordinator._async_update_data()

                    # Check timer expired
                    assert (
                        coordinator.zone_manager.is_manual_control_active("main_living")
                        is False
                    ), "Timer should have expired"

                    # Check adaptive_lighting.apply was called to restore
                    apply_calls = [
                        c for c in service_calls if c[1] == "apply"
                    ]
                    assert len(apply_calls) > 0, (
                        "adaptive_lighting.apply should be called to restore adaptive control"
                    )

                    # Check zone received adjustments again
                    living_calls = [
                        c
                        for c in service_calls
                        if c[1] == "change_switch_settings"
                        and c[2].get("entity_id")
                        == "switch.adaptive_lighting_main_living"
                    ]
                    assert len(living_calls) > 0, (
                        "Zone should receive adjustments after timer expires"
                    )


@pytest.mark.unit
@pytest.mark.coordinator
class TestStartupInitialization:
    """Test coordinator startup initialization - CLEAN STATE ON STARTUP.

    WHAT WE'RE TESTING:
    - Coordinator starts with clean state (Phase 1.10)
    - All manual adjustments reset to 0
    - All zone timers cleared
    - Global pause set to False
    - Environmental adapters initialized

    WHY THIS MATTERS:
    - Replaces automation.al_startup_cleanup from YAML
    - Ensures predictable state on HA restart
    - Prevents stale timers from previous session
    """

    @pytest.fixture
    def coordinator(self, mock_hass, mock_config_entry):
        """Create coordinator."""
        return ALPDataUpdateCoordinator(hass=mock_hass, config_entry=mock_config_entry)

    @pytest.mark.asyncio
    async def test_async_initialize_resets_manual_adjustments(self, coordinator):
        """async_initialize() should reset brightness and warmth adjustments to 0.

        REAL SCENARIO: HA restart with stale adjustments from previous session
        EXPECTED: Both adjustments start at 0
        """
        # Set non-zero adjustments before initialization
        coordinator._brightness_adjustment = 25
        coordinator._warmth_adjustment = -500

        # Do first refresh to populate data
        with patch.object(
            coordinator._env_adapter, "calculate_boost", return_value=0
        ):
            with patch.object(
                coordinator._sunset_boost, "calculate_boost", return_value=0
            ):
                def get_state(entity_id):
                    state = MagicMock()
                    state.state = "on"
                    state.attributes = {
                        "manual_control": False,
                        "brightness_pct": 50,
                        "color_temp_kelvin": 2700,
                    }
                    return state

                coordinator.hass.states.get = MagicMock(side_effect=get_state)
                coordinator.hass.services.async_call = AsyncMock()

                # Populate coordinator.data
                coordinator.data = await coordinator._async_update_data()

        # Now initialize
        await coordinator.async_initialize()

        # Verify adjustments reset
        assert coordinator._brightness_adjustment == 0, (
            f"Expected brightness_adjustment=0, got {coordinator._brightness_adjustment}"
        )
        assert coordinator._warmth_adjustment == 0, (
            f"Expected warmth_adjustment=0, got {coordinator._warmth_adjustment}"
        )
        assert coordinator.data["global"]["total_brightness_adjustment"] == 0
        assert coordinator.data["global"]["total_warmth_adjustment"] == 0

    @pytest.mark.asyncio
    async def test_async_initialize_clears_all_zone_timers(self, coordinator):
        """async_initialize() should clear all active zone timers.

        REAL SCENARIO: HA restart with active timers from previous session
        EXPECTED: All timers cancelled, no zones in manual control
        """
        # Start timers for multiple zones
        await coordinator.zone_manager.async_start_manual_timer("main_living", duration=3600)
        await coordinator.zone_manager.async_start_manual_timer("bedroom", duration=1800)

        # Verify timers active
        assert coordinator.zone_manager.is_manual_control_active("main_living") is True
        assert coordinator.zone_manager.is_manual_control_active("bedroom") is True

        # Do first refresh
        with patch.object(
            coordinator._env_adapter, "calculate_boost", return_value=0
        ):
            with patch.object(
                coordinator._sunset_boost, "calculate_boost", return_value=0
            ):
                def get_state(entity_id):
                    state = MagicMock()
                    state.state = "on"
                    state.attributes = {
                        "manual_control": False,
                        "brightness_pct": 50,
                        "color_temp_kelvin": 2700,
                    }
                    return state

                coordinator.hass.states.get = MagicMock(side_effect=get_state)
                coordinator.hass.services.async_call = AsyncMock()

                # Populate coordinator.data
                coordinator.data = await coordinator._async_update_data()

        # Initialize
        await coordinator.async_initialize()

        # Verify all timers cleared
        assert coordinator.zone_manager.is_manual_control_active("main_living") is False, (
            "Living room timer should be cleared"
        )
        assert coordinator.zone_manager.is_manual_control_active("bedroom") is False, (
            "Bedroom timer should be cleared"
        )

    @pytest.mark.asyncio
    async def test_async_initialize_sets_pause_to_false(self, coordinator):
        """async_initialize() should set global pause to False.

        REAL SCENARIO: HA restart with paused state from previous session
        EXPECTED: System starts unpaused
        """
        # Do first refresh
        with patch.object(
            coordinator._env_adapter, "calculate_boost", return_value=0
        ):
            with patch.object(
                coordinator._sunset_boost, "calculate_boost", return_value=0
            ):
                def get_state(entity_id):
                    state = MagicMock()
                    state.state = "on"
                    state.attributes = {
                        "manual_control": False,
                        "brightness_pct": 50,
                        "color_temp_kelvin": 2700,
                    }
                    return state

                coordinator.hass.states.get = MagicMock(side_effect=get_state)
                coordinator.hass.services.async_call = AsyncMock()

                # Populate coordinator.data
                coordinator.data = await coordinator._async_update_data()

        # Set paused state
        coordinator.data["global"]["paused"] = True

        # Initialize
        await coordinator.async_initialize()

        # Verify unpaused
        assert coordinator.data["global"]["paused"] is False, (
            "System should start unpaused"
        )

    @pytest.mark.asyncio
    async def test_async_initialize_triggers_environmental_calculation(self, coordinator):
        """async_initialize() should trigger initial environmental boost calculation.

        REAL SCENARIO: System startup needs initial environmental state
        EXPECTED: Environmental adapter calculates initial boost
        """
        # Do first refresh
        with patch.object(
            coordinator._env_adapter, "calculate_boost", return_value=0
        ):
            with patch.object(
                coordinator._sunset_boost, "calculate_boost", return_value=0
            ):
                def get_state(entity_id):
                    state = MagicMock()
                    state.state = "on"
                    state.attributes = {
                        "manual_control": False,
                        "brightness_pct": 50,
                        "color_temp_kelvin": 2700,
                    }
                    return state

                coordinator.hass.states.get = MagicMock(side_effect=get_state)
                coordinator.hass.services.async_call = AsyncMock()

                # Populate coordinator.data
                coordinator.data = await coordinator._async_update_data()

        # Mock environmental adapter to track calls
        with patch.object(
            coordinator._env_adapter, "calculate_boost", return_value=15
        ) as mock_calc:
            # Initialize
            await coordinator.async_initialize()

            # Verify environmental calculation triggered
            assert mock_calc.call_count >= 1, (
                "Environmental adapter should calculate boost during initialization"
            )


@pytest.mark.unit
@pytest.mark.coordinator
class TestALSwitchValidation:
    """Test AL switch entity validation - PREVENT CRASHES FROM MISCONFIGURATION.

    WHAT WE'RE TESTING:
    - Coordinator validates AL switch availability on startup (Phase 1.11)
    - Unavailable switches are logged and tracked
    - Zones with unavailable switches are skipped during updates
    - Switch health status exposed in coordinator.data

    WHY THIS MATTERS:
    - Prevents crashes from misconfigured zones
    - User-friendly degradation instead of hard failures
    - Clear visibility into switch availability issues
    """

    @pytest.fixture
    def coordinator_with_missing_switch(self, mock_hass):
        """Create coordinator with one zone having unavailable AL switch."""
        config_entry = MagicMock()
        config_entry.data = {
            "zones": [
                {
                    "id": "good_zone",
                    "zone_id": "good_zone",
                    "name": "Good Zone",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_good",
                    "lights": ["light.good_1"],
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": True,
                },
                {
                    "id": "bad_zone",
                    "zone_id": "bad_zone",
                    "name": "Bad Zone",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_missing",  # Doesn't exist
                    "lights": ["light.bad_1"],
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": True,
                },
            ],
            "environmental": {
                "lux_sensor": "sensor.outdoor_illuminance",
                "weather_entity": "weather.home",
                "enabled": True,
            },
            "global_settings": {},
        }
        config_entry.entry_id = "test_missing_switch"
        return ALPDataUpdateCoordinator(hass=mock_hass, config_entry=config_entry)

    @pytest.mark.asyncio
    async def test_async_initialize_detects_unavailable_switches(
        self, coordinator_with_missing_switch
    ):
        """async_initialize() should detect and log unavailable AL switches.

        REAL SCENARIO: Zone configured but AL switch entity doesn't exist in HA
        EXPECTED: Switch marked as unavailable, logged, stored in switch_health
        """
        # Mock states: good_zone switch exists, bad_zone switch doesn't
        def get_state(entity_id):
            if entity_id == "switch.adaptive_lighting_good":
                state = MagicMock()
                state.state = "on"
                state.attributes = {
                    "manual_control": False,
                    "brightness_pct": 50,
                    "color_temp_kelvin": 2700,
                }
                return state
            elif entity_id == "switch.adaptive_lighting_missing":
                return None  # Switch doesn't exist
            # Default for other entities
            state = MagicMock()
            state.state = "on"
            state.attributes = {}
            return state

        coordinator_with_missing_switch.hass.states.get = MagicMock(side_effect=get_state)
        coordinator_with_missing_switch.hass.services.async_call = AsyncMock()

        # Do first refresh to populate data
        with patch.object(
            coordinator_with_missing_switch._env_adapter, "calculate_boost", return_value=0
        ):
            with patch.object(
                coordinator_with_missing_switch._sunset_boost, "calculate_boost", return_value=0
            ):
                coordinator_with_missing_switch.data = (
                    await coordinator_with_missing_switch._async_update_data()
                )

        # Initialize (this should validate switches)
        await coordinator_with_missing_switch.async_initialize()

        # Verify switch health status
        switch_health = coordinator_with_missing_switch.data["global"]["switch_health"]

        assert switch_health["total_switches"] == 2, "Should have 2 zones"
        assert switch_health["available_switches"] == 1, "Only 1 switch available"
        assert switch_health["status"] == "Degraded", "Status should be Degraded"
        assert "switch.adaptive_lighting_missing" in switch_health["unavailable"], (
            "Missing switch should be in unavailable list"
        )
        assert "switch.adaptive_lighting_good" in switch_health["available_switch_ids"], (
            "Good switch should be in available list"
        )

    @pytest.mark.asyncio
    async def test_async_update_data_skips_zones_with_unavailable_switches(
        self, coordinator_with_missing_switch
    ):
        """Zones with unavailable switches should be skipped during updates.

        REAL SCENARIO: Update cycle encounters zone with unavailable switch
        EXPECTED: Zone skipped, no service calls, no crashes
        """
        # Mock states: good_zone switch exists, bad_zone switch doesn't
        def get_state(entity_id):
            if entity_id == "switch.adaptive_lighting_good":
                state = MagicMock()
                state.state = "on"
                state.attributes = {
                    "manual_control": False,
                    "brightness_pct": 50,
                    "color_temp_kelvin": 2700,
                }
                return state
            elif entity_id == "switch.adaptive_lighting_missing":
                return None
            # Default for other entities
            state = MagicMock()
            state.state = "on"
            state.attributes = {}
            return state

        coordinator_with_missing_switch.hass.states.get = MagicMock(side_effect=get_state)

        service_calls = []

        async def capture_service_call(domain, service, data, **kwargs):
            service_calls.append((domain, service, data))

        coordinator_with_missing_switch.hass.services.async_call = AsyncMock(
            side_effect=capture_service_call
        )

        # Do first refresh and initialize
        with patch.object(
            coordinator_with_missing_switch._env_adapter, "calculate_boost", return_value=0
        ):
            with patch.object(
                coordinator_with_missing_switch._sunset_boost, "calculate_boost", return_value=0
            ):
                coordinator_with_missing_switch.data = (
                    await coordinator_with_missing_switch._async_update_data()
                )
                await coordinator_with_missing_switch.async_initialize()

        # Clear service calls from initialization
        service_calls.clear()

        # Run update again with environmental boost
        with patch.object(
            coordinator_with_missing_switch._env_adapter, "calculate_boost", return_value=20
        ):
            with patch.object(
                coordinator_with_missing_switch._sunset_boost, "calculate_boost", return_value=0
            ):
                await coordinator_with_missing_switch._async_update_data()

        # Check that bad_zone did NOT get any service calls
        bad_zone_calls = [
            c
            for c in service_calls
            if c[2].get("entity_id") == "switch.adaptive_lighting_missing"
        ]
        assert len(bad_zone_calls) == 0, (
            f"bad_zone has unavailable switch but received {len(bad_zone_calls)} service calls. "
            f"Zones with unavailable switches should be COMPLETELY skipped. Calls: {bad_zone_calls}"
        )

        # Check that good_zone DID get service call
        good_zone_calls = [
            c
            for c in service_calls
            if c[2].get("entity_id") == "switch.adaptive_lighting_good"
        ]
        assert len(good_zone_calls) > 0, (
            "good_zone should receive adjustments when its switch is available"
        )

    @pytest.mark.asyncio
    async def test_switch_missing_manual_control_attribute(self, mock_hass):
        """Switch without manual_control attribute should be flagged as problematic.

        REAL SCENARIO: User configured wrong switch entity (not from AL integration)
        EXPECTED: Switch flagged in unavailable list with reason
        """
        config_entry = MagicMock()
        config_entry.data = {
            "zones": [
                {
                    "id": "wrong_switch_zone",
                    "zone_id": "wrong_switch_zone",
                    "name": "Wrong Switch Zone",
                    "adaptive_lighting_switch": "switch.some_other_switch",  # Not an AL switch
                    "lights": ["light.test"],
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": True,
                }
            ],
            "environmental": {
                "lux_sensor": "sensor.outdoor_illuminance",
                "weather_entity": "weather.home",
                "enabled": True,
            },
            "global_settings": {},
        }
        config_entry.entry_id = "test_wrong_switch"
        coordinator = ALPDataUpdateCoordinator(hass=mock_hass, config_entry=config_entry)

        # Mock switch exists but doesn't have manual_control attribute
        def get_state(entity_id):
            if entity_id == "switch.some_other_switch":
                state = MagicMock()
                state.state = "on"
                state.attributes = {
                    "brightness": 50,  # Different attributes, not AL switch
                }
                return state
            state = MagicMock()
            state.state = "on"
            state.attributes = {}
            return state

        coordinator.hass.states.get = MagicMock(side_effect=get_state)
        coordinator.hass.services.async_call = AsyncMock()

        # Do first refresh and initialize
        with patch.object(coordinator._env_adapter, "calculate_boost", return_value=0):
            with patch.object(coordinator._sunset_boost, "calculate_boost", return_value=0):
                coordinator.data = await coordinator._async_update_data()
                await coordinator.async_initialize()

        # Verify switch flagged with reason
        switch_health = coordinator.data["global"]["switch_health"]
        assert switch_health["available_switches"] == 0, "No switches should be available"
        assert any(
            "missing manual_control" in item for item in switch_health["unavailable"]
        ), "Switch should be flagged as missing manual_control attribute"


@pytest.mark.unit
@pytest.mark.coordinator
class TestLightGroupValidation:
    """Test light group validation - ENSURE LIGHTS ARE CONFIGURED CORRECTLY.

    WHAT WE'RE TESTING:
    - Coordinator validates light entities on startup (Phase 1.12)
    - Unavailable lights are detected and tracked
    - Multi-zone lights are detected and warned
    - Light health status exposed in coordinator.data

    WHY THIS MATTERS:
    - Prevents silent failures (lights configured but don't exist)
    - Warns about multi-zone conflicts (confusing behavior)
    - Provides visibility into light availability
    - Graceful degradation for missing lights
    """

    @pytest.fixture
    def coordinator_with_lights(self, mock_hass):
        """Create coordinator with zones containing various light configurations."""
        config_entry = MagicMock()
        config_entry.data = {
            "zones": [
                {
                    "id": "bedroom",
                    "zone_id": "bedroom",
                    "name": "Bedroom",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_bedroom",
                    "lights": [
                        "light.bedroom_main",
                        "light.bedroom_reading",
                        "light.bedroom_closet",
                    ],
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": True,
                },
                {
                    "id": "living_room",
                    "zone_id": "living_room",
                    "name": "Living Room",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_living",
                    "lights": [
                        "light.living_ceiling",
                        "light.living_lamp_unavailable",  # This one doesn't exist
                    ],
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": True,
                },
            ],
            "environmental": {
                "lux_sensor": "sensor.outdoor_illuminance",
                "weather_entity": "weather.home",
                "enabled": True,
            },
            "global_settings": {},
        }
        config_entry.entry_id = "test_lights"
        return ALPDataUpdateCoordinator(hass=mock_hass, config_entry=config_entry)

    @pytest.mark.asyncio
    async def test_zone_with_all_valid_lights(self, coordinator_with_lights):
        """Zone with all valid lights should pass validation.

        REAL SCENARIO: Bedroom with 3 lights, all configured correctly
        EXPECTED: All 3 lights validated, status OK
        """
        # Mock states: bedroom lights all exist
        def get_state(entity_id):
            if entity_id.startswith("light.bedroom"):
                state = MagicMock()
                state.state = "on"
                state.attributes = {}
                return state
            elif entity_id == "light.living_ceiling":
                state = MagicMock()
                state.state = "on"
                state.attributes = {}
                return state
            elif entity_id == "light.living_lamp_unavailable":
                return None  # Unavailable
            elif entity_id.startswith("switch.adaptive_lighting"):
                state = MagicMock()
                state.state = "on"
                state.attributes = {"manual_control": False}
                return state
            # Default
            state = MagicMock()
            state.state = "on"
            state.attributes = {}
            return state

        coordinator_with_lights.hass.states.get = MagicMock(side_effect=get_state)
        coordinator_with_lights.hass.services.async_call = AsyncMock()

        # Do first refresh and initialize
        with patch.object(
            coordinator_with_lights._env_adapter, "calculate_boost", return_value=0
        ):
            with patch.object(
                coordinator_with_lights._sunset_boost, "calculate_boost", return_value=0
            ):
                coordinator_with_lights.data = (
                    await coordinator_with_lights._async_update_data()
                )
                await coordinator_with_lights.async_initialize()

        # Verify light health
        light_health = coordinator_with_lights.data["global"]["light_health"]

        # Total: 3 bedroom + 2 living = 5 lights
        assert light_health["total_lights"] == 5, "Should have 5 total lights"
        # Available: 3 bedroom + 1 living = 4 lights
        assert light_health["available_lights"] == 4, "Should have 4 available lights"
        # Unavailable: 1 living lamp
        assert "light.living_lamp_unavailable" in light_health["unavailable_lights"], (
            "Should flag unavailable light"
        )

    @pytest.mark.asyncio
    async def test_light_in_multiple_zones_warning(self, mock_hass):
        """Light in multiple zones should trigger warning but still work.

        REAL SCENARIO: Living room floor lamp controlled by two AL switches
        EXPECTED: Warning logged, status "Warning", light tracked in multi_zone_lights
        """
        config_entry = MagicMock()
        config_entry.data = {
            "zones": [
                {
                    "id": "zone_a",
                    "zone_id": "zone_a",
                    "name": "Zone A",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_a",
                    "lights": ["light.shared_lamp", "light.zone_a_ceiling"],
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": True,
                },
                {
                    "id": "zone_b",
                    "zone_id": "zone_b",
                    "name": "Zone B",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_b",
                    "lights": ["light.shared_lamp", "light.zone_b_floor"],  # Same lamp!
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": True,
                },
            ],
            "environmental": {
                "lux_sensor": "sensor.outdoor_illuminance",
                "weather_entity": "weather.home",
                "enabled": True,
            },
            "global_settings": {},
        }
        config_entry.entry_id = "test_multi_zone"
        coordinator = ALPDataUpdateCoordinator(hass=mock_hass, config_entry=config_entry)

        # Mock all lights exist
        def get_state(entity_id):
            state = MagicMock()
            state.state = "on"
            if entity_id.startswith("switch.adaptive_lighting"):
                state.attributes = {"manual_control": False}
            else:
                state.attributes = {}
            return state

        coordinator.hass.states.get = MagicMock(side_effect=get_state)
        coordinator.hass.services.async_call = AsyncMock()

        # Do first refresh and initialize
        with patch.object(coordinator._env_adapter, "calculate_boost", return_value=0):
            with patch.object(coordinator._sunset_boost, "calculate_boost", return_value=0):
                coordinator.data = await coordinator._async_update_data()
                await coordinator.async_initialize()

        # Verify multi-zone detection
        light_health = coordinator.data["global"]["light_health"]

        assert light_health["status"] == "Warning", (
            "Status should be Warning when multi-zone lights detected"
        )
        assert "light.shared_lamp" in light_health["multi_zone_lights"], (
            "Shared lamp should be flagged as multi-zone"
        )
        assert light_health["multi_zone_lights"]["light.shared_lamp"] == [
            "zone_a",
            "zone_b",
        ], "Should track which zones contain the shared lamp"

    @pytest.mark.asyncio
    async def test_zone_with_no_available_lights(self, mock_hass):
        """Zone where all lights are unavailable should be flagged.

        REAL SCENARIO: Zone configured but all light entities removed/renamed
        EXPECTED: Zone flagged, warning logged, zone will not control anything
        """
        config_entry = MagicMock()
        config_entry.data = {
            "zones": [
                {
                    "id": "broken_zone",
                    "zone_id": "broken_zone",
                    "name": "Broken Zone",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_broken",
                    "lights": [
                        "light.removed_1",
                        "light.removed_2",
                        "light.removed_3",
                    ],
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": True,
                }
            ],
            "environmental": {
                "lux_sensor": "sensor.outdoor_illuminance",
                "weather_entity": "weather.home",
                "enabled": True,
            },
            "global_settings": {},
        }
        config_entry.entry_id = "test_no_lights"
        coordinator = ALPDataUpdateCoordinator(hass=mock_hass, config_entry=config_entry)

        # Mock: switch exists, all lights don't
        def get_state(entity_id):
            if entity_id == "switch.adaptive_lighting_broken":
                state = MagicMock()
                state.state = "on"
                state.attributes = {"manual_control": False}
                return state
            elif entity_id.startswith("light.removed"):
                return None  # All lights unavailable
            # Default
            state = MagicMock()
            state.state = "on"
            state.attributes = {}
            return state

        coordinator.hass.states.get = MagicMock(side_effect=get_state)
        coordinator.hass.services.async_call = AsyncMock()

        # Do first refresh and initialize
        with patch.object(coordinator._env_adapter, "calculate_boost", return_value=0):
            with patch.object(coordinator._sunset_boost, "calculate_boost", return_value=0):
                coordinator.data = await coordinator._async_update_data()
                await coordinator.async_initialize()

        # Verify degraded status
        light_health = coordinator.data["global"]["light_health"]

        assert light_health["status"] == "Degraded", (
            "Status should be Degraded when lights unavailable"
        )
        assert light_health["available_lights"] == 0, "No lights should be available"
        assert len(light_health["unavailable_lights"]) == 3, (
            "All 3 lights should be flagged as unavailable"
        )

    @pytest.mark.asyncio
    async def test_zone_without_lights_configured(self, mock_hass):
        """Zone with no lights list should be flagged.

        REAL SCENARIO: Zone created but lights array is empty
        EXPECTED: Zone flagged in zones_without_lights, warning logged
        """
        config_entry = MagicMock()
        config_entry.data = {
            "zones": [
                {
                    "id": "empty_zone",
                    "zone_id": "empty_zone",
                    "name": "Empty Zone",
                    "adaptive_lighting_switch": "switch.adaptive_lighting_empty",
                    "lights": [],  # No lights!
                    "brightness_min": 45,
                    "brightness_max": 100,
                    "environmental_enabled": True,
                    "enabled": True,
                }
            ],
            "environmental": {
                "lux_sensor": "sensor.outdoor_illuminance",
                "weather_entity": "weather.home",
                "enabled": True,
            },
            "global_settings": {},
        }
        config_entry.entry_id = "test_empty"
        coordinator = ALPDataUpdateCoordinator(hass=mock_hass, config_entry=config_entry)

        # Mock switch exists
        def get_state(entity_id):
            if entity_id == "switch.adaptive_lighting_empty":
                state = MagicMock()
                state.state = "on"
                state.attributes = {"manual_control": False}
                return state
            state = MagicMock()
            state.state = "on"
            state.attributes = {}
            return state

        coordinator.hass.states.get = MagicMock(side_effect=get_state)
        coordinator.hass.services.async_call = AsyncMock()

        # Do first refresh and initialize
        with patch.object(coordinator._env_adapter, "calculate_boost", return_value=0):
            with patch.object(coordinator._sunset_boost, "calculate_boost", return_value=0):
                coordinator.data = await coordinator._async_update_data()
                await coordinator.async_initialize()

        # Verify empty zone detection
        light_health = coordinator.data["global"]["light_health"]

        assert "empty_zone" in light_health["zones_without_lights"], (
            "Empty zone should be flagged"
        )
        assert light_health["total_lights"] == 0, "Should have 0 total lights"
