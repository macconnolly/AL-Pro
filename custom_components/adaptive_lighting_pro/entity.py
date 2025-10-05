"""Base entities for Adaptive Lighting Pro."""
from __future__ import annotations

from typing import Callable

from homeassistant.helpers.entity import Entity

class AdaptiveLightingProEntity(Entity):
    """Base entity with runtime subscription."""

    _attr_should_poll = False

    def __init__(self, runtime, name: str, unique_id: str) -> None:
        self._runtime = runtime
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._remove_callback: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        self._remove_callback = self._runtime.register_entity_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_callback:
            self._remove_callback()
            self._remove_callback = None

    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def device_info(self) -> dict:
        return self._runtime.device_info()
