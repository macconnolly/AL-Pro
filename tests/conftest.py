"""Pytest fixtures and Home Assistant stubs for Adaptive Lighting Pro tests."""
from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, Optional

import pytest

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# --- Minimal Home Assistant stub modules ---

homeassistant = types.ModuleType("homeassistant")
config_entries = types.ModuleType("homeassistant.config_entries")
helpers = types.ModuleType("homeassistant.helpers")
helpers_event = types.ModuleType("homeassistant.helpers.event")
helpers_typing = types.ModuleType("homeassistant.helpers.typing")
components = types.ModuleType("homeassistant.components")
components_logbook = types.ModuleType("homeassistant.components.logbook")
components_logbook.async_log_entry = lambda hass, **kwargs: None
util_module = types.ModuleType("homeassistant.util")
util_dt_module = types.ModuleType("homeassistant.util.dt")
vol_module = types.ModuleType("voluptuous")


def _dt_now():
    return datetime.utcnow()


util_dt_module.now = _dt_now
util_module.dt = util_dt_module


class DummySchema:
    def __init__(self, schema):
        self.schema = schema

    def __call__(self, value):
        return value


vol_module.Schema = DummySchema
vol_module.Required = lambda key, default=None: key
vol_module.Optional = lambda key, default=None: key


class ConfigFlow:
    def __init_subclass__(cls, **kwargs):
        kwargs.pop("domain", None)
        super().__init_subclass__()

    def async_show_form(self, *, step_id: str, data_schema=None, errors=None):
        return {"type": "form", "step_id": step_id, "errors": errors or {}, "schema": data_schema}

    def async_create_entry(self, *, title: str, data: dict):
        return {"type": "create_entry", "title": title, "data": data}


class OptionsFlow:
    def async_show_form(self, *, step_id: str, data_schema=None):
        return {"type": "form", "step_id": step_id, "schema": data_schema}

    def async_create_entry(self, *, title: str, data: dict):
        return {"type": "create_entry", "title": title, "data": data}


@dataclass
class ConfigEntry:
    data: dict
    options: dict
    entry_id: str = "test"

    def add_update_listener(self, listener: Callable):
        return listener


config_entries.ConfigFlow = ConfigFlow
config_entries.OptionsFlow = OptionsFlow
config_entries.ConfigEntry = ConfigEntry


@dataclass
class State:
    state: str
    attributes: dict


class StateMachine(dict):
    def get(self, entity_id: str) -> Optional[State]:  # type: ignore[override]
        return super().get(entity_id)


class ServiceRegistry:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.handlers: dict[tuple[str, str], Callable] = {}

    async def async_call(self, domain: str, service: str, data: dict, blocking: bool = False) -> None:
        self.calls.append((domain, service, data))
        handler = data.get("_handler")
        if handler:
            result = handler()
            if asyncio.iscoroutine(result):
                await result

    def async_register(
        self,
        domain: str,
        service: str,
        handler: Callable,
        schema=None,
        supports_response: bool = False,
    ) -> None:
        self.handlers[(domain, service)] = handler


class EventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def async_fire(self, event_type: str, event_data: dict) -> None:
        self.events.append((event_type, event_data))

    def async_listen(self, event_type: str, callback: Callable):
        self.events.append(("listen", {"event": event_type}))


class HomeAssistant:
    def __init__(self) -> None:
        self.states = StateMachine()
        self.services = ServiceRegistry()
        self.bus = EventBus()
        self.data: Dict[str, Any] = {}
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.config = types.SimpleNamespace(time_zone="UTC")
        self._config_entry_updates: list[dict] = []
        self.config_entries = types.SimpleNamespace(
            async_update_entry=self._async_update_entry,
            async_forward_entry_setups=self._async_forward_entry_setups,
            async_unload_platforms=self._async_unload_platforms,
            async_forward_entry_unload=self._async_forward_entry_unload,
        )

    def async_create_task(self, coro: Awaitable) -> asyncio.Task:
        return asyncio.create_task(coro)

    def _async_update_entry(self, entry, *, data=None, options=None):
        if data is not None:
            entry.data = data
        if options is not None:
            entry.options = options
        self._config_entry_updates.append(
            {"entry": entry, "data": data, "options": options}
        )

    async def _async_forward_entry_setups(self, entry, platforms):
        return True

    async def _async_unload_platforms(self, entry, platforms):
        return True

    async def _async_forward_entry_unload(self, entry, platforms):
        return True


helpers_typing.ConfigType = dict


def _track_state_change_event(hass: HomeAssistant, entity_ids, action):
    def unsubscribe() -> None:
        pass

    return unsubscribe


def _track_point_in_time(hass: HomeAssistant, action: Callable, when: datetime):
    async def _fire() -> None:
        await action(datetime.utcnow())

    hass.loop.call_later(max(0, (when - datetime.utcnow()).total_seconds()), lambda: asyncio.create_task(_fire()))

    def unsubscribe() -> None:
        pass

    return unsubscribe


def _track_time_interval(hass: HomeAssistant, action: Callable, interval: timedelta):
    async def _fire() -> None:
        await action(datetime.utcnow())

    handle = hass.loop.call_later(interval.total_seconds(), lambda: asyncio.create_task(_fire()))

    def unsubscribe() -> None:
        handle.cancel()

    return unsubscribe


helpers_event.async_track_state_change_event = _track_state_change_event
helpers_event.async_track_point_in_time = _track_point_in_time
helpers_event.async_track_time_interval = _track_time_interval

helpers.event = helpers_event

homeassistant.config_entries = config_entries
homeassistant.helpers = helpers
homeassistant.helpers.event = helpers_event
homeassistant.helpers.typing = helpers_typing
homeassistant.components = components
homeassistant.components.logbook = components_logbook
homeassistant.util = util_module
homeassistant.util.dt = util_dt_module
homeassistant.core = types.ModuleType("homeassistant.core")
homeassistant.core.HomeAssistant = HomeAssistant
homeassistant.core.Event = types.SimpleNamespace
homeassistant.core.CALLBACK_TYPE = Callable


@dataclass
class ServiceCall:
    data: dict
    response: dict | None = None


homeassistant.core.ServiceCall = ServiceCall
homeassistant.core.callback = lambda func: func

sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.config_entries", config_entries)
sys.modules.setdefault("homeassistant.helpers", helpers)
sys.modules.setdefault("homeassistant.helpers.event", helpers_event)
sys.modules.setdefault("homeassistant.helpers.typing", helpers_typing)
sys.modules.setdefault("homeassistant.components", components)
sys.modules.setdefault("homeassistant.components.logbook", components_logbook)
sys.modules.setdefault("homeassistant.util", util_module)
sys.modules.setdefault("homeassistant.util.dt", util_dt_module)
sys.modules.setdefault("homeassistant.core", homeassistant.core)
sys.modules.setdefault("voluptuous", vol_module)


@pytest.fixture
def hass() -> HomeAssistant:
    return HomeAssistant()
