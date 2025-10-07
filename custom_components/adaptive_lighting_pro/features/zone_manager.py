"""Zone state management, timer tracking, and persistence across restarts.

This module manages the state of all zones in the Adaptive Lighting Pro integration,
including manual control override timers. It handles:
- Tracking manual control state per zone
- Managing countdown timers for automatic reversion to adaptive control
- Persisting timer state across Home Assistant restarts
- Providing zone state information for entities and services

The ZoneManager maintains a centralized view of all zone states and coordinates
timer expiry checking with the main integration coordinator.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, UTC
from typing import Any, TYPE_CHECKING
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from ..const import (
    DOMAIN,
    CONF_ZONES,
    CONF_MANUAL_TIMER_DURATION,
    DEFAULT_MANUAL_TIMEOUT_SECONDS,
    EVENT_MANUAL_CONTROL_TRIGGERED,
)

if TYPE_CHECKING:
    from .manual_control import ManualControlDetector
    from ..coordinator import ALPDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class ZoneState:
    """Represents the current state of a zone including manual control and timer info.

    Attributes:
        zone_id: Unique identifier for the zone
        manual_control_active: Whether manual control override is currently active
        timer_expiry: UTC timestamp when the manual control timer expires (None if no timer)
        timer_duration: Original timer duration in seconds (0 if no timer)
        last_manual_trigger: UTC timestamp of the last manual control trigger
    """

    zone_id: str
    manual_control_active: bool = False
    timer_expiry: datetime | None = None
    timer_duration: int = 0
    last_manual_trigger: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert zone state to dictionary with ISO format timestamps.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "zone_id": self.zone_id,
            "manual_control_active": self.manual_control_active,
            "timer_expiry": self.timer_expiry.isoformat() if self.timer_expiry else None,
            "timer_duration": self.timer_duration,
            "last_manual_trigger": self.last_manual_trigger.isoformat() if self.last_manual_trigger else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ZoneState:
        """Parse zone state from dictionary, handling timezone awareness.

        Args:
            data: Dictionary containing zone state data

        Returns:
            ZoneState instance with parsed datetime objects
        """
        # Parse ISO format timestamps and ensure timezone awareness
        timer_expiry = None
        if data.get("timer_expiry"):
            timer_expiry = datetime.fromisoformat(data["timer_expiry"])
            # Ensure timezone awareness
            if timer_expiry.tzinfo is None:
                timer_expiry = timer_expiry.replace(tzinfo=UTC)

        last_manual_trigger = None
        if data.get("last_manual_trigger"):
            last_manual_trigger = datetime.fromisoformat(data["last_manual_trigger"])
            # Ensure timezone awareness
            if last_manual_trigger.tzinfo is None:
                last_manual_trigger = last_manual_trigger.replace(tzinfo=UTC)

        return cls(
            zone_id=data["zone_id"],
            manual_control_active=data.get("manual_control_active", False),
            timer_expiry=timer_expiry,
            timer_duration=data.get("timer_duration", 0),
            last_manual_trigger=last_manual_trigger,
        )


class ZoneManager:
    """Manages zone states, manual control timers, and state persistence.

    The ZoneManager is responsible for:
    - Maintaining the current state of all configured zones
    - Starting and canceling manual control timers
    - Checking for expired timers
    - Persisting and restoring state across restarts
    - Providing zone state information to other components
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        manual_detector: ManualControlDetector | None = None,
        coordinator: ALPDataUpdateCoordinator | None = None,
    ) -> None:
        """Initialize the zone manager.

        Args:
            hass: Home Assistant instance
            config_entry: Configuration entry for this integration instance
            manual_detector: Optional manual control detector for smart timeout calculation
            coordinator: Optional coordinator reference for accessing runtime configuration
        """
        self.hass = hass
        self.config_entry = config_entry
        self._zone_states: dict[str, ZoneState] = {}
        self._manual_detector = manual_detector
        self._coordinator = coordinator

        # Load zones from config
        zones_config = config_entry.data.get(CONF_ZONES, [])
        for zone_config in zones_config:
            zone_id = zone_config["zone_id"]
            self._zone_states[zone_id] = ZoneState(zone_id=zone_id)

        _LOGGER.debug(
            "ZoneManager initialized with %d zones: %s",
            len(self._zone_states),
            list(self._zone_states.keys()),
        )

        # Restore persisted state
        self._restore_state()

    def _restore_state(self) -> None:
        """Load persisted timer state from hass.data.

        Restores zone states that were saved before a restart, allowing
        manual control timers to persist across Home Assistant restarts.
        """
        entry_id = self.config_entry.entry_id

        # Ensure domain data exists
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}

        if entry_id not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][entry_id] = {}

        # Try to restore from persisted data
        persisted_timers = self.hass.data[DOMAIN][entry_id].get("zone_timers", {})

        if not persisted_timers:
            _LOGGER.debug("No persisted zone timer state found")
            return

        restored_count = 0
        now = datetime.now(UTC)

        for zone_id, state_dict in persisted_timers.items():
            if zone_id not in self._zone_states:
                _LOGGER.warning(
                    "Skipping persisted state for unknown zone: %s", zone_id
                )
                continue

            try:
                restored_state = ZoneState.from_dict(state_dict)

                # Check if timer has already expired during downtime
                if restored_state.timer_expiry and restored_state.timer_expiry <= now:
                    _LOGGER.info(
                        "Timer for zone %s expired during downtime, clearing manual control",
                        zone_id,
                    )
                    restored_state.manual_control_active = False
                    restored_state.timer_expiry = None
                    restored_state.timer_duration = 0

                self._zone_states[zone_id] = restored_state
                restored_count += 1

                _LOGGER.debug(
                    "Restored state for zone %s from hass.data: manual_active=%s, timer_expiry=%s",
                    zone_id,
                    restored_state.manual_control_active,
                    restored_state.timer_expiry,
                )

            except Exception as err:
                _LOGGER.error(
                    "Failed to restore state for zone %s: %s", zone_id, err
                )

        _LOGGER.info("Restored state for %d zones from hass.data", restored_count)

        # CRITICAL FIX: Also check timer entity states (they have restore: true)
        # This handles the case where HA restarted and timer entities restored
        # but hass.data was lost (in-memory only, not persisted)
        timer_restored_count = 0
        for zone_id in self._zone_states.keys():
            timer_entity_id = f"timer.alp_manual_{zone_id}"
            timer_state = self.hass.states.get(timer_entity_id)

            if timer_state and timer_state.state == "active":
                # Timer entity is active, restore zone state from it
                finishes_at = timer_state.attributes.get("finishes_at")
                duration_str = timer_state.attributes.get("duration", "0:00:00")

                if finishes_at:
                    try:
                        # Parse finish time
                        timer_expiry = datetime.fromisoformat(finishes_at.replace("Z", "+00:00"))

                        # Parse duration (format: "H:MM:SS")
                        time_parts = duration_str.split(":")
                        duration_seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])

                        # Check if timer already expired
                        if timer_expiry > now:
                            # Restore zone state from timer
                            self._zone_states[zone_id].manual_control_active = True
                            self._zone_states[zone_id].timer_expiry = timer_expiry
                            self._zone_states[zone_id].timer_duration = duration_seconds
                            self._zone_states[zone_id].last_manual_trigger = timer_expiry - timedelta(seconds=duration_seconds)

                            timer_restored_count += 1
                            _LOGGER.info(
                                "Restored zone %s from timer entity: expires=%s, remaining=%ds",
                                zone_id,
                                timer_expiry.isoformat(),
                                (timer_expiry - now).total_seconds(),
                            )
                    except Exception as err:
                        _LOGGER.error("Failed to parse timer state for %s: %s", zone_id, err)

        if timer_restored_count > 0:
            _LOGGER.info("Restored state for %d zones from timer entities", timer_restored_count)

    async def async_persist_state(self) -> None:
        """Save current zone states to hass.data for persistence.

        Stores zone states in a way that survives Home Assistant restarts,
        allowing manual control timers to continue after a restart.
        """
        entry_id = self.config_entry.entry_id

        # Ensure domain data structure exists
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}

        if entry_id not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][entry_id] = {}

        # Convert all zone states to dicts
        zone_timers = {
            zone_id: state.to_dict()
            for zone_id, state in self._zone_states.items()
        }

        self.hass.data[DOMAIN][entry_id]["zone_timers"] = zone_timers

        _LOGGER.debug("Persisted state for %d zones", len(zone_timers))

    async def async_start_manual_timer(
        self,
        zone_id: str,
        duration: int | None = None,
        sun_elevation: float | None = None,
        env_boost: int = 0,
    ) -> None:
        """Start a manual control timer for a zone.

        Args:
            zone_id: Zone identifier
            duration: Timer duration in seconds (uses smart calculation if None)
            sun_elevation: Sun elevation for smart timeout calculation
            env_boost: Environmental boost percentage for smart timeout calculation

        Raises:
            ValueError: If zone_id is not found
        """
        if zone_id not in self._zone_states:
            raise ValueError(f"Unknown zone: {zone_id}")

        # Calculate smart duration if not specified
        if duration is None:
            if self._manual_detector is not None:
                # Use smart timeout calculation
                duration = self._manual_detector.calculate_smart_timeout(
                    zone_id=zone_id,
                    sun_elevation=sun_elevation,
                    env_boost=env_boost,
                )
                _LOGGER.debug(
                    "Using smart timeout for zone %s: %ds (sun_elev=%s, env_boost=%d%%)",
                    zone_id,
                    duration,
                    f"{sun_elevation:.1f}°" if sun_elevation is not None else "unknown",
                    env_boost,
                )
            else:
                # Fall back to coordinator setting (runtime config) or config entry
                if self._coordinator is not None:
                    duration = self._coordinator.get_manual_control_timeout()
                    _LOGGER.debug("Using coordinator timeout for zone %s: %ds", zone_id, duration)
                else:
                    duration = self.config_entry.data.get(
                        CONF_MANUAL_TIMER_DURATION, DEFAULT_MANUAL_TIMEOUT_SECONDS
                    )
                    _LOGGER.debug("Using config entry timeout for zone %s: %ds", zone_id, duration)

        now = datetime.now(UTC)
        expiry = now + timedelta(seconds=duration)

        state = self._zone_states[zone_id]
        state.manual_control_active = True
        state.timer_expiry = expiry
        state.timer_duration = duration
        state.last_manual_trigger = now

        _LOGGER.info(
            "Started manual timer for zone %s: duration=%ds, expiry=%s",
            zone_id,
            duration,
            expiry.isoformat(),
        )

        # CRITICAL FIX: Start actual HA timer entity
        timer_entity = f"timer.alp_manual_{zone_id}"
        try:
            await self.hass.services.async_call(
                "timer",
                "start",
                {
                    "entity_id": timer_entity,
                    "duration": duration,
                },
            )
            _LOGGER.info("Started HA timer entity: %s for %ds", timer_entity, duration)
        except Exception as err:
            _LOGGER.error(
                "Failed to start HA timer %s: %s (timer entity may not exist in YAML)",
                timer_entity,
                err,
            )

        # Fire event for other components to react
        self.hass.bus.async_fire(
            EVENT_MANUAL_CONTROL_TRIGGERED,
            {
                "zone_id": zone_id,
                "duration": duration,
                "expiry": expiry.isoformat(),
            },
        )

        # Persist the change
        await self.async_persist_state()

    async def async_cancel_timer(self, zone_id: str) -> None:
        """Cancel the manual control timer for a zone.

        Args:
            zone_id: Zone identifier

        Raises:
            ValueError: If zone_id is not found
        """
        if zone_id not in self._zone_states:
            raise ValueError(f"Unknown zone: {zone_id}")

        state = self._zone_states[zone_id]

        if not state.manual_control_active:
            _LOGGER.debug("No active timer to cancel for zone %s", zone_id)
            return

        state.manual_control_active = False
        state.timer_expiry = None
        state.timer_duration = 0

        # CRITICAL FIX: Cancel actual HA timer entity
        timer_entity = f"timer.alp_manual_{zone_id}"
        try:
            await self.hass.services.async_call(
                "timer",
                "cancel",
                {
                    "entity_id": timer_entity,
                },
            )
            _LOGGER.info("Cancelled HA timer entity: %s", timer_entity)
        except Exception as err:
            _LOGGER.debug(
                "Could not cancel HA timer %s: %s (may already be finished)",
                timer_entity,
                err,
            )

        _LOGGER.info("Cancelled manual timer for zone %s", zone_id)

        # Persist the change
        await self.async_persist_state()

    async def async_cancel_all_timers(self) -> int:
        """Cancel all active manual control timers.

        Returns:
            Number of timers that were cancelled
        """
        cancelled_count = 0

        for zone_id, state in self._zone_states.items():
            if state.manual_control_active:
                state.manual_control_active = False
                state.timer_expiry = None
                state.timer_duration = 0
                cancelled_count += 1
                _LOGGER.debug("Cancelled timer for zone %s", zone_id)

        if cancelled_count > 0:
            _LOGGER.info("Cancelled %d manual control timers", cancelled_count)
            await self.async_persist_state()

        return cancelled_count

    def is_manual_control_active(self, zone_id: str) -> bool:
        """Check if manual control is currently active for a zone.

        Args:
            zone_id: Zone identifier

        Returns:
            True if manual control is active, False otherwise
        """
        if zone_id not in self._zone_states:
            _LOGGER.warning("Unknown zone queried: %s", zone_id)
            return False

        return self._zone_states[zone_id].manual_control_active

    def get_timer_remaining(self, zone_id: str) -> int:
        """Get remaining time in seconds for a zone's manual control timer.

        Args:
            zone_id: Zone identifier

        Returns:
            Remaining seconds (0 if no active timer or timer expired)
        """
        if zone_id not in self._zone_states:
            return 0

        state = self._zone_states[zone_id]

        if not state.manual_control_active or not state.timer_expiry:
            return 0

        now = datetime.now(UTC)
        remaining = (state.timer_expiry - now).total_seconds()

        return max(0, int(remaining))

    def get_zone_state(self, zone_id: str) -> ZoneState | None:
        """Get the current state for a specific zone.

        Args:
            zone_id: Zone identifier

        Returns:
            ZoneState object or None if zone not found
        """
        return self._zone_states.get(zone_id)

    def get_all_zone_states(self) -> dict[str, ZoneState]:
        """Get all zone states.

        Returns:
            Dictionary mapping zone_id to ZoneState
        """
        return self._zone_states.copy()

    async def async_update_timers(self) -> list[str]:
        """Check all timers and expire any that have passed their expiry time.

        This should be called periodically by the coordinator to check for
        expired timers and transition zones back to adaptive control.

        Returns:
            List of zone_ids whose timers expired
        """
        now = datetime.now(UTC)
        expired_zones = []

        for zone_id, state in self._zone_states.items():
            if not state.manual_control_active or not state.timer_expiry:
                continue

            if state.timer_expiry <= now:
                _LOGGER.info(
                    "Manual control timer expired for zone %s", zone_id
                )
                state.manual_control_active = False
                state.timer_expiry = None
                state.timer_duration = 0
                expired_zones.append(zone_id)

        if expired_zones:
            await self.async_persist_state()

        return expired_zones

    def any_manual_timers_active(self) -> bool:
        """Check if any zone has an active manual control timer.

        Used by coordinator to determine if manual adjustments should be cleared
        when all zone timers expire.

        Returns:
            True if at least one zone has an active timer, False otherwise
        """
        now = datetime.now(UTC)

        for state in self._zone_states.values():
            if state.manual_control_active and state.timer_expiry:
                if state.timer_expiry > now:
                    return True

        return False

    def get_zone_timer_info(self, zone_id: str) -> dict[str, Any]:
        """Get zone timer information formatted for entity attributes.

        Args:
            zone_id: Zone identifier

        Returns:
            Dictionary with timer info suitable for entity attributes
        """
        if zone_id not in self._zone_states:
            return {
                "manual_control_active": False,
                "timer_remaining": 0,
                "timer_duration": 0,
                "timer_expiry": None,
                "last_manual_trigger": None,
            }

        state = self._zone_states[zone_id]

        return {
            "manual_control_active": state.manual_control_active,
            "timer_remaining": self.get_timer_remaining(zone_id),
            "timer_duration": state.timer_duration,
            "timer_expiry": state.timer_expiry.isoformat() if state.timer_expiry else None,
            "last_manual_trigger": state.last_manual_trigger.isoformat() if state.last_manual_trigger else None,
        }

    async def async_set_manual_control(
        self,
        zone_id: str,
        active: bool,
        duration_seconds: int | None = None,
    ) -> None:
        """Set manual control state for a zone.

        This is the primary method for controlling manual override state.
        When activating manual control, starts a timer. When deactivating,
        cancels any existing timer.

        Args:
            zone_id: Zone identifier
            active: Whether to activate or deactivate manual control
            duration_seconds: Timer duration when activating (uses config default if None)

        Raises:
            ValueError: If zone_id is not found
        """
        if zone_id not in self._zone_states:
            raise ValueError(f"Unknown zone: {zone_id}")

        if active:
            # Activate manual control with timer
            await self.async_start_manual_timer(zone_id, duration_seconds)
            _LOGGER.info("Manual control activated for zone %s", zone_id)
        else:
            # Deactivate manual control
            await self.async_cancel_timer(zone_id)
            _LOGGER.info("Manual control deactivated for zone %s", zone_id)

    # ========== Phase 1.9: Query Methods for Sensors ==========

    def get_active_timer_zones(self) -> list[str]:
        """Get list of zone IDs with active manual control timers.

        Returns:
            List of zone IDs that currently have active manual control timers
        """
        return [
            zone_id
            for zone_id, state in self._zone_states.items()
            if state.manual_control_active and state.timer_expiry is not None
        ]

    def get_timer_remaining_seconds(self, zone_id: str) -> int:
        """Get remaining time in seconds for a zone's timer.

        Alias for get_timer_remaining() for consistency with naming convention.

        Args:
            zone_id: Zone identifier

        Returns:
            Remaining seconds (0 if no active timer)
        """
        return self.get_timer_remaining(zone_id)
