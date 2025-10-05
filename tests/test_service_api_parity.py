import asyncio
from typing import List

from custom_components.adaptive_lighting_pro.const import CONF_SENSORS, CONF_ZONES
from custom_components.adaptive_lighting_pro.core.runtime import AdaptiveLightingProRuntime
from tests.conftest import ConfigEntry, HomeAssistant, State


async def _setup_runtime(
    hass: HomeAssistant,
    zones: List[dict],
    sensors: dict | None = None,
) -> AdaptiveLightingProRuntime:
    for zone in zones:
        if zone["al_switch"] not in hass.states:
            hass.states[zone["al_switch"]] = State("on", {"integration": "adaptive_lighting"})
    entry = ConfigEntry(
        data={CONF_ZONES: zones, CONF_SENSORS: sensors or {}},
        options={},
    )
    runtime = AdaptiveLightingProRuntime(hass, entry)
    await runtime.async_setup()
    return runtime


def test_force_sync_and_zone_toggle_services(hass: HomeAssistant) -> None:
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

        apply_calls: list[tuple[str, dict]] = []

        async def fake_apply(entity_id: str, data: dict) -> dict:
            apply_calls.append((entity_id, data))
            return {"status": "ok", "duration_ms": 5}

        runtime._executors.apply = fake_apply  # type: ignore[assignment]

        runtime._zone_manager.set_manual("living", True, 120)
        await runtime.force_sync("living")
        await asyncio.sleep(0.05)
        assert not apply_calls  # manual zones skip sync

        runtime._zone_manager.set_manual("living", False)
        await runtime.force_sync("living")
        await asyncio.sleep(0.05)
        assert apply_calls and apply_calls[-1][0] == "switch.living"

        apply_calls.clear()
        runtime._zone_manager.set_enabled("living", False)
        result_disable = await runtime.disable_zone("living")
        await asyncio.sleep(0.05)
        assert result_disable["status"] == "ok"
        assert not runtime._zone_manager.get_zone("living").enabled
        assert not apply_calls

        result_enable = await runtime.enable_zone("living")
        await asyncio.sleep(0.05)
        assert result_enable["status"] == "ok"
        assert runtime._zone_manager.get_zone("living").enabled
        assert apply_calls and apply_calls[-1][0] == "switch.living"

        apply_calls.clear()
        await runtime.force_sync()
        await asyncio.sleep(0.05)
        entities = [entity for entity, _ in apply_calls]
        assert "switch.living" in entities and "switch.kitchen" in entities

    hass.loop.run_until_complete(scenario())


def test_reset_zone_and_backup_restore_roundtrip(hass: HomeAssistant) -> None:
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

        manual_calls: list[tuple[str, bool]] = []
        apply_calls: list[tuple[str, dict]] = []

        async def fake_manual(entity_id: str, manual: bool) -> dict:
            manual_calls.append((entity_id, manual))
            return {"status": "ok"}

        async def fake_apply(entity_id: str, data: dict) -> dict:
            apply_calls.append((entity_id, data))
            return {"status": "ok"}

        runtime._executors.set_manual_control = fake_manual  # type: ignore[assignment]
        runtime._executors.apply = fake_apply  # type: ignore[assignment]

        runtime._zone_manager.set_manual("living", True, 180)
        reset_result = await runtime.reset_zone("living")
        await asyncio.sleep(0.05)
        assert reset_result["status"] == "ok"
        assert manual_calls and manual_calls[-1] == ("switch.living", False)
        assert apply_calls and apply_calls[-1][0] == "switch.living"
        assert not runtime._zone_manager.manual_active("living")

        runtime.set_scene_brightness_offset(12)
        runtime.set_scene_warmth_offset(-300)
        await asyncio.sleep(0.05)
        assert runtime.scene_brightness_offset() == 12
        assert runtime.scene_warmth_offset() == -300

        backup_result = await runtime.backup_prefs()
        assert backup_result["status"] == "ok"

        runtime.set_scene_brightness_offset(0)
        runtime.set_scene_warmth_offset(0)
        await asyncio.sleep(0.05)
        apply_calls.clear()

        restore_result = await runtime.restore_prefs()
        await asyncio.sleep(0.05)
        assert restore_result["status"] == "ok"
        assert runtime.scene_brightness_offset() == 12
        assert runtime.scene_warmth_offset() == -300
        assert apply_calls and apply_calls[-1][0] == "switch.living"

    hass.loop.run_until_complete(scenario())
