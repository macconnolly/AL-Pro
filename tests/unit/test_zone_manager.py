"""Tests for zone manager smart timeout and persistence.

THE CRITICAL STATE MANAGEMENT: Does zone manager handle timers correctly?
This tests REAL USER SCENARIOS where state persistence and smart timeouts matter.

WHAT WE'RE TESTING:
1. Smart timeout calculation based on sun elevation and environmental boost
2. Timer expiration detection and automatic zone reactivation
3. State persistence across restarts (save/restore)
4. Multiple simultaneous zone timers
5. Timer edge cases (expired during downtime, cancel, extend)

WHY THIS MATTERS:
- Zone manager is 20% tested (CRITICAL GAP)
- Users expect timers to survive HA restarts
- Smart timeout should give longer override at sunset (when system is brightest)
- Expired timers must transition zones back to adaptive control
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from custom_components.adaptive_lighting_pro.features.manual_control import (
    ManualControlDetector,
)
from custom_components.adaptive_lighting_pro.features.zone_manager import (
    ZoneManager,
    ZoneState,
)


@pytest.mark.unit
@pytest.mark.zone_manager
class TestSmartTimeout:
    """Test smart timeout calculation - adapts to conditions."""

    @pytest.fixture
    def zone_manager_with_manual_detector(self, mock_hass, mock_config_entry):
        """Create zone manager with manual detector for smart timeout.

        Note: ManualControlDetector uses hardcoded logic:
        - Base: 1800s (30 min)
        - Night (sun < -6°): 1.5x
        - Dim (env > 10%): 1.3x
        - Max: 7200s (2 hr)
        """
        manual_detector = ManualControlDetector(mock_hass)
        return ZoneManager(
            hass=mock_hass,
            config_entry=mock_config_entry,
            manual_detector=manual_detector,
        )

    @pytest.mark.asyncio
    async def test_smart_timeout_at_night_extends_duration(
        self, zone_manager_with_manual_detector
    ):
        """Smart timeout at night should extend duration.

        REAL SCENARIO: User manually dims lights at 9 PM (sun well below horizon)
        REASON: System uses night time, user wants longer override
        USER INTENT: Override should last longer at night
        EXPECTED: Base 1800s * 1.5 (night) = 2700s
        """
        await zone_manager_with_manual_detector.async_start_manual_timer(
            zone_id="main_living",
            duration=None,  # Use smart calculation
            sun_elevation=-10.0,  # Night (below -6°)
            env_boost=0,  # No environmental boost
        )

        state = zone_manager_with_manual_detector.get_zone_state("main_living")
        assert state.manual_control_active is True
        # Smart timeout: base(1800) * 1.5 (night) = 2700
        assert state.timer_duration == 2700, (
            f"Expected 2700s smart timeout at night, got {state.timer_duration}s. "
            f"Night override should be 1.5x base (1800 * 1.5 = 2700)."
        )

    @pytest.mark.asyncio
    async def test_smart_timeout_at_noon_uses_base_duration(
        self, zone_manager_with_manual_detector
    ):
        """Smart timeout at noon should use base duration (no multipliers).

        REAL SCENARIO: User manually adjusts at noon (sun high)
        REASON: System not compensating much, user just fine-tuning
        EXPECTED: Base 1800s duration (no multiplier)
        """
        await zone_manager_with_manual_detector.async_start_manual_timer(
            zone_id="main_living",
            duration=None,
            sun_elevation=60.0,  # High sun (no night multiplier)
            env_boost=0,  # No dim multiplier
        )

        state = zone_manager_with_manual_detector.get_zone_state("main_living")
        # Smart timeout: base(1800) * 1.0 = 1800
        assert state.timer_duration == 1800, (
            f"Expected 1800s (30min) base timeout at noon, got {state.timer_duration}s"
        )

    @pytest.mark.asyncio
    async def test_smart_timeout_with_environmental_boost_extends_more(
        self, zone_manager_with_manual_detector
    ):
        """Environmental boost + night = maximum smart timeout.

        REAL SCENARIO: User dims at night on foggy day
        CONDITIONS: Night (1.5x) + environmental boost >10% (1.3x)
        USER INTENT: Fighting against environmental boost at night
        EXPECTED: base(1800) * 1.5 (night) * 1.3 (env) = 3510s
        """
        await zone_manager_with_manual_detector.async_start_manual_timer(
            zone_id="main_living",
            duration=None,
            sun_elevation=-10.0,  # Night
            env_boost=15,  # Foggy day boost (>10%)
        )

        state = zone_manager_with_manual_detector.get_zone_state("main_living")
        # Smart timeout: base * night * dim = 1800 * 1.5 * 1.3 = 3510
        assert state.timer_duration == 3510, (
            f"Expected 3510s smart timeout for foggy night, got {state.timer_duration}s. "
            f"Maximum extension when user overrides environmental boost at night (1800 * 1.5 * 1.3)."
        )

    @pytest.mark.asyncio
    async def test_manual_duration_override_ignores_smart_calculation(
        self, zone_manager_with_manual_detector
    ):
        """Explicit duration should bypass smart timeout.

        REAL SCENARIO: Service call with specific duration
        EXPECTED: Use exact duration, ignore sun/env conditions
        """
        await zone_manager_with_manual_detector.async_start_manual_timer(
            zone_id="main_living",
            duration=600,  # Explicit 10 minutes
            sun_elevation=-10.0,  # Would normally extend
            env_boost=25,  # Would normally extend
        )

        state = zone_manager_with_manual_detector.get_zone_state("main_living")
        assert state.timer_duration == 600, (
            f"Expected exact duration 600s when specified, got {state.timer_duration}s. "
            f"Explicit duration should ignore smart calculation."
        )


@pytest.mark.unit
@pytest.mark.zone_manager
class TestTimerExpiration:
    """Test timer expiration and zone reactivation."""

    @pytest.fixture
    def zone_manager(self, mock_hass, mock_config_entry):
        """Create basic zone manager."""
        return ZoneManager(hass=mock_hass, config_entry=mock_config_entry)

    @pytest.mark.asyncio
    async def test_expired_timer_deactivates_manual_control(self, zone_manager):
        """Expired timer should automatically deactivate manual control.

        REAL SCENARIO: User presses dimmer at 6 PM, timer set for 1 hour
        TIME: Now 7:01 PM (timer expired 1 minute ago)
        EXPECTED: Manual control deactivated, zone returns to adaptive
        """
        from datetime import UTC, datetime, timedelta

        # Mock time to control expiration
        with patch(
            "custom_components.adaptive_lighting_pro.features.zone_manager.datetime"
        ) as mock_dt:
            start_time = datetime(2025, 1, 15, 18, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = start_time
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Start timer that expires in 1 second
            await zone_manager.async_start_manual_timer(
                zone_id="main_living",
                duration=1,
            )

            # Verify timer started
            assert zone_manager.is_manual_control_active("main_living") is True

            # Advance time past expiration
            mock_dt.now.return_value = start_time + timedelta(seconds=2)

            # Check for expired timers
            expired = await zone_manager.async_update_timers()

            assert "main_living" in expired, (
                f"Timer should have expired. Got expired zones: {expired}"
            )
            assert zone_manager.is_manual_control_active("main_living") is False, (
                "Manual control should be deactivated after timer expires"
            )

    @pytest.mark.asyncio
    async def test_multiple_zones_different_expiry_times(self, zone_manager):
        """Multiple zones with different timers should expire independently.

        REAL SCENARIO: User adjusts living room (5s timer) and bedroom (10s timer)
        EXPECTED: Living room expires first, bedroom continues
        """
        await zone_manager.async_start_manual_timer("main_living", duration=1)
        await zone_manager.async_start_manual_timer("bedroom", duration=10)

        # Verify both active
        assert zone_manager.is_manual_control_active("main_living") is True
        assert zone_manager.is_manual_control_active("bedroom") is True

        # Wait for first timer
        import asyncio

        await asyncio.sleep(1.1)
        expired = await zone_manager.async_update_timers()

        # Only main_living should expire
        assert "main_living" in expired
        assert "bedroom" not in expired
        assert zone_manager.is_manual_control_active("main_living") is False
        assert zone_manager.is_manual_control_active("bedroom") is True

    @pytest.mark.asyncio
    async def test_get_timer_remaining_accurate(self, zone_manager):
        """Timer remaining should count down accurately.

        REAL SCENARIO: User wants to know how long until adaptive resumes
        EXPECTED: Accurate countdown in seconds
        """
        await zone_manager.async_start_manual_timer("main_living", duration=10)

        # Immediately after start
        remaining = zone_manager.get_timer_remaining("main_living")
        assert 9 <= remaining <= 10, (
            f"Expected 9-10s remaining immediately after start, got {remaining}s"
        )

        # After some time
        import asyncio

        await asyncio.sleep(5)
        remaining = zone_manager.get_timer_remaining("main_living")
        assert 4 <= remaining <= 6, (
            f"Expected ~5s remaining after 5s delay, got {remaining}s"
        )

    @pytest.mark.asyncio
    async def test_cancel_timer_clears_manual_control(self, zone_manager):
        """Canceling timer should immediately clear manual control.

        REAL SCENARIO: User presses "resume adaptive" button
        EXPECTED: Timer cancelled, zone returns to adaptive immediately
        """
        await zone_manager.async_start_manual_timer("main_living", duration=3600)

        # Verify active
        assert zone_manager.is_manual_control_active("main_living") is True

        # Cancel
        await zone_manager.async_cancel_timer("main_living")

        # Verify cleared
        assert zone_manager.is_manual_control_active("main_living") is False
        assert zone_manager.get_timer_remaining("main_living") == 0


@pytest.mark.unit
@pytest.mark.zone_manager
class TestStatePersistence:
    """Test state persistence across restarts - THE CRITICAL FEATURE."""

    @pytest.fixture
    def zone_manager(self, mock_hass, mock_config_entry):
        """Create zone manager."""
        return ZoneManager(hass=mock_hass, config_entry=mock_config_entry)

    @pytest.mark.asyncio
    async def test_active_timer_persists_across_restart(
        self, mock_hass, mock_config_entry
    ):
        """Active timer should survive HA restart.

        REAL SCENARIO: User sets 1hr override at 6 PM, HA restarts at 6:30 PM
        EXPECTED: Timer continues, expires at 7 PM as originally scheduled
        """
        # Create manager and start timer
        manager1 = ZoneManager(hass=mock_hass, config_entry=mock_config_entry)
        await manager1.async_start_manual_timer("main_living", duration=3600)

        state_before = manager1.get_zone_state("main_living")
        assert state_before.manual_control_active is True
        original_expiry = state_before.timer_expiry

        # Simulate restart: create new manager instance with same hass.data
        manager2 = ZoneManager(hass=mock_hass, config_entry=mock_config_entry)

        state_after = manager2.get_zone_state("main_living")
        assert state_after.manual_control_active is True, (
            "Manual control should persist after restart"
        )
        assert state_after.timer_expiry == original_expiry, (
            f"Timer expiry should be preserved: before={original_expiry}, after={state_after.timer_expiry}"
        )

    @pytest.mark.asyncio
    async def test_timer_expired_during_downtime_clears_on_restore(
        self, mock_hass, mock_config_entry
    ):
        """Timer that expired during downtime should clear on restart.

        REAL SCENARIO: User sets 1s override, HA down for 10s, then restarts
        EXPECTED: Timer recognized as expired, manual control cleared
        """
        # Start timer
        manager1 = ZoneManager(hass=mock_hass, config_entry=mock_config_entry)
        await manager1.async_start_manual_timer("main_living", duration=1)

        # Wait for timer to expire while "down"
        import asyncio

        await asyncio.sleep(2)

        # Restart: new manager sees expired timer
        manager2 = ZoneManager(hass=mock_hass, config_entry=mock_config_entry)

        state = manager2.get_zone_state("main_living")
        assert state.manual_control_active is False, (
            "Manual control should be cleared if timer expired during downtime"
        )
        assert state.timer_expiry is None
        assert state.timer_duration == 0

    @pytest.mark.asyncio
    async def test_multiple_zones_persist_independently(
        self, mock_hass, mock_config_entry
    ):
        """Multiple zone timers should persist independently.

        REAL SCENARIO: Living room (1hr) and bedroom (30min) both have active timers
        EXPECTED: Both persist with correct individual expiry times
        """
        manager1 = ZoneManager(hass=mock_hass, config_entry=mock_config_entry)
        await manager1.async_start_manual_timer("main_living", duration=3600)
        await manager1.async_start_manual_timer("bedroom", duration=1800)

        living_expiry = manager1.get_zone_state("main_living").timer_expiry
        bedroom_expiry = manager1.get_zone_state("bedroom").timer_expiry

        # Restart
        manager2 = ZoneManager(hass=mock_hass, config_entry=mock_config_entry)

        # Verify both restored correctly
        living_state = manager2.get_zone_state("main_living")
        bedroom_state = manager2.get_zone_state("bedroom")

        assert living_state.manual_control_active is True
        assert bedroom_state.manual_control_active is True
        assert living_state.timer_expiry == living_expiry
        assert bedroom_state.timer_expiry == bedroom_expiry
        assert living_state.timer_duration == 3600
        assert bedroom_state.timer_duration == 1800


@pytest.mark.unit
@pytest.mark.zone_manager
class TestZoneStateDataStructure:
    """Test ZoneState data structure serialization/deserialization."""

    def test_zone_state_to_dict_serializable(self):
        """ZoneState should serialize to JSON-compatible dict.

        REAL SCENARIO: Saving state to hass.data for persistence
        EXPECTED: All fields converted to JSON-serializable types
        """
        now = datetime.now(UTC)
        expiry = now + timedelta(hours=1)

        state = ZoneState(
            zone_id="main_living",
            manual_control_active=True,
            timer_expiry=expiry,
            timer_duration=3600,
            last_manual_trigger=now,
        )

        data = state.to_dict()

        # Verify structure
        assert data["zone_id"] == "main_living"
        assert data["manual_control_active"] is True
        assert isinstance(data["timer_expiry"], str)  # ISO format string
        assert data["timer_duration"] == 3600
        assert isinstance(data["last_manual_trigger"], str)

    def test_zone_state_from_dict_parses_correctly(self):
        """ZoneState should deserialize from dict with timezone handling.

        REAL SCENARIO: Restoring state from persisted data
        EXPECTED: Datetimes parsed as timezone-aware UTC
        """
        now = datetime.now(UTC)
        expiry = now + timedelta(hours=1)

        data = {
            "zone_id": "bedroom",
            "manual_control_active": True,
            "timer_expiry": expiry.isoformat(),
            "timer_duration": 1800,
            "last_manual_trigger": now.isoformat(),
        }

        state = ZoneState.from_dict(data)

        assert state.zone_id == "bedroom"
        assert state.manual_control_active is True
        assert state.timer_expiry.tzinfo is not None, "Expiry should be timezone-aware"
        assert abs((state.timer_expiry - expiry).total_seconds()) < 1
        assert state.timer_duration == 1800
        assert state.last_manual_trigger.tzinfo is not None

    def test_zone_state_handles_naive_datetime_in_dict(self):
        """Should add timezone to naive datetimes from old persisted data.

        REAL SCENARIO: Restoring from data saved before timezone fix
        EXPECTED: Naive datetime converted to UTC
        """
        naive_time = datetime(2025, 1, 15, 18, 0, 0)  # No tzinfo

        data = {
            "zone_id": "kitchen",
            "manual_control_active": False,
            "timer_expiry": naive_time.isoformat(),
            "timer_duration": 0,
            "last_manual_trigger": None,
        }

        state = ZoneState.from_dict(data)

        assert state.timer_expiry.tzinfo is not None, (
            "Naive datetime should be converted to timezone-aware"
        )
        assert state.timer_expiry.tzinfo == UTC
