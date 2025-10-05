"""Tests for sunset boost calculation.

Tests the CORRECTED logic (was backwards in YAML - dimmed instead of boosted).
These tests verify the system BOOSTS on dark days during sunset, not dims.
"""
from unittest.mock import MagicMock, patch

import pytest

from custom_components.adaptive_lighting_pro.features.sunset_boost import (
    SunsetBoostCalculator,
)


@pytest.mark.unit
@pytest.mark.sunset
class TestSunsetBoostRealWorld:
    """Test sunset boost with scenarios that expose bugs in the corrected logic."""

    @pytest.fixture
    def clean_mock_hass(self):
        """Create a clean mock hass without pre-configured side_effects."""
        from unittest.mock import MagicMock
        hass = MagicMock()
        hass.states = MagicMock()
        return hass

    @pytest.fixture
    def sunset_calc(self, clean_mock_hass):
        """Create sunset boost calculator."""
        calc = SunsetBoostCalculator(clean_mock_hass)
        calc.configure(enabled=True)
        return calc

    def test_dark_cloudy_day_at_sunset_should_boost(
        self, sunset_calc, clean_mock_hass
    ):
        """Dark cloudy day at sunset should apply POSITIVE boost.

        REAL SCENARIO: 5:30 PM, overcast all day, lux 800, sun at horizon (0°)
        EXPECTED: 12.5% boost (halfway through sunset window)
        WHY CRITICAL: This is THE use case we fixed - YAML dimmed, we boost
        BUG WOULD CAUSE: Lights dimming when they should brighten
        """
        sun_state = MagicMock()
        sun_state.state = "above_horizon"  # Required for is_available() check
        sun_state.attributes = {"elevation": 0.0}  # At horizon
        clean_mock_hass.states.get.return_value = sun_state
        
        lux = 800  # Dark day (< 3000 threshold)
        boost = sunset_calc.calculate_boost(lux)
        
        # Expected: (4 - 0) / 8 * 25 = 12.5 → 12 (int)
        assert boost == 12, (
            f"Expected 12% boost for dark day at sunset (elevation 0°), got {boost}%. "
            f"This is the CORRECTED logic - YAML was backwards and dimmed instead."
        )

    def test_clear_bright_day_at_sunset_should_skip_boost(
        self, sunset_calc, clean_mock_hass
    ):
        """Bright clear day at sunset should NOT boost (lux gating).

        REAL SCENARIO: Beautiful clear evening, lux 8000, sun at horizon
        EXPECTED: 0% boost (lux > 3000 prevents boost)
        WHY CRITICAL: System should only compensate when NEEDED
        BUG WOULD CAUSE: Unnecessary boost on already-bright evenings
        """
        sun_state = MagicMock()
        sun_state.state = "above_horizon"
        sun_state.attributes = {"elevation": 0.0}
        clean_mock_hass.states.get.return_value = sun_state
        
        lux = 8000  # Bright day (> 3000 threshold)
        boost = sunset_calc.calculate_boost(lux)
        
        assert boost == 0, (
            f"Expected 0% boost for bright day at sunset, got {boost}%. "
            f"Lux gating (>3000) should prevent boost when not needed."
        )

    def test_dark_day_outside_sunset_window_should_skip(
        self, sunset_calc, clean_mock_hass
    ):
        """Dark day but sun too high should NOT boost.

        REAL SCENARIO: 3:00 PM, overcast, lux 600, sun at 10° elevation
        EXPECTED: 0% boost (outside -4° to 4° window)
        WHY CRITICAL: Sunset boost is for sunset period only, not all day
        BUG WOULD CAUSE: Boost active during afternoon when not appropriate
        """
        sun_state = MagicMock()
        sun_state.state = "above_horizon"
        sun_state.attributes = {"elevation": 10.0}  # Too high
        clean_mock_hass.states.get.return_value = sun_state
        
        lux = 600  # Dark (< 3000)
        boost = sunset_calc.calculate_boost(lux)
        
        assert boost == 0, (
            f"Expected 0% boost outside sunset window (10° elevation), got {boost}%. "
            f"Sunset boost should only activate between -4° and 4° elevation."
        )

    def test_sunset_window_linear_interpolation(
        self, sunset_calc, clean_mock_hass
    ):
        """Verify linear scaling across sunset window.

        REAL SCENARIO: Track boost as sun descends through sunset
        EXPECTED: Linear increase from 0% at 4° to 25% at -4°
        WHY CRITICAL: Smooth transition, not sudden jump
        BUG WOULD CAUSE: Abrupt lighting changes during sunset
        """
        lux = 500  # Dark day
        
        test_cases = [
            (4.0, 0),     # Top of window: 0%
            (2.0, 6),     # (4-2)/8 * 25 = 6.25 → 6%
            (0.0, 12),    # Horizon: (4-0)/8 * 25 = 12.5 → 12%
            (-2.0, 18),   # Below: (4-(-2))/8 * 25 = 18.75 → 18%
            (-4.0, 25),   # Bottom: full 25%
        ]
        
        lux = 500  # Dark day (< 3000)

        for elevation, expected_boost in test_cases:
            sun_state = MagicMock()
            sun_state.state = "above_horizon" if elevation >= 0 else "below_horizon"
            sun_state.attributes = {"elevation": elevation}
            clean_mock_hass.states.get.return_value = sun_state
            
            boost = sunset_calc.calculate_boost(lux)
            
            assert boost == expected_boost, (
                f"At {elevation}° elevation, expected {expected_boost}% boost, got {boost}%. "
                f"Linear interpolation across sunset window is broken."
            )

    def test_lux_threshold_exactly_3000_should_not_boost(
        self, sunset_calc, mock_hass
    ):
        """Edge case: lux exactly at 3000 threshold.
        
        REAL SCENARIO: Lux right at threshold value
        EXPECTED: 0% (threshold is exclusive: < 3000)
        WHY CRITICAL: Off-by-one errors cause inconsistent behavior
        BUG WOULD CAUSE: Boost flickering on/off at threshold
        """
        sun_state = MagicMock()
        sun_state.attributes = {"elevation": 0.0}
        mock_hass.states.get.return_value = sun_state
        
        lux = 3000  # Exactly at threshold
        boost = sunset_calc.calculate_boost(lux)
        
        assert boost == 0, (
            f"Expected 0% boost at exactly 3000 lux, got {boost}%. "
            f"Threshold check (< 3000) should exclude boundary value."
        )

    def test_sun_entity_unavailable_should_safely_degrade(
        self, sunset_calc, clean_mock_hass
    ):
        """Sun entity unavailable should return 0 boost.

        REAL SCENARIO: HA restart, sun integration temporarily unavailable
        EXPECTED: 0% boost (safe degradation)
        WHY CRITICAL: System must not crash on missing data
        BUG WOULD CAUSE: Exception crash, integration fails to load
        """
        clean_mock_hass.states.get.return_value = None  # Entity not found
        
        lux = 500  # Would normally trigger boost
        boost = sunset_calc.calculate_boost(lux)
        
        assert boost == 0, (
            f"Expected 0% boost when sun.sun unavailable, got {boost}%. "
            f"Must gracefully degrade when sun entity missing."
        )

    def test_negative_lux_should_be_treated_as_zero(
        self, sunset_calc, clean_mock_hass
    ):
        """Negative lux (sensor error) should not cause issues.

        REAL SCENARIO: Buggy lux sensor reports -10
        EXPECTED: Treated as very dark, boost if in sunset window
        WHY CRITICAL: Sensor errors happen in real deployments
        BUG WOULD CAUSE: Crash or incorrect calculation
        """
        sun_state = MagicMock()
        sun_state.state = "above_horizon"
        sun_state.attributes = {"elevation": 0.0}
        clean_mock_hass.states.get.return_value = sun_state
        
        lux = -10  # Invalid but possible sensor value
        boost = sunset_calc.calculate_boost(lux)
        
        # Should treat as dark (< 3000) and apply boost
        assert boost == 12, (
            f"Expected 12% boost for negative lux (sensor error), got {boost}%. "
            f"Negative lux should be treated as very dark condition."
        )
