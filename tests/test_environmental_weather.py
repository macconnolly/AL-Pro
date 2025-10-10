"""Environmental observer weather mapping tests."""
from __future__ import annotations

import pytest

from custom_components.adaptive_lighting_pro.core.event_bus import EventBus
from custom_components.adaptive_lighting_pro.core.timer_manager import TimerManager
from custom_components.adaptive_lighting_pro.features.environmental import (
    EnvironmentalConfig,
    EnvironmentalObserver,
)
from tests.conftest import HomeAssistant


@pytest.fixture
def observer(hass: HomeAssistant) -> EnvironmentalObserver:
    event_bus = EventBus(hass, debug=False, trace=False)
    timer_manager = TimerManager(hass, event_bus, debug=False)
    return EnvironmentalObserver(
        hass,
        event_bus,
        timer_manager,
        EnvironmentalConfig(lux_entity=None, weather_entity=None, debug=False),
    )


@pytest.mark.parametrize(
    ("raw_state", "expected"),
    [
        ("rain", 12),
        ("Rain Showers", 12),
        ("thunder-storm", 12),
        ("Blizzard", 15),
        ("drizzle", 12),
        ("scattered clouds", 10),
        ("partly sunny", 5),
        ("mostly clear", 5),
        ("clear-night", 0),
        ("exceptional", 15),
    ],
)
def test_weather_alias_mapping(
    observer: EnvironmentalObserver, raw_state: str, expected: int
) -> None:
    normalized = observer._normalize_weather_state(raw_state)  # pylint: disable=protected-access
    boost = observer._calculate_weather_boost(normalized)
    assert boost == expected


def test_unknown_weather_defaults_to_zero(observer: EnvironmentalObserver) -> None:
    boost = observer._calculate_weather_boost("unknownstate")
    assert boost == 0
