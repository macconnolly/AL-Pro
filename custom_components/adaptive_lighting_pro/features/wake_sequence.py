"""Wake sequence for Adaptive Lighting Pro.

This module provides gradual brightness ramping before alarms (Sonos integration).

Purpose:
- Gentle wake-up experience with 15-minute brightness ramp
- Starts 15 minutes before alarm time (configurable)
- Gradually increases from 0% to 20% boost (configurable)
- Targets specific zone (bedroom by default)
- Combines with environmental and sunset boosts

Real-world scenario from claude.md:
- 6:30 AM alarm set on Sonos
- 6:15 AM: Wake sequence starts (0% boost)
- 6:22 AM: Halfway through (10% boost)
- 6:30 AM: Alarm fires (20% boost), sequence ends
- Dark cloudy morning: env_boost (25%) + wake_boost (20%) = 45% total
  → Intelligent capping applies to prevent boundary collapse

Quality standards:
- "This is YOUR home" - Must work reliably every morning
- Graceful degradation when alarm cancelled or Sonos unavailable
- Clean separation: WakeSequenceCalculator = pure logic, SonosIntegration = sensor monitoring
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class WakeSequenceCalculator:
    """Calculate brightness boost during sunrise wake sequence.

    This calculator provides gradual brightness ramping before alarms:
    1. Alarm time set (via SonosIntegration or manual)
    2. Wake sequence starts 15 minutes before alarm
    3. Brightness boost ramps from 0% → 20% linearly over 15 minutes
    4. Boost applied only to target zone (bedroom by default)
    5. Sequence ends when alarm fires

    The wake boost combines with environmental and sunset boosts,
    subject to intelligent capping to prevent boundary collapse.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize wake sequence calculator.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass
        self._enabled: bool = False
        self._alarm_time: datetime | None = None
        self._wake_start_time: datetime | None = None
        self._target_zone: str = "bedroom"
        self._duration_seconds: int = 900  # 15 minutes
        self._max_boost_pct: int = 20

    def configure(
        self,
        enabled: bool = False,
        target_zone: str = "bedroom",
        duration_seconds: int = 900,
        max_boost_pct: int = 20,
    ) -> None:
        """Configure wake sequence feature.

        Args:
            enabled: Enable wake sequence calculations
            target_zone: Zone ID to apply wake boost to
            duration_seconds: Wake ramp duration (default 900 = 15 min)
            max_boost_pct: Maximum boost at alarm time (default 20%)
        """
        self._enabled = enabled
        self._target_zone = target_zone
        self._duration_seconds = duration_seconds
        self._max_boost_pct = max_boost_pct

        _LOGGER.info(
            "Wake sequence configured: enabled=%s, target_zone=%s, duration=%ds, max_boost=%d%%",
            enabled,
            target_zone,
            duration_seconds,
            max_boost_pct,
        )

    def set_next_alarm(self, alarm_time: datetime) -> None:
        """Set next alarm time and calculate wake sequence start.

        Called by SonosIntegration when alarm detected.

        Args:
            alarm_time: Alarm time (timezone-aware datetime)

        Raises:
            ValueError: If alarm_time is in the past
        """
        if not self._enabled:
            _LOGGER.debug("Wake sequence disabled, ignoring alarm")
            return

        now = datetime.now(UTC)

        # Validate alarm is in the future
        if alarm_time <= now:
            _LOGGER.warning(
                "Ignoring alarm in the past: %s (current time: %s)",
                alarm_time.isoformat(),
                now.isoformat(),
            )
            return

        # Calculate wake start time
        self._alarm_time = alarm_time
        self._wake_start_time = alarm_time - timedelta(seconds=self._duration_seconds)

        _LOGGER.info(
            "Wake sequence scheduled: alarm=%s, wake_start=%s, target_zone=%s",
            alarm_time.isoformat(),
            self._wake_start_time.isoformat(),
            self._target_zone,
        )

    def clear_alarm(self) -> None:
        """Clear current alarm and stop wake sequence.

        Called when alarm cancelled or after alarm fires.
        """
        if self._alarm_time:
            _LOGGER.info("Clearing wake sequence alarm")

        self._alarm_time = None
        self._wake_start_time = None

    def calculate_boost(self, zone_id: str) -> int:
        """Calculate wake sequence boost for this zone.

        Returns boost percentage based on current position in wake sequence.
        Only applies to target zone during active wake window.

        Args:
            zone_id: Zone identifier

        Returns:
            Brightness boost in percent (0 to max_boost_pct)
            Returns 0 if:
            - Feature disabled
            - No alarm set
            - Current time before wake start
            - Current time after alarm
            - zone_id != target_zone
            - Skip toggle is enabled

        Examples:
            >>> # 6:15 AM (alarm at 6:30 AM, just started)
            >>> calculator.calculate_boost("bedroom")
            0  # Just started, 0% boost

            >>> # 6:22:30 AM (halfway through 15-min ramp)
            >>> calculator.calculate_boost("bedroom")
            10  # 50% progress → 10% boost

            >>> # 6:30 AM (alarm time)
            >>> calculator.calculate_boost("bedroom")
            20  # Full boost

            >>> # 6:22 AM but living_room zone
            >>> calculator.calculate_boost("living_room")
            0  # Only affects bedroom
        """
        if not self.is_available():
            return 0

        # Check if skip toggle is enabled (user requested to skip this alarm)
        skip_entity = "input_boolean.alp_disable_next_sonos_wakeup"
        if self.hass:
            skip_state = self.hass.states.get(skip_entity)
            if skip_state and skip_state.state == "on":
                _LOGGER.info("Wake sequence skipped by user request (skip toggle enabled)")
                return 0

        # Only apply to target zone
        if zone_id != self._target_zone:
            return 0

        # No alarm set
        if not self._alarm_time or not self._wake_start_time:
            return 0

        now = datetime.now(UTC)

        # Before wake sequence starts
        if now < self._wake_start_time:
            return 0

        # After alarm fires - clear and stop
        if now >= self._alarm_time:
            _LOGGER.debug("Wake sequence complete (alarm fired), clearing")
            self.clear_alarm()
            return 0

        # During wake sequence - calculate progress
        elapsed = (now - self._wake_start_time).total_seconds()
        progress = min(1.0, elapsed / self._duration_seconds)
        boost = int(progress * self._max_boost_pct)

        _LOGGER.debug(
            "Wake sequence active: progress=%.1f%%, boost=%d%% (elapsed=%ds/%ds)",
            progress * 100,
            boost,
            int(elapsed),
            self._duration_seconds,
        )

        return boost

    def is_available(self) -> bool:
        """Check if wake sequence is enabled.

        Returns:
            True if wake sequence is enabled
        """
        return self._enabled

    def get_alarm_time(self) -> datetime | None:
        """Get current alarm time.

        Returns:
            Alarm time or None if no alarm set
        """
        return self._alarm_time

    def get_wake_start_time(self) -> datetime | None:
        """Get wake sequence start time.

        Returns:
            Wake start time or None if no alarm set
        """
        return self._wake_start_time

    def get_target_zone(self) -> str:
        """Get target zone for wake sequence.

        Returns:
            Target zone ID
        """
        return self._target_zone

    def get_progress_pct(self) -> float:
        """Get current progress through wake sequence.

        Returns:
            Progress percentage (0.0 to 100.0) or 0.0 if not active
        """
        if not self._alarm_time or not self._wake_start_time:
            return 0.0

        now = datetime.now(UTC)

        if now < self._wake_start_time:
            return 0.0

        if now >= self._alarm_time:
            return 0.0

        elapsed = (now - self._wake_start_time).total_seconds()
        progress = min(1.0, elapsed / self._duration_seconds)
        return progress * 100.0

    def get_state_dict(self) -> dict:
        """Get complete wake sequence state for sensors.

        Returns:
            Dictionary with all wake sequence state information
        """
        active = self._alarm_time is not None and self._wake_start_time is not None

        if not active:
            return {
                "active": False,
                "alarm_time": None,
                "wake_start_time": None,
                "target_zone": self._target_zone,
                "current_boost_pct": 0,
                "progress_pct": 0.0,
                "duration_seconds": self._duration_seconds,
                "max_boost_pct": self._max_boost_pct,
            }

        now = datetime.now(UTC)
        current_boost = self.calculate_boost(self._target_zone)
        progress = self.get_progress_pct()

        # Check if currently in active window
        in_window = (
            self._wake_start_time <= now < self._alarm_time
            if self._wake_start_time and self._alarm_time
            else False
        )

        return {
            "active": in_window,
            "alarm_time": self._alarm_time,  # Return datetime object for timestamp sensors
            "wake_start_time": self._wake_start_time,  # Return datetime object for timestamp sensors
            "target_zone": self._target_zone,
            "current_boost_pct": current_boost,
            "progress_pct": round(progress, 1),
            "duration_seconds": self._duration_seconds,
            "max_boost_pct": self._max_boost_pct,
        }
