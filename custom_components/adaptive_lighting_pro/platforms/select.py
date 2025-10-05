"""Select platform for Adaptive Lighting Pro.

This module provides scene selection dropdown for quick scene switching.
Scenes are shortcuts that apply offset adjustments and zone actions,
then get out of the way - they're actions, not competing states.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN, Scene
from .entity import ALPEntity

if TYPE_CHECKING:
    from ..coordinator import ALPDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Lighting Pro select entities.

    Creates the scene selector dropdown that provides quick access
    to the 4 practical scene presets.
    """
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: ALPDataUpdateCoordinator = (
        entry_data.get("coordinator") if isinstance(entry_data, dict) else entry_data
    )

    entities = [
        ALPSceneSelect(coordinator, config_entry),
    ]

    async_add_entities(entities)


class ALPSceneSelect(ALPEntity, SelectEntity):
    """Scene selection dropdown.

    Provides dead-simple access to the 4 practical scene presets:
    - All Lights: Everything normal
    - No Spotlights: Disable accent zones (reading/focus)
    - Evening Comfort: -30% brightness, -500K warmth (relaxation)
    - Ultra Dim: Minimal light for movie watching

    Scenes are actions that apply offsets and get out of the way.
    Manual adjustments layer cleanly on top.
    """

    _attr_icon = "mdi:palette-outline"

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the scene select entity."""
        super().__init__(
            coordinator,
            config_entry,
            "select",
            "scene",
            "Scene"
        )

        # Build options list from Scene enum (exclude DEFAULT for UI)
        self._attr_options = [
            scene.value for scene in Scene
            if scene != Scene.DEFAULT
        ]

    @property
    def current_option(self) -> str | None:
        """Return the currently selected scene.

        DEFAULT scene (pure adaptive lighting) is represented as ALL_LIGHTS
        in the UI since ALL_LIGHTS is the action that returns to adaptive.
        """
        current_scene = self.coordinator.get_current_scene()

        # DEFAULT means pure adaptive lighting (no scene active)
        # Show as ALL_LIGHTS since that's the user action to get there
        if current_scene == Scene.DEFAULT:
            return Scene.ALL_LIGHTS.value

        return current_scene.value

    async def async_select_option(self, option: str) -> None:
        """Apply the selected scene.

        Converts the option string back to Scene enum and applies it
        via the coordinator, which handles all the offset calculations
        and zone actions.

        Args:
            option: Scene value string (e.g., "evening_comfort")
        """
        try:
            # Convert string to Scene enum
            scene = Scene(option)

            _LOGGER.info("User selected scene via dropdown: %s", option)

            # Apply scene through coordinator
            success = await self.coordinator.apply_scene(scene)

            if not success:
                _LOGGER.error("Failed to apply scene: %s", option)
            elif self.hass is not None:
                # Trigger entity state update (only if registered with HA)
                self.async_write_ha_state()

        except ValueError:
            _LOGGER.error("Invalid scene option selected: %s", option)
