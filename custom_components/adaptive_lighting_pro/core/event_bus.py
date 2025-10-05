"""Internal event bus for Adaptive Lighting Pro."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List

from homeassistant.components import logbook
from homeassistant.core import CALLBACK_TYPE, HomeAssistant

from ..const import DOMAIN
from ..utils.logger import log_debug

EventCallback = Callable[..., Awaitable[None] | None]


class EventBus:
    """Simple async event bus."""

    def __init__(self, hass: HomeAssistant, *, debug: bool, trace: bool) -> None:
        self._hass = hass
        self._debug = debug
        self._trace = trace
        self._subscribers: Dict[str, List[EventCallback]] = defaultdict(list)

    def subscribe(self, event: str, callback: EventCallback) -> CALLBACK_TYPE:
        self._subscribers[event].append(callback)

        def _unsubscribe() -> None:
            self._subscribers[event].remove(callback)

        return _unsubscribe

    def post(self, event: str, **data: Any) -> None:
        log_debug(self._debug, "Event posted %s %s", event, data)
        if self._trace:
            logbook.async_log_entry(
                self._hass,
                name="Adaptive Lighting Pro",
                message=f"{event}",
                domain=DOMAIN,
                entity_id=None,
                context_id=None,
                extra=data,
            )
        for callback in list(self._subscribers.get(event, [])):
            self._schedule(callback, data)

    def _schedule(self, callback: EventCallback, data: Dict[str, Any]) -> None:
        async def _invoke() -> None:
            result = callback(**data)
            if asyncio.iscoroutine(result):
                await result

        self._hass.async_create_task(_invoke())
