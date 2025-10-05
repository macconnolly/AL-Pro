from __future__ import annotations

import asyncio
from typing import List

from custom_components.adaptive_lighting_pro.const import (
    CONF_SCENES,
    CONF_SENSORS,
    CONF_ZONES,
)
from custom_components.adaptive_lighting_pro.core.runtime import AdaptiveLightingProRuntime
from tests.conftest import ConfigEntry, HomeAssistant, State


async def _setup_runtime(
    hass: HomeAssistant,
    zones: List[dict],
    sensors: dict | None = None,
) -> AdaptiveLightingProRuntime:
    for zone in zones:
        if zone["al_switch"] not in hass.states:
            hass.states[zone["al_switch"]] = State(
                "on", {"integration": "adaptive_lighting"}
            )
    entry = ConfigEntry(
        data={CONF_ZONES: zones, CONF_SENSORS: sensors or {}},
        options={},
    )
    runtime = AdaptiveLightingProRuntime(hass, entry)
    await runtime.async_setup()
    return runtime


def test_adjust_service_applies_deltas_and_triggers_manual(hass: HomeAssistant) -> None:
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
        hass.states["light.one"] = State(
            "on",
            {
                "brightness": 128,
                "color_temp": 370,
            },
        )
        runtime = await _setup_runtime(hass, zones)

        apply_calls: list[tuple[str, dict]] = []
        manual_calls: list[tuple[str, bool]] = []

        async def fake_apply(entity_id: str, data: dict) -> dict:
            apply_calls.append((entity_id, data))
            return {"status": "ok", "duration_ms": 15}

        async def fake_manual(entity_id: str, manual: bool) -> dict:
            manual_calls.append((entity_id, manual))
            return {"status": "ok"}

        runtime._executors.apply = fake_apply  # type: ignore[assignment]
        runtime._executors.set_manual_control = fake_manual  # type: ignore[assignment]

        result = await runtime.adjust(step_brightness_pct=10, step_color_temp=-200)
        await asyncio.sleep(0.1)

        assert result["status"] == "ok"
        assert apply_calls
        entity_id, data = apply_calls[0]
        assert entity_id == "switch.living"
        assert data["brightness_pct"] == 60
        assert data["context"]["brightness_step_pct"] == 10
        assert data["context"]["color_temp_step"] == -200
        assert data["context"]["color_temp_target_kelvin"] == data["color_temp_kelvin"]
        assert manual_calls and manual_calls[0] == ("switch.living", True)
        assert runtime._zone_manager.manual_active("living")
        flags = runtime.manual_action_flags()
        assert flags["brighter"] is True
        assert flags["warmer"] is True

    hass.loop.run_until_complete(scenario())


