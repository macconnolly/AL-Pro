"""Test environmental boost paradigm implementation.

Tests that environmental boost follows implementation_1.yaml patterns:
- Disabled at night (10 PM - 6 AM)
- Reduced during transitions (dawn/dusk)
- Weather and seasonal adjustments
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from custom_components.adaptive_lighting_pro.features.environmental import EnvironmentalAdapter


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    hass.states.get = Mock(return_value=None)
    return hass


async def test_environmental_boost_disabled_at_night(mock_hass):
    """Verify environmental boost returns 0 between 10 PM and 6 AM.

    PARADIGM: Time-of-Day Gating
    From implementation_1.yaml lines 1550-1552 - environmental boost
    must be COMPLETELY DISABLED during night hours.
    """
    adapter = EnvironmentalAdapter(mock_hass)
    adapter.configure(
        lux_sensor="sensor.outdoor_lux",
        weather_entity="weather.home",
        enabled=True
    )

    # Mock sensors with conditions that would normally boost
    mock_lux_state = Mock()
    mock_lux_state.state = "5"  # Very dark - would normally give +15%

    mock_weather_state = Mock()
    mock_weather_state.state = "fog"  # Foggy - would normally give +20%

    def mock_get(entity_id):
        if entity_id == "sensor.outdoor_lux":
            return mock_lux_state
        elif entity_id == "weather.home":
            return mock_weather_state
        return None

    mock_hass.states.get = Mock(side_effect=mock_get)

    # Test at 11 PM (should be disabled)
    with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 15, 23, 0, 0)  # 11 PM in winter

        result = adapter.calculate_boost()

        assert result == 0, "Boost should be 0 at night (11 PM)"
        breakdown = adapter.get_breakdown()
        assert breakdown["time_multiplier"] == 0.0
        assert breakdown["limiting_factor"] == "time_suppression"

    # Test at 3 AM (should be disabled)
    with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 15, 3, 0, 0)  # 3 AM

        result = adapter.calculate_boost()

        assert result == 0, "Boost should be 0 at night (3 AM)"
        breakdown = adapter.get_breakdown()
        assert breakdown["time_multiplier"] == 0.0

    # Test at 6 AM exactly (should still be disabled - inclusive)
    with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 15, 6, 0, 0)  # 6 AM

        result = adapter.calculate_boost()

        assert result == 0, "Boost should be 0 at 6 AM (inclusive)"


async def test_environmental_boost_reduced_at_dawn_dusk(mock_hass):
    """Verify environmental boost is reduced to 70% during transition periods.

    Dawn: 6-8 AM
    Dusk: 6-10 PM
    """
    adapter = EnvironmentalAdapter(mock_hass)
    adapter.configure(
        lux_sensor="sensor.outdoor_lux",
        weather_entity="weather.home",
        enabled=True
    )

    # Mock sensors
    mock_lux_state = Mock()
    mock_lux_state.state = "20"  # Dark - +10% base

    mock_weather_state = Mock()
    mock_weather_state.state = "cloudy"  # +10% base

    def mock_get(entity_id):
        if entity_id == "sensor.outdoor_lux":
            return mock_lux_state
        elif entity_id == "weather.home":
            return mock_weather_state
        return None

    mock_hass.states.get = Mock(side_effect=mock_get)

    # Test at 7 AM (dawn - should be reduced)
    with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 15, 7, 0, 0)  # 7 AM in winter

        result = adapter.calculate_boost()

        # Base would be 10 (lux) + 10 (weather) + 8 (winter) = 28
        # With 0.7x multiplier = 19.6 → 19
        assert result == 19, f"Dawn boost should be reduced to 70% (got {result})"
        breakdown = adapter.get_breakdown()
        assert breakdown["time_multiplier"] == 0.7

    # Test at 7 PM (dusk - should be reduced)
    with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 15, 19, 0, 0)  # 7 PM

        result = adapter.calculate_boost()

        assert result == 19, f"Dusk boost should be reduced to 70% (got {result})"
        breakdown = adapter.get_breakdown()
        assert breakdown["time_multiplier"] == 0.7


async def test_environmental_boost_full_during_day(mock_hass):
    """Verify environmental boost applies fully during day hours (8 AM - 6 PM)."""
    adapter = EnvironmentalAdapter(mock_hass)
    adapter.configure(
        lux_sensor="sensor.outdoor_lux",
        weather_entity="weather.home",
        enabled=True
    )

    # Mock sensors
    mock_lux_state = Mock()
    mock_lux_state.state = "30"  # +7% from lux

    mock_weather_state = Mock()
    mock_weather_state.state = "rainy"  # +12% from weather

    def mock_get(entity_id):
        if entity_id == "sensor.outdoor_lux":
            return mock_lux_state
        elif entity_id == "weather.home":
            return mock_weather_state
        return None

    mock_hass.states.get = Mock(side_effect=mock_get)

    # Test at 2 PM (full day)
    with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 7, 15, 14, 0, 0)  # 2 PM in summer

        result = adapter.calculate_boost()

        # Base: 7 (lux) + 12 (weather) - 3 (summer) = 16
        # With 1.0x multiplier = 16
        assert result == 16, f"Day boost should apply fully (got {result})"
        breakdown = adapter.get_breakdown()
        assert breakdown["time_multiplier"] == 1.0
        assert breakdown["lux_boost_pct"] == 7
        assert breakdown["weather_boost_pct"] == 12
        assert breakdown["seasonal_adjustment_pct"] == -3


async def test_environmental_boost_capped_at_25_percent(mock_hass):
    """Verify environmental boost is capped at 25% maximum."""
    adapter = EnvironmentalAdapter(mock_hass)
    adapter.configure(
        lux_sensor="sensor.outdoor_lux",
        weather_entity="weather.home",
        enabled=True
    )

    # Mock extreme conditions
    mock_lux_state = Mock()
    mock_lux_state.state = "5"  # Very dark +15%

    mock_weather_state = Mock()
    mock_weather_state.state = "fog"  # Very foggy +20%

    def mock_get(entity_id):
        if entity_id == "sensor.outdoor_lux":
            return mock_lux_state
        elif entity_id == "weather.home":
            return mock_weather_state
        return None

    mock_hass.states.get = Mock(side_effect=mock_get)

    # Test at noon in winter (maximum conditions)
    with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 15, 12, 0, 0)  # Noon in winter

        result = adapter.calculate_boost()

        # Base: 15 (lux) + 20 (fog) + 8 (winter) = 43%
        # Should be capped at 25%
        assert result == 25, f"Boost should be capped at 25% (got {result})"
        breakdown = adapter.get_breakdown()
        assert breakdown["limiting_factor"] == "max_boost_cap"
        assert breakdown["raw_boost_before_time"] == 43