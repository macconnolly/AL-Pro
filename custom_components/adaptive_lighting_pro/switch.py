"""Switch platform for Adaptive Lighting Pro.

This module implements the switch entities for the Adaptive Lighting Pro integration.

Phase 1 Implementation:
- ALPGlobalPauseSwitch: Global pause control (switch.alp_global_pause)

Future Phase 2 will add per-zone switches for each zone:
- ALPZoneSwitch: Per-zone enable/disable control
- Additional zone-specific controls as needed

The switches interact with the coordinator to manage the state of the integration,
allowing users to pause/resume adaptive lighting behavior globally or per-zone.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import ALPEntity

if TYPE_CHECKING:
    from .coordinator import ALPDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Lighting Pro switch entities from a config entry.

    This function is called by Home Assistant when the integration is loaded.
    It creates all switch entities and adds them to Home Assistant.

    Phase 1: Creates only the global pause switch
    Future Phase 2: Will create per-zone switches for each configured zone

    Args:
        hass: Home Assistant instance
        entry: Config entry containing zone and settings configuration
        async_add_entities: Callback to add entities to Home Assistant
    """
    # Get the coordinator from hass.data (handle both dict and direct storage)
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ALPDataUpdateCoordinator = (
        entry_data.get("coordinator") if isinstance(entry_data, dict) else entry_data
    )

    # Phase 1: Create list of switch entities (only global pause switch)
    entities: list[SwitchEntity] = []

    # Add global pause switch
    entities.append(ALPGlobalPauseSwitch(coordinator, entry))

    # Add wake sequence enable/disable switch
    entities.append(ALPWakeSequenceSwitch(coordinator, entry))

    # Phase 2 will add per-zone switches here:
    # for zone_id in coordinator.zone_ids:
    #     entities.append(ALPZoneSwitch(coordinator, entry, zone_id))

    _LOGGER.info(
        "Setting up %d ALP switch entities: %s",
        len(entities),
        [entity.name for entity in entities]
    )

    # Add all entities to Home Assistant
    async_add_entities(entities)


class ALPGlobalPauseSwitch(ALPEntity, SwitchEntity):
    """Switch to control global pause state for Adaptive Lighting Pro.

    This switch allows users to pause/resume all adaptive lighting operations
    across all zones. When paused, no automatic adjustments are made, but
    manual controls still function.

    Entity ID: switch.alp_global_pause
    Display Name: "Global Pause"

    State:
    - ON: Adaptive lighting is paused (no automatic adjustments)
    - OFF: Adaptive lighting is active (normal operation)

    Behavior:
    - turn_on: Calls coordinator.set_paused(True)
    - turn_off: Calls coordinator.set_paused(False)
    - is_on: Reads from coordinator.data["global"]["paused"]  # OK: property access, consider adding getter if pattern spreads

    The coordinator will respect this state during its update cycle and
    skip automatic adjustments when paused is True.
    """

    _attr_icon = "mdi:pause-circle"

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the global pause switch.

        Args:
            coordinator: Data update coordinator managing state
            entry: Config entry this switch belongs to
        """
        super().__init__(
            coordinator=coordinator,
            entry=entry,
            entity_type="switch",
            entity_id_suffix="global_pause",
            name_suffix="Global Pause",
        )

        _LOGGER.debug(
            "Initialized ALPGlobalPauseSwitch: %s (ID: %s)",
            self.name,
            self.unique_id
        )

    @property
    def is_on(self) -> bool:
        """Return True if the global pause is enabled.

        Returns:
            True if adaptive lighting is paused, False if active
        """
        return self.coordinator.get_paused()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the global pause (pause adaptive lighting).

        Uses coordinator.set_paused() method for proper encapsulation.

        Args:
            **kwargs: Additional arguments (not used)
        """
        _LOGGER.info("Turning ON global pause - pausing adaptive lighting")
        await self.coordinator.set_paused(True)
        _LOGGER.debug("Global pause enabled successfully")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the global pause (resume adaptive lighting).

        Uses coordinator.set_paused() method for proper encapsulation.

        Args:
            **kwargs: Additional arguments (not used)
        """
        _LOGGER.info("Turning OFF global pause - resuming adaptive lighting")
        await self.coordinator.set_paused(False)
        _LOGGER.debug("Global pause disabled successfully - adaptive lighting resumed")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        global_data = self.coordinator.data.get("global", {})

        return {
            "current_mode": global_data.get("current_mode", "default"),
            "zones_count": len(self.coordinator.zones),
            "paused": global_data.get("paused", False),
        }


class ALPWakeSequenceSwitch(ALPEntity, SwitchEntity):
    """Switch to enable/disable wake sequence feature.

    This switch allows users to temporarily disable wake sequences
    for weekends or vacation without losing alarm configuration.

    Entity ID: switch.alp_wake_sequence_enabled
    Display Name: "Wake Sequence"

    State:
    - ON: Wake sequences will activate before alarms
    - OFF: Wake sequences disabled (alarms still tracked)

    Behavior:
    - turn_on: Calls coordinator.set_wake_sequence_enabled(True)
    - turn_off: Calls coordinator.set_wake_sequence_enabled(False)
    - is_on: Reads from coordinator.get_wake_sequence_enabled()
    """

    _attr_icon = "mdi:alarm-light"

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize wake sequence enable switch.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
        """
        super().__init__(
            coordinator,
            entry,
            "switch",
            "wake_sequence_enabled",
            "Wake Sequence",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if wake sequence is enabled.

        Returns:
            True if wake sequence enabled, False if disabled, None if unknown
        """
        return self.coordinator.get_wake_sequence_enabled()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable wake sequence feature.

        Args:
            **kwargs: Additional arguments (not used)
        """
        _LOGGER.info("Enabling wake sequence feature")
        await self.coordinator.set_wake_sequence_enabled(True)
        _LOGGER.debug("Wake sequence enabled successfully")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable wake sequence feature.

        Args:
            **kwargs: Additional arguments (not used)
        """
        _LOGGER.info("Disabling wake sequence feature")
        await self.coordinator.set_wake_sequence_enabled(False)
        _LOGGER.debug("Wake sequence disabled successfully")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        # ARCHITECTURAL FIX: Use coordinator API instead of accessing internals
        wake_alarm = self.coordinator.get_next_alarm_time()
        wake_start = self.coordinator.get_wake_start_time()
        wake_state = self.coordinator.get_wake_sequence_state()

        return {
            "next_alarm": wake_alarm.isoformat() if wake_alarm else None,
            "wake_start_time": wake_start.isoformat() if wake_start else None,
            "duration_minutes": wake_state.get("duration_seconds", 0) / 60,
            "active_now": wake_state.get("active", False),
        }
