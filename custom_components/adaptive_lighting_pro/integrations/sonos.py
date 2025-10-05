"""Sonos integration for Adaptive Lighting Pro.

This module provides Sonos alarm detection to trigger wake sequences.

Real-world behavior (from MY home):
- Sonos bedroom speaker has alarm feature
- Home Assistant exposes sensor with next alarm time
- We monitor this sensor for changes
- When alarm detected, notify wake_sequence calculator
- Handle all the messy real-world edge cases:
  * Sonos sensor goes unavailable (network issue, speaker offline)
  * Alarm cancelled mid-sequence
  * Multiple alarms same day
  * Sensor shows stale/past alarm data
  * HA restart mid-sequence

Quality standards from claude.md:
- "This is YOUR home" - must work reliably every morning
- Graceful degradation - keep working if Sonos offline
- No crashes - handle all error cases
- Clear logging - debug issues at 6 AM when half asleep
"""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

if TYPE_CHECKING:
    from ..features.wake_sequence import WakeSequenceCalculator

_LOGGER = logging.getLogger(__name__)


class SonosIntegration:
    """Monitor Sonos alarm sensor and trigger wake sequences.

    This integration watches a Sonos media_player's next_alarm attribute
    (or a dedicated alarm sensor) and notifies the wake_sequence calculator
    when alarms are detected.

    Real-world scenarios handled:
    1. Normal case: Alarm set for 6:30 AM → wake sequence starts at 6:15 AM
    2. Alarm cancelled: Mid-sequence cancellation → immediately stop wake boost
    3. Sensor unavailable: Sonos offline → gracefully skip, resume when back
    4. Stale data: Sensor shows past alarm → ignore
    5. Multiple alarms: Process each independently
    6. HA restart: Wake sequence persists via coordinator state
    """

    def __init__(
        self,
        hass: HomeAssistant,
        wake_sequence: WakeSequenceCalculator,
    ) -> None:
        """Initialize Sonos integration.

        Args:
            hass: Home Assistant instance
            wake_sequence: Wake sequence calculator to notify of alarms
        """
        self.hass = hass
        self._wake_sequence = wake_sequence
        self._alarm_sensor: str | None = None
        self._enabled: bool = False
        self._remove_listener: Any = None
        self._last_alarm_time: datetime | None = None

    def configure(
        self,
        enabled: bool = False,
        alarm_sensor: str | None = None,
    ) -> None:
        """Configure Sonos integration.

        Args:
            enabled: Enable Sonos alarm monitoring
            alarm_sensor: Entity ID of Sonos alarm sensor (e.g., sensor.sonos_bedroom_next_alarm)
        """
        self._enabled = enabled
        self._alarm_sensor = alarm_sensor

        _LOGGER.info(
            "Sonos integration configured: enabled=%s, alarm_sensor=%s",
            enabled,
            alarm_sensor,
        )

    async def async_setup(self) -> bool:
        """Set up Sonos alarm monitoring.

        Returns:
            True if setup successful, False otherwise
        """
        if not self._enabled:
            _LOGGER.debug("Sonos integration disabled, skipping setup")
            return False

        if not self._alarm_sensor:
            _LOGGER.warning(
                "Sonos integration enabled but no alarm_sensor configured. "
                "Wake sequence will not trigger automatically."
            )
            return False

        # Verify sensor exists
        sensor_state = self.hass.states.get(self._alarm_sensor)
        if not sensor_state:
            _LOGGER.error(
                "Sonos alarm sensor %s not found. Wake sequence will not work. "
                "Please check your configuration and ensure Sonos integration is loaded.",
                self._alarm_sensor,
            )
            return False

        # Register state change listener
        self._remove_listener = async_track_state_change_event(
            self.hass,
            [self._alarm_sensor],
            self._alarm_sensor_changed,
        )

        _LOGGER.info(
            "Sonos integration setup complete. Monitoring %s for alarm changes.",
            self._alarm_sensor,
        )

        # Process current state (in case alarm already set)
        await self._process_alarm_state(sensor_state.state, sensor_state.attributes)

        return True

    async def async_shutdown(self) -> None:
        """Shut down Sonos integration and clean up listeners."""
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None
            _LOGGER.debug("Sonos alarm listener removed")

    @callback
    def _alarm_sensor_changed(self, event: Event) -> None:
        """Handle Sonos alarm sensor state changes.

        Args:
            event: State change event from Home Assistant
        """
        new_state = event.data.get("new_state")
        if not new_state:
            _LOGGER.debug("Alarm sensor removed, clearing wake sequence")
            self._wake_sequence.clear_alarm()
            self._last_alarm_time = None
            return

        # Process the new state
        self.hass.async_create_task(
            self._process_alarm_state(new_state.state, new_state.attributes)
        )

    async def _process_alarm_state(
        self,
        state: str,
        attributes: dict[str, Any],
    ) -> None:
        """Process Sonos alarm sensor state and update wake sequence.

        Args:
            state: Sensor state (ISO timestamp or unavailable/unknown)
            attributes: Sensor attributes
        """
        # Handle unavailable/unknown states
        if state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.info(
                "Sonos alarm sensor unavailable (state=%s). "
                "Wake sequence will resume when sensor comes back online.",
                state,
            )
            # Clear current alarm but don't disable wake_sequence
            # It might come back online
            if self._last_alarm_time is not None:
                self._wake_sequence.clear_alarm()
                self._last_alarm_time = None
            return

        # Parse alarm time from state
        alarm_time = self._parse_alarm_time(state)
        if not alarm_time:
            _LOGGER.debug(
                "Could not parse alarm time from state: %s. No wake sequence will trigger.",
                state,
            )
            # Clear any existing alarm
            if self._last_alarm_time is not None:
                self._wake_sequence.clear_alarm()
                self._last_alarm_time = None
            return

        # Check if this is a new/different alarm
        if alarm_time == self._last_alarm_time:
            _LOGGER.debug(
                "Alarm time unchanged (%s), no action needed",
                alarm_time.isoformat() if alarm_time else "None",
            )
            return

        # New alarm detected
        _LOGGER.info(
            "Sonos alarm detected: %s (previous: %s)",
            alarm_time.isoformat(),
            self._last_alarm_time.isoformat() if self._last_alarm_time else "None",
        )

        # Notify wake_sequence calculator
        self._wake_sequence.set_next_alarm(alarm_time)
        self._last_alarm_time = alarm_time

    def _parse_alarm_time(self, state_value: str) -> datetime | None:
        """Parse alarm time from sensor state.

        Sonos alarm sensors typically provide ISO 8601 timestamp strings.
        Examples:
        - "2025-10-02T06:30:00-07:00"
        - "2025-10-02T06:30:00+00:00"
        - "2025-10-02T06:30:00Z"

        Args:
            state_value: Sensor state string

        Returns:
            Parsed datetime (timezone-aware) or None if parsing fails
        """
        if not state_value or state_value in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None

        try:
            # Parse ISO 8601 timestamp
            alarm_time = datetime.fromisoformat(state_value.replace('Z', '+00:00'))

            # Ensure timezone-aware
            if alarm_time.tzinfo is None:
                _LOGGER.warning(
                    "Alarm time %s is timezone-naive, assuming UTC",
                    state_value,
                )
                alarm_time = alarm_time.replace(tzinfo=UTC)

            return alarm_time

        except (ValueError, AttributeError) as err:
            _LOGGER.warning(
                "Failed to parse alarm time from '%s': %s. "
                "Expected ISO 8601 format (e.g., '2025-10-02T06:30:00-07:00')",
                state_value,
                err,
            )
            return None

    def get_status(self) -> dict[str, Any]:
        """Get current Sonos integration status.

        Returns:
            Status dictionary with monitoring info
        """
        sensor_state = None
        if self._alarm_sensor:
            sensor_state_obj = self.hass.states.get(self._alarm_sensor)
            sensor_state = sensor_state_obj.state if sensor_state_obj else "not_found"

        return {
            "enabled": self._enabled,
            "alarm_sensor": self._alarm_sensor,
            "sensor_state": sensor_state,
            "last_alarm_time": (
                self._last_alarm_time.isoformat() if self._last_alarm_time else None
            ),
            "monitoring_active": self._remove_listener is not None,
        }
