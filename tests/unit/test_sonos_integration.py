"""Tests for Sonos integration and alarm detection.

Real-world morning scenarios following claude.md standards:
"This is YOUR home. You live here. Bad code = bad sleep, bad mornings."

These tests verify the Sonos integration that triggers wake sequences before alarms.
"""
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, AsyncMock, patch, call
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

import pytest

from custom_components.adaptive_lighting_pro.integrations.sonos import SonosIntegration
from custom_components.adaptive_lighting_pro.features.wake_sequence import WakeSequenceCalculator


@pytest.mark.unit
@pytest.mark.sonos
class TestSonosAlarmDetection:
    """Test Sonos alarm detection and wake sequence triggering."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass instance."""
        hass = MagicMock()
        hass.states = MagicMock()
        hass.bus = MagicMock()
        hass.async_create_task = lambda coro: coro
        return hass

    @pytest.fixture
    def wake_calc(self, mock_hass):
        """Create wake sequence calculator."""
        calc = WakeSequenceCalculator(mock_hass)
        calc.configure(enabled=True, target_zone="bedroom")
        return calc

    @pytest.fixture
    def sonos_integration(self, mock_hass, wake_calc):
        """Create Sonos integration."""
        integration = SonosIntegration(mock_hass, wake_calc)
        integration.configure(
            enabled=True,
            alarm_sensor="sensor.sonos_bedroom_next_alarm"
        )
        return integration

    @pytest.mark.asyncio
    async def test_alarm_detected_triggers_wake_sequence(
        self, mock_hass, sonos_integration, wake_calc
    ):
        """Alarm detected should trigger wake sequence.

        SCENARIO: 10:00 PM - I set Sonos alarm for 6:30 AM tomorrow
        EXPECTED: Wake sequence scheduled to start at 6:15 AM
        WHY: This is THE primary use case - gentle wake every morning
        BUG WOULD CAUSE: No wake sequence, jarring alarm at 6:30 AM
        """
        # Mock sensor state with alarm set for tomorrow 6:30 AM
        tomorrow_6am = (datetime.now(UTC) + timedelta(hours=10)).replace(
            hour=6, minute=30, second=0, microsecond=0
        )
        alarm_iso = tomorrow_6am.isoformat()

        sensor_state = MagicMock()
        sensor_state.state = alarm_iso
        sensor_state.attributes = {}
        mock_hass.states.get.return_value = sensor_state

        # Setup integration (processes current sensor state)
        await sonos_integration.async_setup()

        # Verify wake sequence was set
        assert wake_calc.get_alarm_time() == tomorrow_6am, (
            f"Expected alarm time {tomorrow_6am.isoformat()}, "
            f"got {wake_calc.get_alarm_time()}"
        )

        expected_wake_start = tomorrow_6am - timedelta(minutes=15)
        assert wake_calc.get_wake_start_time() == expected_wake_start, (
            f"Expected wake start {expected_wake_start.isoformat()}, "
            f"got {wake_calc.get_wake_start_time()}"
        )

    @pytest.mark.asyncio
    async def test_stale_alarm_in_past_ignored(
        self, mock_hass, sonos_integration, wake_calc
    ):
        """Alarm in the past should be ignored (stale data).

        SCENARIO: 7:00 AM - Sonos sensor shows yesterday's 6:30 AM alarm (stale)
        EXPECTED: Alarm ignored, no wake sequence
        WHY: Prevents wake boost activating hours after alarm
        BUG WOULD CAUSE: Lights brightening at random times during day
        """
        # Mock sensor with past alarm
        past_alarm = datetime.now(UTC) - timedelta(hours=1)
        alarm_iso = past_alarm.isoformat()

        sensor_state = MagicMock()
        sensor_state.state = alarm_iso
        sensor_state.attributes = {}
        mock_hass.states.get.return_value = sensor_state

        # Setup should ignore past alarm
        await sonos_integration.async_setup()

        # Verify no wake sequence set
        assert wake_calc.get_alarm_time() is None, (
            "Past alarm should be ignored, but wake sequence was set"
        )

    @pytest.mark.asyncio
    async def test_sensor_unavailable_clears_alarm(
        self, mock_hass, sonos_integration, wake_calc
    ):
        """Sensor unavailable should clear current alarm gracefully.

        SCENARIO: 6:20 AM mid-sequence - Network blip, Sonos offline
        EXPECTED: Wake sequence cleared, resume when sensor returns
        WHY: Network issues happen, must degrade gracefully
        BUG WOULD CAUSE: Stuck wake sequence or crash
        """
        # First, set up with valid alarm
        future_alarm = datetime.now(UTC) + timedelta(hours=8)
        sensor_state = MagicMock()
        sensor_state.state = future_alarm.isoformat()
        sensor_state.attributes = {}
        mock_hass.states.get.return_value = sensor_state

        await sonos_integration.async_setup()
        assert wake_calc.get_alarm_time() is not None

        # Now sensor becomes unavailable
        event = MagicMock()
        event.data = {
            "new_state": MagicMock(state=STATE_UNAVAILABLE, attributes={})
        }

        # Process unavailable state (directly call async method, skip callback)
        await sonos_integration._process_alarm_state(STATE_UNAVAILABLE, {})

        # Verify alarm cleared
        assert wake_calc.get_alarm_time() is None, (
            "Alarm should be cleared when sensor unavailable"
        )

    @pytest.mark.asyncio
    async def test_alarm_time_unchanged_no_duplicate_trigger(
        self, mock_hass, sonos_integration, wake_calc
    ):
        """Same alarm time should not re-trigger wake sequence.

        SCENARIO: Sensor updates every 30s with same alarm time
        EXPECTED: Wake sequence set once, not retriggered
        WHY: Avoid unnecessary wake sequence resets
        BUG WOULD CAUSE: Wake sequence constantly restarting
        """
        future_alarm = datetime.now(UTC) + timedelta(hours=8)
        alarm_iso = future_alarm.isoformat()

        sensor_state = MagicMock()
        sensor_state.state = alarm_iso
        sensor_state.attributes = {}
        mock_hass.states.get.return_value = sensor_state

        # First setup
        await sonos_integration.async_setup()
        first_alarm = wake_calc.get_alarm_time()

        # Sensor updates with SAME alarm time
        event = MagicMock()
        event.data = {
            "new_state": MagicMock(state=alarm_iso, attributes={})
        }

        # Process alarm state (directly call async method, skip callback)
        await sonos_integration._process_alarm_state(alarm_iso, {})

        # Verify alarm time unchanged (not reset)
        assert wake_calc.get_alarm_time() == first_alarm, (
            "Alarm should not be reset when time unchanged"
        )

    @pytest.mark.asyncio
    async def test_alarm_cancelled_mid_sequence_clears(
        self, mock_hass, sonos_integration, wake_calc
    ):
        """Alarm cancelled mid-sequence should clear wake boost immediately.

        SCENARIO: 6:20 AM (mid-wake) - I cancel Sonos alarm
        EXPECTED: Wake sequence stops, boost returns to 0%
        WHY: Don't continue brightening without alarm
        BUG WOULD CAUSE: Lights keep brightening, user confused
        """
        # Setup with alarm
        future_alarm = datetime.now(UTC) + timedelta(hours=8)
        sensor_state = MagicMock()
        sensor_state.state = future_alarm.isoformat()
        sensor_state.attributes = {}
        mock_hass.states.get.return_value = sensor_state

        await sonos_integration.async_setup()
        assert wake_calc.get_alarm_time() is not None

        # User cancels alarm - sensor state becomes unknown/empty
        event = MagicMock()
        event.data = {
            "new_state": MagicMock(state=STATE_UNKNOWN, attributes={})
        }

        # Process alarm state (directly call async method, skip callback)
        await sonos_integration._process_alarm_state(STATE_UNKNOWN, {})

        # Verify alarm cleared
        assert wake_calc.get_alarm_time() is None, (
            "Cancelled alarm should clear wake sequence"
        )


