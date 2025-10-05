"""Tests for the Adaptive Lighting Pro config flow."""
from __future__ import annotations

import asyncio

from custom_components.adaptive_lighting_pro.config_flow import AdaptiveLightingProConfigFlow
from custom_components.adaptive_lighting_pro.const import (
    CONF_CONTROLLERS,
    CONF_LUX_SENSOR,
    CONF_SENSORS,
    CONF_SONOS_SENSOR,
    CONF_WEATHER_ENTITY,
    CONF_ZEN32_DEVICE,
)
from tests.conftest import HomeAssistant, State


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def resolve(result):
    value = run(result)
    if asyncio.iscoroutine(value):
        value = run(value)
    return value


def test_config_flow_valid(hass: HomeAssistant) -> None:
    hass.states["switch.living_al"] = State("on", {"integration": "adaptive_lighting"})
    flow = AdaptiveLightingProConfigFlow()
    flow.hass = hass
    user_input = {
        "zones": [
            {
                "zone_id": "living",
                "al_switch": "switch.living_al",
                "lights": ["light.a"],
            }
        ]
    }
    result = resolve(flow.async_step_user(user_input))
    assert result["type"] == "create_entry"
    assert result["data"]["zones"][0]["zone_id"] == "living"


def test_config_flow_collects_optional_fields(hass: HomeAssistant) -> None:
    hass.states["switch.living_al"] = State("on", {"integration": "adaptive_lighting"})
    flow = AdaptiveLightingProConfigFlow()
    flow.hass = hass
    user_input = {
        "zones": [
            {
                "zone_id": "living",
                "al_switch": "switch.living_al",
                "lights": ["light.a"],
            }
        ],
        CONF_LUX_SENSOR: "sensor.lux",
        CONF_WEATHER_ENTITY: "weather.home",
        CONF_SONOS_SENSOR: "sensor.sonos",
        CONF_ZEN32_DEVICE: "device-123",
    }
    result = resolve(flow.async_step_user(user_input))
    assert result["type"] == "create_entry"
    sensors = result["data"][CONF_SENSORS]
    controllers = result["data"][CONF_CONTROLLERS]
    assert sensors[CONF_LUX_SENSOR] == "sensor.lux"
    assert sensors[CONF_WEATHER_ENTITY] == "weather.home"
    assert sensors[CONF_SONOS_SENSOR] == "sensor.sonos"
    assert controllers[CONF_ZEN32_DEVICE] == "device-123"


def test_config_flow_rejects_non_adaptive_switch(hass: HomeAssistant) -> None:
    hass.states["switch.bad"] = State("on", {"integration": "other"})
    flow = AdaptiveLightingProConfigFlow()
    flow.hass = hass
    user_input = {
        "zones": [
            {
                "zone_id": "living",
                "al_switch": "switch.bad",
                "lights": ["light.a"],
            }
        ]
    }
    result = resolve(flow.async_step_user(user_input))
    assert result["type"] == "form"
    assert "al_switch" in result["errors"]


def test_config_flow_duplicate_zone(hass: HomeAssistant) -> None:
    hass.states["switch.one"] = State("on", {"integration": "adaptive_lighting"})
    hass.states["switch.two"] = State("on", {"integration": "adaptive_lighting"})
    flow = AdaptiveLightingProConfigFlow()
    flow.hass = hass
    user_input = {
        "zones": [
            {
                "zone_id": "zone",
                "al_switch": "switch.one",
                "lights": ["light.a"],
            },
            {
                "zone_id": "zone",
                "al_switch": "switch.two",
                "lights": ["light.b"],
            },
        ]
    }
    result = resolve(flow.async_step_user(user_input))
    assert result["type"] == "form"
    assert result["errors"].get("zone_id")