def test_scene_presets_apply_expected_payload(hass: HomeAssistant) -> None:
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
        hass.states["light.one"] = State("on", {"brightness": 200, "color_temp": 300})
        runtime = await _setup_runtime(hass, zones)

        apply_calls: list[tuple[str, dict]] = []
        manual_calls: list[tuple[str, bool]] = []

        async def fake_apply(entity_id: str, data: dict) -> dict:
            apply_calls.append((entity_id, data))
            return {"status": "ok"}

        async def fake_manual(entity_id: str, manual: bool) -> dict:
            manual_calls.append((entity_id, manual))
            return {"status": "ok"}

        runtime._executors.apply = fake_apply  # type: ignore[assignment]
        runtime._executors.set_manual_control = fake_manual  # type: ignore[assignment]

        await runtime.select_scene("evening_comfort")
        await asyncio.sleep(0.05)
        assert apply_calls
        _, data = apply_calls.pop(0)
        assert data["brightness_pct"] == 50
        assert data["color_temp_kelvin"] == 2300
        assert data["context"]["scene"] == "evening_comfort"
        assert data["adapt_brightness"] is False
        assert data["context"]["scene_offsets"] == {"brightness": -5, "warmth": -500}
        assert manual_calls and manual_calls[-1] == ("switch.living", True)
        assert runtime._zone_manager.manual_active("living")
        flags = runtime.manual_action_flags()
        assert flags["dimmer"] is True
        assert flags["warmer"] is True

        result_default = await runtime.select_scene("default")
        await asyncio.sleep(0.05)
        assert result_default["status"] == "ok"
        assert result_default["cleared"] == 1
        _, default_data = apply_calls.pop(0)
        assert default_data["adapt_brightness"] is True
        assert default_data["adapt_color_temp"] is True
        assert "brightness_pct" not in default_data
        assert manual_calls and manual_calls[-1] == ("switch.living", False)
        assert not runtime._zone_manager.manual_active("living")
        flags = runtime.manual_action_flags()
        assert not any(flags.values())
        if apply_calls:
            _, sync_payload = apply_calls.pop(0)
            assert sync_payload.get("context", {}).get("source") != "alp_scene"

        # Scene offsets can be tuned dynamically
        runtime.set_scene_brightness_offset(10)
        runtime.set_scene_warmth_offset(-200)
        assert runtime.scene_brightness_offset() == 10
        assert runtime.scene_warmth_offset() == -200
        flags_after_override = runtime.manual_action_flags()
        assert flags_after_override["brighter"] is True
        assert flags_after_override["warmer"] is True

        await asyncio.sleep(0.05)
        apply_calls.clear()
        await runtime.select_scene("evening_comfort")
        await asyncio.sleep(0.05)
        assert apply_calls
        _, boosted_data = apply_calls.pop(0)
        assert boosted_data["brightness_pct"] == 60
        assert boosted_data["color_temp_kelvin"] == 2100
        assert boosted_data["context"]["scene_offsets"] == {"brightness": 5, "warmth": -700}
        assert boosted_data["context"]["scene_user_offsets"] == {
            "brightness": 10,
            "warmth": -200,
        }
        assert hass._config_entry_updates
        latest_options = hass._config_entry_updates[-1]["options"]
        assert latest_options[CONF_SCENES]["offsets"]["brightness"] == 10
        assert latest_options[CONF_SCENES]["offsets"]["warmth"] == -200

        runtime._zone_manager.set_manual("living", True, 30)
        await runtime.select_scene("ultra_dim")
        assert not apply_calls

    hass.loop.run_until_complete(scenario())


def test_force_sync_rate_limit_flag_across_zones(hass: HomeAssistant) -> None:
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
                "zone_id": "kitchen",
                "al_switch": "switch.kitchen",
                "lights": ["light.two"],
                "enabled": True,
                "zone_multiplier": 1.0,
                "sunrise_offset_min": 0,
                "environmental_boost_enabled": True,
                "sunset_boost_enabled": True,
            },
        ]
        hass.states["light.one"] = State("on", {"brightness": 200})
        hass.states["light.two"] = State("on", {"brightness": 200})
        runtime = await _setup_runtime(hass, zones)

        responses: List[dict] = []

        async def fake_apply(entity_id: str, data: dict) -> dict:
            return responses.pop(0)

        runtime._executors.apply = fake_apply  # type: ignore[assignment]

        responses.extend(
            [
                {"status": "error", "error_code": "RATE_LIMITED", "duration_ms": 0},
                {"status": "ok", "duration_ms": 12},
            ]
        )
        first_result = await runtime.force_sync()
        assert first_result["status"] == "ok"
        assert runtime.rate_limit_reached() is True
        assert first_result["results"][0]["error_code"] == "RATE_LIMITED"

        assert not responses
        responses.extend(
            [
                {"status": "ok", "duration_ms": 8},
                {"status": "ok", "duration_ms": 7},
            ]
        )
        second_result = await runtime.force_sync()
        assert second_result["status"] == "ok"
        assert runtime.rate_limit_reached() is False

    hass.loop.run_until_complete(scenario())
