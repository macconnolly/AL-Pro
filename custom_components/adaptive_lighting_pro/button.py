"""Button entities for Adaptive Lighting Pro."""
from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import AdaptiveLightingProEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AdaptiveLightingProForceSyncButton(runtime),
            AdaptiveLightingProResetButton(runtime),
            AdaptiveLightingProSceneResetButton(runtime),
            AdaptiveLightingProBackupButton(runtime),
            AdaptiveLightingProRestoreButton(runtime),
        ]
    )


class AdaptiveLightingProButtonBase(AdaptiveLightingProEntity, ButtonEntity):
    async def async_press(self) -> None:
        await self._async_handle()

    async def _async_handle(self) -> None:
        raise NotImplementedError


class AdaptiveLightingProForceSyncButton(AdaptiveLightingProButtonBase):
    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Force Sync", "alp_force_sync_button")

    async def _async_handle(self) -> None:
        await self._runtime.force_sync()


class AdaptiveLightingProResetButton(AdaptiveLightingProButtonBase):
    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Reset", "alp_reset_button")

    async def _async_handle(self) -> None:
        for zone_id in self._runtime.zone_states().keys():
            await self._runtime.reset_zone(zone_id)


class AdaptiveLightingProSceneResetButton(AdaptiveLightingProButtonBase):
    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Scene Reset", "alp_scene_reset_button")

    async def _async_handle(self) -> None:
        await self._runtime.select_scene("default")


class AdaptiveLightingProBackupButton(AdaptiveLightingProButtonBase):
    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Backup Preferences", "alp_backup_button")

    async def _async_handle(self) -> None:
        await self._runtime.backup_prefs()


class AdaptiveLightingProRestoreButton(AdaptiveLightingProButtonBase):
    def __init__(self, runtime) -> None:
        super().__init__(runtime, "ALP Restore Preferences", "alp_restore_button")

    async def _async_handle(self) -> None:
        await self._runtime.restore_prefs()
