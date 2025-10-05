"""Zen32 controller handler."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, TYPE_CHECKING

from homeassistant.core import Event, HomeAssistant

from ..const import EVENT_BUTTON_PRESSED, ZEN32_DEBOUNCE_MS
from ..utils.logger import log_debug

if TYPE_CHECKING:
    from ..core.event_bus import EventBus


@dataclass
class Zen32Config:
    device_id: str
    debug: bool


@dataclass
class Zen32Handler:
    hass: HomeAssistant
    event_bus: "EventBus"
    config: Zen32Config
    _last_seen: Dict[str, float] = field(default_factory=dict)

    def start(self) -> None:
        if not self.config.device_id:
            return
        self.hass.bus.async_listen("zwave_js.scene_activated", self._handle_event)

    async def _handle_event(self, event: Event) -> None:
        device_id = event.data.get("device_id")
        if device_id != self.config.device_id:
            return
        button = str(event.data.get("property_key_name") or event.data.get("label") or "")
        action = str(event.data.get("event"))
        key = f"{button}:{action}"
        now = time.monotonic() * 1000
        last = self._last_seen.get(key, 0)
        if now - last < ZEN32_DEBOUNCE_MS:
            log_debug(self.config.debug, "Dropping Zen32 duplicate event %s", key)
            return
        self._last_seen[key] = now
        payload = {
            "device": "zen32",
            "button": button,
            "action": action,
        }
        log_debug(self.config.debug, "Zen32 event %s", payload)
        self.event_bus.post(EVENT_BUTTON_PRESSED, **payload)