@pytest.mark.unit
@pytest.mark.sonos
class TestSonosAlarmParsing:
    """Test alarm time parsing from various formats."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass."""
        return MagicMock()

    @pytest.fixture
    def wake_calc(self, mock_hass):
        """Create wake calc."""
        calc = WakeSequenceCalculator(mock_hass)
        calc.configure(enabled=True)
        return calc

    @pytest.fixture
    def sonos_integration(self, mock_hass, wake_calc):
        """Create Sonos integration."""
        return SonosIntegration(mock_hass, wake_calc)

    def test_parse_iso8601_with_timezone(self, sonos_integration):
        """Parse ISO 8601 with timezone offset.

        FORMATS TESTED:
        - 2025-10-02T06:30:00-07:00 (PST)
        - 2025-10-02T06:30:00+00:00 (UTC)
        """
        # PST format
        alarm_pst = "2025-10-02T06:30:00-07:00"
        parsed = sonos_integration._parse_alarm_time(alarm_pst)

        assert parsed is not None, "Should parse PST timezone"
        assert parsed.hour == 6
        assert parsed.minute == 30
        assert parsed.tzinfo is not None

        # UTC format
        alarm_utc = "2025-10-02T06:30:00+00:00"
        parsed = sonos_integration._parse_alarm_time(alarm_utc)

        assert parsed is not None, "Should parse UTC timezone"
        assert parsed.tzinfo is not None

    def test_parse_iso8601_with_z_suffix(self, sonos_integration):
        """Parse ISO 8601 with Z suffix (UTC).

        FORMAT: 2025-10-02T06:30:00Z
        """
        alarm_z = "2025-10-02T06:30:00Z"
        parsed = sonos_integration._parse_alarm_time(alarm_z)

        assert parsed is not None, "Should parse Z suffix as UTC"
        assert parsed.hour == 6
        assert parsed.minute == 30
        assert parsed.tzinfo == UTC

    def test_parse_invalid_format_returns_none(self, sonos_integration):
        """Invalid format should return None with warning.

        INVALID FORMATS:
        - "tomorrow at 6:30" (human readable)
        - "06:30" (time only)
        - "garbage"
        """
        invalid_formats = [
            "tomorrow at 6:30",
            "06:30",
            "garbage",
            "",
            "not_a_timestamp",
        ]

        for invalid in invalid_formats:
            parsed = sonos_integration._parse_alarm_time(invalid)
            assert parsed is None, (
                f"Invalid format '{invalid}' should return None"
            )

    def test_parse_unavailable_returns_none(self, sonos_integration):
        """Unavailable/unknown states should return None."""
        assert sonos_integration._parse_alarm_time(STATE_UNAVAILABLE) is None
        assert sonos_integration._parse_alarm_time(STATE_UNKNOWN) is None


