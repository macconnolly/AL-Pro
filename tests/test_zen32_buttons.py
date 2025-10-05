import asyncio

from custom_components.adaptive_lighting_pro.const import (
    CONF_SENSORS,
    CONF_ZONES,
    EVENT_BUTTON_PRESSED,
)
from custom_components.adaptive_lighting_pro.core.runtime import AdaptiveLightingProRuntime
from tests.conftest import ConfigEntry, HomeAssistant, State


async def _setup_runtime(
    hass: HomeAssistant,
    zones: list[dict],
    sensors: dict | None = None,
) -> AdaptiveLightingProRuntime:
    for zone in zones:
        hass.states[zone["al_switch"]] = State("on", {"integration": "adaptive_lighting"})
    entry = ConfigEntry(
        data={CONF_ZONES: zones, CONF_SENSORS: sensors or {}},
        options={},
    )
    runtime = AdaptiveLightingProRuntime(hass, entry)
    await runtime.async_setup()
    return runtime


def test_zen32_scene_cycle_respects_mode(hass: HomeAssistant) -> None:
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

        async def fake_force_sync(zone: str | None = None) -> dict:
            return {"status": "ok", "results": []}

        runtime.force_sync = fake_force_sync  # type: ignore[assignment]

        cycle_calls: list[str] = []

        async def fake_cycle() -> None:
            cycle_calls.append("cycle")

        runtime._scene_manager.cycle = fake_cycle  # type: ignore[assignment]

        await runtime.select_mode("movie")
        runtime._event_bus.post(
            EVENT_BUTTON_PRESSED,
            device="zen32",
            button="001",
            action="KeyPressed",
        )
        await asyncio.sleep(0.1)
        assert not cycle_calls

        await runtime.select_mode("adaptive")
        runtime._event_bus.post(
            EVENT_BUTTON_PRESSED,
            device="zen32",
            button="001",
            action="KeyPressed",
        )
        await asyncio.sleep(0.1)
        assert cycle_calls == ["cycle"]

    hass.loop.run_until_complete(scenario())


def test_zen32_adjust_buttons_use_configured_steps(hass: HomeAssistant) -> None:
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
        runtime.set_adjust_brightness_step(15)
        runtime.set_adjust_color_temp_step(250)

        adjust_calls: list[dict] = []

        async def fake_adjust(**kwargs) -> dict:
            adjust_calls.append(kwargs)
            return {"status": "ok", "results": []}

        runtime.adjust = fake_adjust  # type: ignore[assignment]

        runtime._event_bus.post(
            EVENT_BUTTON_PRESSED,
            device="zen32",
            button="002",
            action="KeyPressed",
        )
        runtime._event_bus.post(
            EVENT_BUTTON_PRESSED,
            device="zen32",
            button="002",
            action="KeyHeldDown",
        )
        runtime._event_bus.post(
            EVENT_BUTTON_PRESSED,
            device="zen32",
            button="004",
            action="KeyPressed",
        )
        runtime._event_bus.post(
            EVENT_BUTTON_PRESSED,
            device="zen32",
            button="004",
            action="KeyHeldDown",
        )
        await asyncio.sleep(0.1)

        assert len(adjust_calls) == 4
        assert adjust_calls[0]["step_brightness_pct"] == 15
        assert adjust_calls[0].get("step_color_temp") is None
        assert adjust_calls[1]["step_color_temp"] == -250
        assert adjust_calls[2]["step_brightness_pct"] == -15
        assert adjust_calls[3]["step_color_temp"] == 250

    hass.loop.run_until_complete(scenario())


def test_zen32_reset_clears_manual_and_restores_adaptive(hass: HomeAssistant) -> None:
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
        runtime = await _setup_runtime(hass, zones)

        async def fake_force_sync(zone: str | None = None) -> dict:
            return {"status": "ok", "results": []}

        runtime.force_sync = fake_force_sync  # type: ignore[assignment]

        async def fake_manual(entity_id: str, manual: bool) -> dict:
            return {"status": "ok"}

        runtime._executors.set_manual_control = fake_manual  # type: ignore[assignment]

        await runtime.select_mode("movie")
        runtime._zone_manager.set_manual("living", True, 30)
        runtime._zone_manager.set_manual("kitchen", True, 30)

        runtime._event_bus.post(
            EVENT_BUTTON_PRESSED,
            device="zen32",
            button="003",
            action="KeyPressed",
        )
        await asyncio.sleep(0.1)

        assert runtime._mode_manager.mode == "adaptive"
        assert not runtime._zone_manager.manual_active("living")
        assert not runtime._zone_manager.manual_active("kitchen")

    hass.loop.run_until_complete(scenario())


def test_zen32_toggle_all_lights_calls_service(hass: HomeAssistant) -> None:
    async def scenario() -> None:
        zones = [
            {
                "zone_id": "living",
                "al_switch": "switch.living",
                "lights": ["light.one", "light.two"],
                "enabled": True,
                "zone_multiplier": 1.0,
                "sunrise_offset_min": 0,
                "environmental_boost_enabled": True,
                "sunset_boost_enabled": True,
            },
            {
                "zone_id": "kitchen",
                "al_switch": "switch.kitchen",
                "lights": ["light.two", "light.three"],
                "enabled": True,
                "zone_multiplier": 1.0,
                "sunrise_offset_min": 0,
                "environmental_boost_enabled": True,
                "sunset_boost_enabled": True,
            },
        ]
        runtime = await _setup_runtime(hass, zones)

        toggle_calls: list[tuple[str, dict]] = []

        async def fake_light(service: str, data: dict) -> dict:
            toggle_calls.append((service, data))
            return {"status": "ok"}

        runtime._executors.call_light_service = fake_light  # type: ignore[assignment]

        runtime._event_bus.post(
            EVENT_BUTTON_PRESSED,
            device="zen32",
            button="005",
            action="KeyPressed",
        )
        await asyncio.sleep(0.1)

        assert toggle_calls
        service, data = toggle_calls[0]
        assert service == "toggle"
        assert sorted(data["entity_id"]) == ["light.one", "light.three", "light.two"]

    hass.loop.run_until_complete(scenario())
