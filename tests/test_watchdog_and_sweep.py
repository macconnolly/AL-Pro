"""Tests for watchdog and nightly sweep."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from custom_components.adaptive_lighting_pro.const import CONF_ZONES
from custom_components.adaptive_lighting_pro.core.runtime import AdaptiveLightingProRuntime
from custom_components.adaptive_lighting_pro.robustness.watchdog import Watchdog
from tests.conftest import ConfigEntry, HomeAssistant, State


def test_watchdog_triggers_reset(hass: HomeAssistant) -> None:
    async def scenario() -> list[str]:
        triggered: list[str] = []
        watchdog = Watchdog(
            hass,
            interval=timedelta(seconds=0.01),
            on_reset=lambda scope: triggered.append(scope),
            debug=False,
        )
        watchdog.start()
        watchdog.beat("observer")
        await asyncio.sleep(0.05)
        watchdog.stop()
        return triggered

    triggered = hass.loop.run_until_complete(scenario())
    assert "observer" in triggered


def test_nightly_sweep_clears_manual_and_requests_sync(hass: HomeAssistant) -> None:
    async def scenario() -> bool:
        hass.states["switch.zone"] = State("on", {"integration": "adaptive_lighting"})
        entry = ConfigEntry(
            data={
                CONF_ZONES: [
                    {
                        "zone_id": "zone",
                        "al_switch": "switch.zone",
                        "lights": ["light.one"],
                        "enabled": True,
                        "zone_multiplier": 1.0,
                        "sunrise_offset_min": 0,
                    }
                ]
            },
            options={},
        )
        runtime = AdaptiveLightingProRuntime(hass, entry)
        await runtime.async_setup()
        runtime._zone_manager.set_manual("zone", True, 120)  # pylint: disable=protected-access

        async def fake_manual(entity_id: str, manual: bool):
            return {"status": "ok"}

        runtime._executors.set_manual_control = fake_manual  # type: ignore[assignment]
        runtime.force_sync = lambda zone=None: asyncio.sleep(0)  # type: ignore[assignment]
        await runtime._nightly_sweep(datetime.now(UTC))  # pylint: disable=protected-access
        return runtime._zone_manager.manual_active("zone")  # pylint: disable=protected-access

    still_manual = hass.loop.run_until_complete(scenario())
    assert not still_manual