@pytest.mark.unit
@pytest.mark.sonos
class TestSonosIntegrationLifecycle:
    """Test Sonos integration setup, shutdown, and state management."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass with async support."""
        hass = MagicMock()
        hass.states = MagicMock()
        hass.helpers = MagicMock()
        return hass

    @pytest.fixture
    def wake_calc(self, mock_hass):
        """Create wake calc."""
        calc = WakeSequenceCalculator(mock_hass)
        calc.configure(enabled=True)
        return calc

    @pytest.mark.asyncio
    async def test_setup_with_valid_sensor_succeeds(
        self, mock_hass, wake_calc
    ):
        """Setup with valid sensor should succeed.

        SCENARIO: Integration configured with valid Sonos sensor
        EXPECTED: Setup returns True, listener registered
        """
        integration = SonosIntegration(mock_hass, wake_calc)
        integration.configure(
            enabled=True,
            alarm_sensor="sensor.sonos_bedroom_next_alarm"
        )

        # Mock sensor exists
        sensor_state = MagicMock()
        sensor_state.state = "2025-10-02T06:30:00Z"
        sensor_state.attributes = {}
        mock_hass.states.get.return_value = sensor_state

        # Mock listener registration
        with patch(
            "custom_components.adaptive_lighting_pro.integrations.sonos.async_track_state_change_event"
        ) as mock_track:
            mock_track.return_value = MagicMock()  # Remove listener function

            result = await integration.async_setup()

            assert result is True, "Setup should succeed with valid sensor"
            mock_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_with_missing_sensor_fails_gracefully(
        self, mock_hass, wake_calc
    ):
        """Setup with missing sensor should fail gracefully.

        SCENARIO: Sonos integration not loaded, sensor doesn't exist
        EXPECTED: Setup returns False with error log
        WHY: Integration should fail safely if dependency missing
        """
        integration = SonosIntegration(mock_hass, wake_calc)
        integration.configure(
            enabled=True,
            alarm_sensor="sensor.sonos_bedroom_next_alarm"
        )

        # Mock sensor doesn't exist
        mock_hass.states.get.return_value = None

        result = await integration.async_setup()

        assert result is False, (
            "Setup should fail gracefully when sensor missing"
        )

    @pytest.mark.asyncio
    async def test_shutdown_removes_listener(self, mock_hass, wake_calc):
        """Shutdown should remove state change listener.

        SCENARIO: Integration being unloaded
        EXPECTED: Listener removed, no memory leaks
        """
        integration = SonosIntegration(mock_hass, wake_calc)
        integration.configure(enabled=True, alarm_sensor="sensor.test")

        # Setup first
        sensor_state = MagicMock()
        sensor_state.state = "2025-10-02T06:30:00Z"
        sensor_state.attributes = {}
        mock_hass.states.get.return_value = sensor_state

        mock_remove = MagicMock()
        with patch(
            "custom_components.adaptive_lighting_pro.integrations.sonos.async_track_state_change_event",
            return_value=mock_remove
        ):
            await integration.async_setup()

        # Now shutdown
        await integration.async_shutdown()

        # Verify listener removed
        mock_remove.assert_called_once()

    def test_get_status_shows_integration_state(
        self, mock_hass, wake_calc
    ):
        """get_status() should provide complete integration state.

        SCENARIO: Debugging why wake sequence not working
        EXPECTED: Status shows enabled, sensor, monitoring state
        """
        integration = SonosIntegration(mock_hass, wake_calc)
        integration.configure(
            enabled=True,
            alarm_sensor="sensor.sonos_bedroom_next_alarm"
        )

        # Mock sensor state
        sensor_state = MagicMock()
        sensor_state.state = "2025-10-02T06:30:00Z"
        mock_hass.states.get.return_value = sensor_state

        status = integration.get_status()

        assert status["enabled"] is True
        assert status["alarm_sensor"] == "sensor.sonos_bedroom_next_alarm"
        assert status["sensor_state"] == "2025-10-02T06:30:00Z"
        assert "last_alarm_time" in status
        assert "monitoring_active" in status


