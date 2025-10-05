"""Tests for environmental boost calculation.

These tests verify REAL functionality with challenging scenarios that expose bugs.
Each test represents actual conditions the system will encounter in production.
"""
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.adaptive_lighting_pro.features.environmental import (
    EnvironmentalAdapter,
)


@pytest.mark.unit
@pytest.mark.environmental
class TestEnvironmentalBoostRealWorld:
    """Test environmental boost with realistic scenarios that should fail if logic is wrong."""

    @pytest.fixture
    def env_adapter(self, mock_hass):
        """Create environmental adapter."""
        adapter = EnvironmentalAdapter(mock_hass)
        adapter.configure(
            lux_sensor="sensor.outdoor_illuminance",
            weather_entity="weather.home",
            enabled=True,
        )
        return adapter

    def test_foggy_winter_morning_should_max_out_boost(
        self, env_adapter, mock_hass, mock_datetime_winter_morning
    ):
        """Foggy winter morning should hit maximum boost.
        
        REAL SCENARIO: January morning, fog, 15 lux
        EXPECTED: System maxes out at 25% boost (clamped)
        WHY THIS MATTERS: Tests if clamping works - without it boost would be 30.1%
        BUG WOULD CAUSE: Brightness exceeding configured max, collapsed ranges
        """
        # Setup: Very dark (15 lux), fog weather, January, dawn
        lux_state = MagicMock()
        lux_state.state = "15"  # Very dark
        
        weather_state = MagicMock()
        weather_state.state = "fog"  # +20% weather boost
        
        mock_hass.states.get.side_effect = lambda e: {
            "sensor.outdoor_illuminance": lux_state,
            "weather.home": weather_state,
        }.get(e)
        
        with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
            mock_dt.now.return_value = mock_datetime_winter_morning
            
            boost, breakdown = env_adapter.calculate_boost()

            # Calculate expected: (15 lux component + 20 fog + 8 winter) * 0.7 dawn = 30.1
            # Should clamp to 25
            assert boost == 25, (
                f"Expected maximum boost of 25% for foggy winter dawn, got {boost}%. "
                f"Without proper clamping, this scenario creates illegal brightness values."
            )

            # Phase 2.5: Verify breakdown structure
            assert breakdown["boost_pct"] == 25
            assert breakdown["lux_value"] == 15
            assert breakdown["limiting_factor"] == "max_boost_cap"

    def test_clear_summer_day_should_give_zero_boost(
        self, env_adapter, mock_hass, mock_datetime_summer_afternoon
    ):
        """Bright summer day should provide zero boost.
        
        REAL SCENARIO: July afternoon, sunny, 15000 lux
        EXPECTED: 0% boost (no compensation needed)
        WHY THIS MATTERS: Tests if system stays off when not needed
        BUG WOULD CAUSE: Unnecessary brightness increase on already-bright days
        """
        lux_state = MagicMock()
        lux_state.state = "15000"  # Very bright
        
        weather_state = MagicMock()
        weather_state.state = "sunny"
        
        mock_hass.states.get.side_effect = lambda e: {
            "sensor.outdoor_illuminance": lux_state,
            "weather.home": weather_state,
        }.get(e)
        
        with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
            mock_dt.now.return_value = mock_datetime_summer_afternoon
            
            boost, breakdown = env_adapter.calculate_boost()

            assert boost == 0, (
                f"Expected 0% boost for bright summer day, got {boost}%. "
                f"System should not compensate when conditions are already bright."
            )
            assert breakdown["boost_pct"] == 0

    def test_night_should_completely_suppress_boost(
        self, env_adapter, mock_hass, mock_datetime_night
    ):
        """Night should completely suppress environmental boost.
        
        REAL SCENARIO: 11 PM, dark and rainy (would normally trigger high boost)
        EXPECTED: 0% boost (time multiplier = 0.0)
        WHY THIS MATTERS: Environmental boost compensates for unexpected darkness.
        At night, darkness is EXPECTED, so boost should not activate.
        BUG WOULD CAUSE: Lights getting brighter at night when they should be dimming
        """
        lux_state = MagicMock()
        lux_state.state = "0"  # Completely dark
        
        weather_state = MagicMock()
        weather_state.state = "rainy"  # Would normally add +15%
        
        mock_hass.states.get.side_effect = lambda e: {
            "sensor.outdoor_illuminance": lux_state,
            "weather.home": weather_state,
        }.get(e)
        
        with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
            # December 1st, 11 PM
            mock_dt.now.return_value = datetime(2025, 12, 1, 23, 0, 0, tzinfo=UTC)
            
            boost, breakdown = env_adapter.calculate_boost()

            assert boost == 0, (
                f"Expected 0% boost at night (time multiplier 0.0), got {boost}%. "
                f"Environmental boost should never activate at night regardless of conditions. "
                f"This is a CRITICAL bug - night darkness is expected, not a failure to compensate."
            )
            assert breakdown["limiting_factor"] == "time_suppression"

    def test_dawn_should_reduce_but_not_eliminate_boost(
        self, env_adapter, mock_hass, mock_datetime_dawn
    ):
        """Dawn should apply 0.7x multiplier to environmental boost.
        
        REAL SCENARIO: 7 AM, cloudy, 100 lux
        EXPECTED: Reduced boost (0.7x multiplier)
        WHY THIS MATTERS: Dawn is darker than day but lighter than night
        BUG WOULD CAUSE: Either too much boost (treats dawn as day) or too little (treats as night)
        """
        lux_state = MagicMock()
        lux_state.state = "100"  # Moderately dark
        
        weather_state = MagicMock()
        weather_state.state = "cloudy"  # +10%
        
        mock_hass.states.get.side_effect = lambda e: {
            "sensor.outdoor_illuminance": lux_state,
            "weather.home": weather_state,
        }.get(e)
        
        with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
            mock_dt.now.return_value = mock_datetime_dawn
            
            boost, breakdown = env_adapter.calculate_boost()

            # Expected: Some boost but reduced by 0.7x
            # Lux 100 = ~7%, cloudy = +10%, seasonal = ~0%, total ~17% * 0.7 = ~11.9%
            assert 9 <= boost <= 13, (
                f"Expected reduced boost (10-13%) for dawn conditions, got {boost}%. "
                f"Dawn multiplier (0.7x) should reduce but not eliminate boost."
            )
            assert breakdown["time_multiplier"] == 0.7

    def test_sensor_unavailable_should_safely_degrade(
        self, env_adapter, mock_hass
    ):
        """Unavailable sensors should gracefully return 0 boost.
        
        REAL SCENARIO: Lux sensor offline/unavailable
        EXPECTED: 0% boost (safe degradation)
        WHY THIS MATTERS: Sensor failures happen in real deployments
        BUG WOULD CAUSE: Exception crash or invalid boost calculation
        """
        lux_state = MagicMock()
        lux_state.state = "unavailable"
        
        weather_state = MagicMock()
        weather_state.state = "sunny"
        
        mock_hass.states.get.side_effect = lambda e: {
            "sensor.outdoor_illuminance": lux_state,
            "weather.home": weather_state,
        }.get(e)
        
        with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
            mock_dt.now.return_value = datetime.now(UTC)
            
            # Should not crash
            boost, breakdown = env_adapter.calculate_boost()

            assert boost == 0, (
                f"Expected 0% boost when lux sensor unavailable, got {boost}%. "
                f"System must gracefully degrade when sensors fail."
            )
            assert breakdown["lux_value"] == 0

    def test_all_weather_states_should_produce_valid_boost(
        self, env_adapter, mock_hass
    ):
        """Every weather state should produce a valid boost value.
        
        REAL SCENARIO: Test all 15 weather conditions
        EXPECTED: All produce valid boost (0-25%)
        WHY THIS MATTERS: Ensures no weather state crashes or produces invalid values
        BUG WOULD CAUSE: Crashes on uncommon weather states, invalid boost values
        """
        weather_states = [
            "clear-night", "cloudy", "fog", "hail", "lightning",
            "lightning-rainy", "partlycloudy", "pouring", "rainy",
            "snowy", "snowy-rainy", "sunny", "windy", "windy-variant",
            "exceptional"
        ]
        
        lux_state = MagicMock()
        lux_state.state = "200"  # Moderate darkness
        
        for weather_condition in weather_states:
            weather_state = MagicMock()
            weather_state.state = weather_condition
            
            mock_hass.states.get.side_effect = lambda e: {
                "sensor.outdoor_illuminance": lux_state,
                "weather.home": weather_state,
            }.get(e)
            
            with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
                mock_dt.now.return_value = datetime(2025, 10, 1, 14, 0, 0, tzinfo=UTC)
                
                boost, breakdown = env_adapter.calculate_boost()

                assert 0 <= boost <= 25, (
                    f"Weather state '{weather_condition}' produced invalid boost {boost}%. "
                    f"All weather states must produce boost in range 0-25%."
                )
                assert breakdown["weather_boost_pct"] >= 0

    def test_seasonal_adjustment_winter_vs_summer(
        self, env_adapter, mock_hass
    ):
        """Winter should add boost, summer should reduce boost.
        
        REAL SCENARIO: Same conditions in January vs July
        EXPECTED: January boost > July boost
        WHY THIS MATTERS: Winter days are darker and need more compensation
        BUG WOULD CAUSE: Lights too dim in winter, too bright in summer
        """
        lux_state = MagicMock()
        lux_state.state = "500"  # Same lux both times
        
        weather_state = MagicMock()
        weather_state.state = "cloudy"
        
        mock_hass.states.get.side_effect = lambda e: {
            "sensor.outdoor_illuminance": lux_state,
            "weather.home": weather_state,
        }.get(e)
        
        # Calculate winter boost (January, 2 PM)
        with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 15, 14, 0, 0, tzinfo=UTC)
            winter_boost, winter_breakdown = env_adapter.calculate_boost()

        # Calculate summer boost (July, 2 PM)
        with patch("custom_components.adaptive_lighting_pro.features.environmental.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 7, 15, 14, 0, 0, tzinfo=UTC)
            summer_boost, summer_breakdown = env_adapter.calculate_boost()
        
        assert winter_boost > summer_boost, (
            f"Winter boost ({winter_boost}%) should exceed summer boost ({summer_boost}%). "
            f"Seasonal adjustment not working - winter days are darker and need more compensation."
        )
        
        # Verify expected difference (winter +8%, summer -3% = 11% difference)
        difference = winter_boost - summer_boost
        assert 8 <= difference <= 14, (
            f"Seasonal difference ({difference}%) outside expected range (8-14%). "
            f"Seasonal adjustment calculation may be incorrect."
        )
