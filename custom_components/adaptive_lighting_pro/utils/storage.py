"""Storage adapter that falls back when HA storage is unavailable."""
from __future__ import annotations

import sys
from importlib import import_module, util
from typing import Any, Dict, Optional


class StorageAdapter:
    """Provide Home Assistant storage when available with an in-memory fallback."""

    _FALLBACK_DOMAIN = "adaptive_lighting_pro_storage"

    def __init__(self, hass, version: int, key: str) -> None:
        self._hass = hass
        self._key = key
        self._store = self._resolve_store(hass, version, key)

    @classmethod
    def _resolve_store(cls, hass, version: int, key: str):
        base_module = sys.modules.get("homeassistant.helpers")
        if base_module is not None and getattr(base_module, "__spec__", None) is None:
            hass.data.setdefault(cls._FALLBACK_DOMAIN, {})
            hass.data[cls._FALLBACK_DOMAIN].setdefault(key, None)
            return None
        spec = util.find_spec("homeassistant.helpers.storage")
        if spec is None:
            hass.data.setdefault(cls._FALLBACK_DOMAIN, {})
            hass.data[cls._FALLBACK_DOMAIN].setdefault(key, None)
            return None
        module = import_module("homeassistant.helpers.storage")
        store_cls = getattr(module, "Store", None)
        if store_cls is None:
            hass.data.setdefault(cls._FALLBACK_DOMAIN, {})
            hass.data[cls._FALLBACK_DOMAIN].setdefault(key, None)
            return None
        return store_cls(hass, version, key)

    async def async_save(self, data: Dict[str, Any]) -> None:
        if self._store is not None:
            await self._store.async_save(data)
            return
        storage = self._hass.data.setdefault(self._FALLBACK_DOMAIN, {})
        storage[self._key] = data

    async def async_load(self) -> Optional[Dict[str, Any]]:
        if self._store is not None:
            return await self._store.async_load()
        storage = self._hass.data.setdefault(self._FALLBACK_DOMAIN, {})
        return storage.get(self._key)
