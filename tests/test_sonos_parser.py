"""Tests for Sonos alarm parsing."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.adaptive_lighting_pro.const import CONF_SENSORS, CONF_ZONES
from custom_components.adaptive_lighting_pro.core.runtime import AdaptiveLightingProRuntime
from custom_components.adaptive_lighting_pro.features.sonos_integration import find_next_alarm
from tests.conftest import ConfigEntry, HomeAssistant, State


@pytest.mark.parametrize(
    "attributes,state,expected",
    [
        (
            {"alarms": [{"datetime": "2030-05-01T06:30:00"}, {"time": "2030-05-01T05:45:00"}]},
            None,
            "2030-05-01T05:45:00",
        ),
        (
            {},
            "2030-05-01T07:00:00",
            "2030-05-01T07:00:00",
        ),
    ],
)
def test_find_next_alarm(attributes, state, expected) -> None:
    tz = ZoneInfo("UTC")
    now = datetime(2030, 5, 1, 0, 0, tzinfo=tz)
    result = find_next_alarm(now=now, tz=tz, state=state, attributes=attributes)
    assert result.isoformat().startswith(expected)


def test_find_next_alarm_filters_outside_window() -> None:
    tz = ZoneInfo("UTC")
    now = datetime(2030, 5, 1, 0, 0, tzinfo=tz)
    attributes = {"alarms": [{"datetime": "2030-05-03T05:00:00"}]}
    assert find_next_alarm(now=now, tz=tz, state=None, attributes=attributes) is None


def test_sonos_fallback_to_sun_anchor(hass: HomeAssistant) -> None:
    async def scenario() -> None:
        now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        sun_iso = (now + timedelta(hours=1)).isoformat()
        zones = [
            {
                "zone_id": "living",
                "al_switch": "switch.living",
                "lights": ["light.one"],
                "enabled": True,
                "zone_multiplier": 1.0,
                "sunrise_offset_min": 0,
                "environmental_boost_enabled": True,
                "sunset_boost_enabled": True,
            }
        ]
        hass.states["switch.living"] = State("on", {"integration": "adaptive_lighting"})
        hass.states["sun.sun"] = State(
            "below_horizon",
            {"next_rising": sun_iso},
        )
        entry = ConfigEntry(data={CONF_ZONES: zones, CONF_SENSORS: {}}, options={})
        runtime = AdaptiveLightingProRuntime(hass, entry)
        await runtime.async_setup()
        assert runtime._sonos._anchor is not None
        assert runtime._sonos._anchor.isoformat().startswith(sun_iso[:19])

    hass.loop.run_until_complete(scenario())


def test_sonos_skip_flag_uses_sun_and_clears(hass: HomeAssistant) -> None:
    async def scenario() -> None:
        now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        alarm_iso = (now + timedelta(minutes=45)).isoformat()
        sun_iso = (now + timedelta(hours=1)).isoformat()
        zones = [
            {
                "zone_id": "living",
                "al_switch": "switch.living",
                "lights": ["light.one"],
                "enabled": True,
                "zone_multiplier": 1.0,
                "sunrise_offset_min": 0,
                "environmental_boost_enabled": True,
                "sunset_boost_enabled": True,
            }
        ]
        hass.states["switch.living"] = State("on", {"integration": "adaptive_lighting"})
        hass.states["sensor.sonos"] = State(
            "ready",
            {"alarms": [{"datetime": alarm_iso}]},
        )
        hass.states["sun.sun"] = State(
            "below_horizon",
            {"next_rising": sun_iso},
        )
        entry = ConfigEntry(
            data={
                CONF_ZONES: zones,
                CONF_SENSORS: {"sonos_alarm_sensor": "sensor.sonos"},
            },
            options={}
        )
        runtime = AdaptiveLightingProRuntime(hass, entry)
        await runtime.async_setup()
        assert runtime._sonos._anchor is not None
        assert runtime._sonos._anchor.isoformat().startswith(alarm_iso[:19])
        runtime._sonos._skip_next = True
        runtime._sonos._evaluate()
        assert runtime._sonos._anchor is not None
        assert runtime._sonos._anchor.isoformat().startswith(sun_iso[:19])
        await runtime._sonos._check_anchor(runtime._sonos._anchor + timedelta(minutes=2))
        assert runtime._sonos._skip_next is False

    hass.loop.run_until_complete(scenario())
