import asyncio

import pytest

from custom_components.adaptive_lighting_pro.const import (
    CONF_ENV_BOOST,
    CONF_ZONES,
    EVENT_ENVIRONMENTAL_CHANGED,
    EVENT_MANUAL_DETECTED,
    EVENT_TIMER_EXPIRED,
)
from custom_components.adaptive_lighting_pro.core.runtime import AdaptiveLightingProRuntime
from tests.conftest import ConfigEntry, HomeAssistant, State


async def _setup_runtime(hass: HomeAssistant, zones: list[dict]) -> AdaptiveLightingProRuntime:
    for zone in zones:
        if zone["al_switch"] not in hass.states:
            hass.states[zone["al_switch"]] = State(
                "on", {"integration": "adaptive_lighting"}
            )
    entry = ConfigEntry(data={CONF_ZONES: zones}, options={CONF_ENV_BOOST: 0.5})
    runtime = AdaptiveLightingProRuntime(hass, entry)
    await runtime.async_setup()
    return runtime


def test_environmental_boost_respects_mode_and_zone(hass: HomeAssistant) -> None:
    async def scenario() -> None:
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
            },
            {
                "zone_id": "bed",
                "al_switch": "switch.bed",
                "lights": ["light.two"],
                "enabled": True,
                "zone_multiplier": 1.0,
                "sunrise_offset_min": 0,
                "environmental_boost_enabled": False,
                "sunset_boost_enabled": True,
            },
        ]
        runtime = await _setup_runtime(hass, zones)
        await runtime.select_mode("late_night")
        runtime._event_bus.post(EVENT_ENVIRONMENTAL_CHANGED, boost_active=True)
        await asyncio.sleep(0.1)
        non_adaptive_duration = runtime._timer_manager.compute_duration_seconds("living")
        await runtime.select_mode("adaptive")
        runtime._event_bus.post(EVENT_ENVIRONMENTAL_CHANGED, boost_active=True)
        await asyncio.sleep(0.1)
        adaptive_duration = runtime._timer_manager.compute_duration_seconds("living")
        runtime._timer_manager.set_environment(False)
        baseline_bed = runtime._timer_manager.compute_duration_seconds("bed")
        runtime._timer_manager.set_environment(True)
        bed_duration = runtime._timer_manager.compute_duration_seconds("bed")
        assert non_adaptive_duration > adaptive_duration
        assert bed_duration == baseline_bed

    hass.loop.run_until_complete(scenario())


def test_manual_override_restores_mode(hass: HomeAssistant) -> None:
    async def scenario() -> None:
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
        runtime = await _setup_runtime(hass, zones)
        await runtime.select_mode("late_night")

        async def fake_manual(entity_id: str, manual: bool) -> dict:
            return {"status": "ok"}

        runtime._executors.set_manual_control = fake_manual  # type: ignore[assignment]
        runtime.force_sync = lambda zone=None: asyncio.sleep(0)  # type: ignore[assignment]
        runtime._event_bus.post(EVENT_MANUAL_DETECTED, zone="living", duration_s=5)
        await asyncio.sleep(0.1)
        assert runtime._mode_manager.mode == "adaptive"
        assert runtime._previous_mode == "late_night"
        runtime._event_bus.post(EVENT_TIMER_EXPIRED, zone="living")
        await asyncio.sleep(0.1)
        assert runtime._mode_manager.mode == "late_night"
        assert runtime._previous_mode is None

    hass.loop.run_until_complete(scenario())


def test_scene_blocked_outside_adaptive(hass: HomeAssistant) -> None:
    async def scenario() -> None:
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
        runtime = await _setup_runtime(hass, zones)
        await runtime.select_mode("movie")
        result = await runtime.select_scene("default")
        assert result["error_code"] == "MODE_BLOCKED"
        await runtime.select_mode("adaptive")
        result_ok = await runtime.select_scene("default")
        assert result_ok["status"] == "ok"

    hass.loop.run_until_complete(scenario())


def test_mode_alias_resolution(hass: HomeAssistant) -> None:
    async def scenario() -> None:
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
        runtime = await _setup_runtime(hass, zones)
        assert "Bright Focus" in runtime.available_modes()
        result = await runtime.select_mode("Bright Focus")
        assert result["mode"] == "focus"
        assert runtime.current_mode() == "focus"
        # Alias lookup should be case-insensitive
        await runtime.select_mode("dim relax")
        assert runtime.current_mode() == "relax"

    hass.loop.run_until_complete(scenario())


def test_sunset_boost_respects_zone_flags(hass: HomeAssistant) -> None:
    async def scenario() -> None:
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
            },
            {
                "zone_id": "bed",
                "al_switch": "switch.bed",
                "lights": ["light.two"],
                "enabled": True,
                "zone_multiplier": 1.0,
                "sunrise_offset_min": 0,
                "environmental_boost_enabled": True,
                "sunset_boost_enabled": False,
            },
        ]
        hass.states["switch.living"] = State(
            "on",
            {
                "integration": "adaptive_lighting",
                "min_brightness": 40,
                "max_brightness": 80,
                "min_color_temp": 2200,
                "max_color_temp": 4000,
            },
        )
        hass.states["switch.bed"] = State(
            "on",
            {
                "integration": "adaptive_lighting",
                "min_brightness": 20,
                "max_brightness": 45,
                "min_color_temp": 2000,
                "max_color_temp": 3500,
            },
        )
        runtime = await _setup_runtime(hass, zones)

        calls: list[tuple[str, dict]] = []

        async def fake_change(entity_id: str, data: dict) -> dict:
            calls.append((entity_id, data))
            return {"status": "ok"}

        runtime._executors.change_switch_settings = fake_change  # type: ignore[assignment]

        await runtime._handle_environmental_changed(True, sunset_boost_pct=12)
        await asyncio.sleep(0.1)

        assert any(call[0] == "switch.living" for call in calls)
        for entity_id, data in calls:
            if entity_id == "switch.living":
                assert data["min_brightness"] >= 40
                assert data["min_brightness"] <= 75
            if entity_id == "switch.bed":
                pytest.fail("Sunset boost should skip zones with sunset disabled")

    hass.loop.run_until_complete(scenario())