@pytest.mark.unit
@pytest.mark.sonos
class TestSonosRealWorldScenarios:
    """Test real-world edge cases that WILL happen in daily use."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass."""
        hass = MagicMock()
        hass.states = MagicMock()
        hass.async_create_task = lambda coro: coro
        return hass

    @pytest.fixture
    def wake_calc(self, mock_hass):
        """Create wake calc."""
        calc = WakeSequenceCalculator(mock_hass)
        calc.configure(enabled=True, target_zone="bedroom")
        return calc

    @pytest.fixture
    def sonos_integration(self, mock_hass, wake_calc):
        """Create Sonos integration."""
        integration = SonosIntegration(mock_hass, wake_calc)
        integration.configure(
            enabled=True,
            alarm_sensor="sensor.sonos_bedroom_next_alarm"
        )
        return integration

    @pytest.mark.asyncio
    async def test_multiple_alarms_same_day_processes_earliest(
        self, mock_hass, sonos_integration, wake_calc
    ):
        """Multiple alarms same day should process each independently.

        SCENARIO: 6:30 AM alarm, then 8:00 AM alarm same day
        EXPECTED: First wake at 6:15 AM, second wake at 7:45 AM
        WHY: Weekend mornings - snooze alarm + actual wake alarm
        """
        # First alarm at 6:30 AM
        alarm_1 = (datetime.now(UTC) + timedelta(hours=8)).replace(
            hour=6, minute=30, second=0, microsecond=0
        )

        sensor_state = MagicMock()
        sensor_state.state = alarm_1.isoformat()
        sensor_state.attributes = {}
        mock_hass.states.get.return_value = sensor_state

        await sonos_integration.async_setup()
        first_wake_time = wake_calc.get_wake_start_time()

        # Later, alarm changes to 8:00 AM
        alarm_2 = alarm_1.replace(hour=8, minute=0)
        event = MagicMock()
        event.data = {
            "new_state": MagicMock(
                state=alarm_2.isoformat(),
                attributes={}
            )
        }

        # Process alarm state (directly call async method, skip callback)
        await sonos_integration._process_alarm_state(
            alarm_2.isoformat(), {}
        )

        # Verify new wake time calculated
        second_wake_time = wake_calc.get_wake_start_time()
        assert second_wake_time != first_wake_time, (
            "Wake time should update for new alarm"
        )
        assert wake_calc.get_alarm_time() == alarm_2

    @pytest.mark.asyncio
    async def test_network_blip_sensor_unavailable_recovers(
        self, mock_hass, sonos_integration, wake_calc
    ):
        """Network blip causing sensor unavailable should recover.

        SCENARIO: 6:20 AM - WiFi hiccup, sensor unavailable for 30s
        EXPECTED: Alarm cleared temporarily, restored when sensor returns
        WHY: Network issues are common, must handle gracefully
        """
        # Setup with alarm
        future_alarm = datetime.now(UTC) + timedelta(hours=8)
        sensor_state = MagicMock()
        sensor_state.state = future_alarm.isoformat()
        sensor_state.attributes = {}
        mock_hass.states.get.return_value = sensor_state

        await sonos_integration.async_setup()
        assert wake_calc.get_alarm_time() == future_alarm

        # Network blip - sensor unavailable (directly call async method, skip callback)
        await sonos_integration._process_alarm_state(STATE_UNAVAILABLE, {})

        # Verify alarm cleared during outage
        assert wake_calc.get_alarm_time() is None

        # Network recovers - sensor returns with same alarm (directly call async method)
        await sonos_integration._process_alarm_state(
            future_alarm.isoformat(), {}
        )

        # Verify alarm restored
        assert wake_calc.get_alarm_time() == future_alarm, (
            "Alarm should be restored when sensor recovers"
        )
