"""Base entity class for the Adaptive Lighting Pro integration.

This module provides the ALPEntity base class that all ALP entities should inherit from.
It handles common functionality like coordinator integration, device info, and entity naming.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .coordinator import ALPDataUpdateCoordinator


class ALPEntity(CoordinatorEntity["ALPDataUpdateCoordinator"]):
    """Base class for all Adaptive Lighting Pro entities.

    This class provides common functionality for all entities in the integration:
    - Coordinator integration for automatic updates
    - Device association for grouping in the UI
    - Consistent naming and identification
    - Availability tracking

    All platform entities (switch, number, select, etc.) should inherit from this class.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        entry: ConfigEntry,
        entity_type: str,
        entity_id_suffix: str,
        name_suffix: str | None = None,
    ) -> None:
        """Initialize the ALP entity.

        Args:
            coordinator: The data update coordinator that manages state updates
            entry: The config entry this entity belongs to
            entity_type: Type of entity (e.g., "switch", "number", "select")
            entity_id_suffix: Suffix for the entity's unique ID (e.g., "main_switch")
            name_suffix: Optional suffix for the entity's display name.
                        If None, will use entity_id_suffix converted to title case.
        """
        super().__init__(coordinator)

        self._entry = entry
        self._entity_type = entity_type
        self._entity_id_suffix = entity_id_suffix

        # Generate display name
        if name_suffix is None:
            # Convert entity_id_suffix to title case (e.g., "main_switch" -> "Main Switch")
            name_suffix = entity_id_suffix.replace("_", " ").title()

        self._attr_name = name_suffix

        # Generate unique ID: {domain}_{entry_id}_{entity_type}_{suffix}
        # Example: adaptive_lighting_pro_abc123_switch_main_living
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{entity_type}_{entity_id_suffix}"

        # Associate this entity with the integration's device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Adaptive Lighting Pro",
            manufacturer="Adaptive Lighting Pro",
            model="ALP v1.0",
            sw_version="1.0.0",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available.

        An entity is available if:
        1. The coordinator's last update was successful
        2. The coordinator has data

        This ensures entities show as unavailable in the UI if there are
        communication issues with the Adaptive Lighting integration.
        """
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes.

        Can be overridden by child classes to add entity-specific attributes.
        Base implementation returns None (no extra attributes).
        """
        return None


class ALPZoneEntity(ALPEntity):
    """Base class for zone-specific ALP entities.

    This specialized entity class is for entities that belong to a specific zone
    (e.g., zone-specific switches, numbers, or sensors).
    """

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        entry: ConfigEntry,
        zone_id: str,
        entity_type: str,
        entity_id_suffix: str,
        name_suffix: str | None = None,
    ) -> None:
        """Initialize the zone-specific ALP entity.

        Args:
            coordinator: The data update coordinator that manages state updates
            entry: The config entry this entity belongs to
            zone_id: The zone this entity belongs to (e.g., "main_living")
            entity_type: Type of entity (e.g., "switch", "number", "select")
            entity_id_suffix: Suffix for the entity's unique ID (e.g., "manual_timer")
            name_suffix: Optional suffix for the entity's display name.
                        If None, will use entity_id_suffix converted to title case.
        """
        self._zone_id = zone_id

        # Include zone_id in the entity ID for uniqueness
        # Example: adaptive_lighting_pro_abc123_switch_main_living_manual_timer
        full_suffix = f"{zone_id}_{entity_id_suffix}"

        # If no name suffix provided, use zone name + entity suffix
        if name_suffix is None:
            # Get zone name from config or fall back to zone_id
            zone_name = self._get_zone_name(entry, zone_id)
            entity_name = entity_id_suffix.replace("_", " ").title()
            name_suffix = f"{zone_name} {entity_name}"

        super().__init__(
            coordinator=coordinator,
            entry=entry,
            entity_type=entity_type,
            entity_id_suffix=full_suffix,
            name_suffix=name_suffix,
        )

    @staticmethod
    def _get_zone_name(entry: ConfigEntry, zone_id: str) -> str:
        """Get the display name for a zone from config entry.

        Args:
            entry: The config entry containing zone definitions
            zone_id: The zone ID to look up

        Returns:
            The zone's display name, or zone_id as title case if not found
        """
        zones = entry.data.get("zones", [])
        for zone in zones:
            if zone.get("zone_id") == zone_id:
                return zone.get("zone_name", zone_id.replace("_", " ").title())

        # Fallback to converting zone_id to title case
        return zone_id.replace("_", " ").title()

    @property
    def zone_id(self) -> str:
        """Return the zone ID this entity belongs to."""
        return self._zone_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return zone-specific state attributes.

        Includes the zone_id as an attribute for debugging and automation purposes.
        Child classes can override this to add more attributes.
        """
        return {
            "zone_id": self._zone_id,
        }
