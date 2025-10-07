import asyncio

from custom_components.adaptive_lighting_pro.const import CONF_ZONES
from custom_components.adaptive_lighting_pro.core.runtime import AdaptiveLightingProRuntime
from custom_components.adaptive_lighting_pro.sensor import (
    AdaptiveLightingProRealtimeSensor,
    AdaptiveLightingProStatusSensor,
)
from tests.conftest import ConfigEntry, HomeAssistant, State


async def _runtime_with_single_zone(hass: HomeAssistant) -> AdaptiveLightingProRuntime:
    hass.states["switch.living"] = State(
        "on",
        {
            "integration": "adaptive_lighting",
            "min_brightness": 40,
            "max_brightness": 90,
            "min_color_temp": 2200,
            "max_color_temp": 4000,
        },
    )
    hass.states["light.lamp"] = State(
        "on",
        {
            "brightness": 128,
            "color_temp_kelvin": 3000,
        },
    )
    entry = ConfigEntry(
        data={
            CONF_ZONES: [
                {
                    "zone_id": "living",
                    "al_switch": "switch.living",
                    "lights": ["light.lamp"],
                    "enabled": True,
                    "zone_multiplier": 1.0,
                    "sunrise_offset_min": 0,
                    "environmental_boost_enabled": True,
                    "sunset_boost_enabled": True,
                }
            ]
        },
        options={},
    )
    runtime = AdaptiveLightingProRuntime(hass, entry)
    await runtime.async_setup()
    return runtime


def test_realtime_and_status_sensors(hass: HomeAssistant) -> None:
    async def scenario() -> None:
        runtime = await _runtime_with_single_zone(hass)
        realtime = AdaptiveLightingProRealtimeSensor(runtime)
        status = AdaptiveLightingProStatusSensor(runtime)
        realtime.hass = hass  # type: ignore[assignment]
        status.hass = hass  # type: ignore[assignment]
        realtime.async_write_ha_state = lambda: None  # type: ignore[assignment]
        status.async_write_ha_state = lambda: None  # type: ignore[assignment]
        await realtime.async_added_to_hass()
        await status.async_added_to_hass()

        await runtime.adjust(step_brightness_pct=10)
        await asyncio.sleep(0)

        assert realtime.native_value == "Brightened +10%"
        realtime_attrs = realtime.extra_state_attributes
        assert realtime_attrs["trigger_source"] == "manual_adjust"
        assert realtime_attrs["final_brightness_adjustment"] == 10
        assert any(
            event[0] == "adaptive_lighting_calculation_complete"
            for event in hass.bus.events
        )

        status_value = status.native_value
        assert "Manual Adjusted" in status_value
        status_attrs = status.extra_state_attributes
        assert status_attrs["active_scene"] == "default"
        assert "manual_brighter" in status_attrs["active_modifiers"]
        adjustments = status_attrs["current_adjustments"]
        assert adjustments["final_brightness"] == 10
        assert status_attrs["environmental_boost_active"] is False

    hass.loop.run_until_complete(scenario())
