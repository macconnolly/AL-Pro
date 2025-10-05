"""Select entities for Adaptive Lighting Pro."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MODE_SELECT_ID, SCENE_SELECT_ID, DEFAULT_SCENE_ORDER
from .entity import AdaptiveLightingProEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AdaptiveLightingProModeSelect(runtime),
            AdaptiveLightingProSceneSelect(runtime),
        ]
    )


class AdaptiveLightingProModeSelect(AdaptiveLightingProEntity, SelectEntity):
    """Select for modes."""

    _attr_entity_id = MODE_SELECT_ID

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Mode", MODE_SELECT_ID)

    @property
    def options(self) -> list[str]:
        return self._runtime.available_modes()

    @property
    def current_option(self) -> str:
        return self._runtime.current_mode()

    async def async_select_option(self, option: str) -> None:
        await self._runtime.select_mode(option)

    def _handle_update(self) -> None:
        self._attr_options = self._runtime.available_modes()
        super()._handle_update()


class AdaptiveLightingProSceneSelect(AdaptiveLightingProEntity, SelectEntity):
    """Select for scenes."""

    _attr_entity_id = SCENE_SELECT_ID

    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Scene", SCENE_SELECT_ID)

    @property
    def options(self) -> list[str]:
        options = self._runtime.available_scenes()
        return options or DEFAULT_SCENE_ORDER

    @property
    def current_option(self) -> str:
        return self._runtime.current_scene()

    async def async_select_option(self, option: str) -> None:
        await self._runtime.select_scene(option)

    def _handle_update(self) -> None:
        self._attr_options = self.options
        super()._handle_update()
