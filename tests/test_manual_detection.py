"""Manual detection tests."""
from __future__ import annotations

import asyncio

from custom_components.adaptive_lighting_pro.const import EVENT_MANUAL_DETECTED
from custom_components.adaptive_lighting_pro.core.event_bus import EventBus
from custom_components.adaptive_lighting_pro.core.timer_manager import TimerManager
from custom_components.adaptive_lighting_pro.core.zone_manager import ZoneManager
from custom_components.adaptive_lighting_pro.features.manual_control import (
    ManualControlConfig,
    ManualControlObserver,
)
from tests.conftest import HomeAssistant, State


def test_manual_detection_duration(hass: HomeAssistant) -> None:
    async def scenario() -> int:
        hass.states["sun.sun"] = State("above", {"elevation": 10})
        event_bus = EventBus(hass, debug=False, trace=False)
        timer_manager = TimerManager(hass, event_bus, debug=False)
        zone_manager = ZoneManager(timer_manager)
        zone_manager.load_zones(
            [
                {
                    "zone_id": "living",
                    "al_switch": "switch.living",
                    "lights": ["light.a"],
                    "enabled": True,
                    "zone_multiplier": 1.5,
                    "sunrise_offset_min": 0,
                }
            ]
        )
        received: list[tuple[str, int]] = []

        async def _record(zone: str, duration_s: int) -> None:
            received.append((zone, duration_s))

        event_bus.subscribe(EVENT_MANUAL_DETECTED, _record)
        observer = ManualControlObserver(
            hass,
            event_bus,
            timer_manager,
            zone_manager,
            ManualControlConfig(debug=False),
        )
        await observer._schedule("living")  # pylint: disable=protected-access
        await asyncio.sleep(0.6)
        await asyncio.sleep(0.1)
        assert received
        return received[0][1]

    duration = hass.loop.run_until_complete(scenario())
    assert duration == 5400
