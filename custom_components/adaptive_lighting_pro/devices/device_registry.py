"""Device registry helpers."""
from __future__ import annotations

from homeassistant.helpers import device_registry as dr


def device_exists(hass, device_id: str) -> bool:
    """Return True if device id exists in HA registry."""
    registry = dr.async_get(hass)
    return registry.async_get(device_id) is not None
