"""Tests for adjustment engine boundary calculations.

THE CRITICAL COMPONENT: Does asymmetric boundary logic work correctly?
This tests the CORE INNOVATION of the system - allowing manual control while preserving AL.

WHAT WE'RE TESTING:
1. Positive offset raises min only (preserves natural dimming at night)
2. Negative offset lowers max only (preserves natural brightening in morning)
3. Combined environmental boost overflow scenarios
4. Boundary collapse detection when min >= max
5. Zone with insufficient range handling

WHY THIS MATTERS:
- Adjustment engine is 24% tested (CRITICAL GAP)
- Combined boost overflow discovered: env(25%) + sunset(12%) = 37%
- If zone has min=45, max=80 (35% range), offset=37% → min=82 > max=80 → COLLAPSE
- System MUST handle this gracefully or lights break
"""
import pytest

from custom_components.adaptive_lighting_pro.adjustment_engine import (
    Boundaries,
    calculate_boundaries,
    calculate_brightness_bounds,
    calculate_color_temp_bounds,
    validate_brightness_range,
    validate_color_temp_range,
)


@pytest.mark.unit
@pytest.mark.adjustment_engine
class TestBrightnessAsymmetricAdjustment:
    """Test asymmetric brightness boundary calculations."""

    def test_positive_adjustment_raises_min_only(self):
        """Positive adjustment should raise minimum only, keep maximum unchanged.

        REAL SCENARIO: User presses "brighter" button (+5%)
        EXPECTED: min=45 → min=50, max=100 stays 100
        WHY: Preserves natural dimming at night (AL can still reach max)
        """
        new_min, new_max = calculate_brightness_bounds(
            current_min=45,
            current_max=100,
            adjustment=5,
        )

        assert new_min == 50, f"Expected min=50, got {new_min}"
        assert new_max == 100, f"Expected max unchanged at 100, got {new_max}"

    def test_negative_adjustment_lowers_max_only(self):
        """Negative adjustment should lower maximum only, keep minimum unchanged.

        REAL SCENARIO: User presses "dimmer" button (-5%)
        EXPECTED: min=45 stays 45, max=100 → max=95
        WHY: Preserves natural brightening in morning (AL can still reach min)
        """
        new_min, new_max = calculate_brightness_bounds(
            current_min=45,
            current_max=100,
            adjustment=-5,
        )

        assert new_min == 45, f"Expected min unchanged at 45, got {new_min}"
        assert new_max == 95, f"Expected max=95, got {new_max}"

    def test_zero_adjustment_no_change(self):
        """Zero adjustment should leave boundaries unchanged."""
        new_min, new_max = calculate_brightness_bounds(
            current_min=45,
            current_max=100,
            adjustment=0,
        )

        assert new_min == 45 and new_max == 100

    def test_extreme_positive_clamps_at_100(self):
        """Extreme positive adjustment should clamp at 100%.

        REAL SCENARIO: Zone min=90, user presses brighter (+20%)
        EXPECTED: min=100 (clamped), not 110
        """
        new_min, new_max = calculate_brightness_bounds(
            current_min=90,
            current_max=100,
            adjustment=20,
        )

        assert new_min == 100, f"Expected min clamped at 100, got {new_min}"
        assert new_max == 100

    def test_extreme_negative_clamps_at_0(self):
        """Extreme negative adjustment should clamp at 0%.

        REAL SCENARIO: Zone max=10, user presses dimmer (-20%)
        EXPECTED: max=0 (clamped), not -10
        """
        new_min, new_max = calculate_brightness_bounds(
            current_min=0,
            current_max=10,
            adjustment=-20,
        )

        assert new_min == 0
        assert new_max == 0, f"Expected max clamped at 0, got {new_max}"


@pytest.mark.unit
@pytest.mark.adjustment_engine
class TestColorTempAsymmetricAdjustment:
    """Test asymmetric color temperature boundary calculations."""

    def test_positive_adjustment_raises_min_cooler(self):
        """Positive adjustment (cooler) should raise minimum only.

        REAL SCENARIO: User presses "cooler" button (+500K)
        EXPECTED: min=2250K → min=2750K, max=2950K stays 2950K
        WHY: Prevents AL from going too warm (below new preference)
        """
        new_min, new_max = calculate_color_temp_bounds(
            current_min=2250,
            current_max=2950,
            adjustment=500,
        )

        assert new_min == 2750, f"Expected min=2750K, got {new_min}K"
        assert new_max == 2950, f"Expected max unchanged at 2950K, got {new_max}K"

    def test_negative_adjustment_lowers_max_warmer(self):
        """Negative adjustment (warmer) should lower maximum only.

        REAL SCENARIO: User presses "warmer" button (-500K)
        EXPECTED: min=2250K stays 2250K, max=2950K → max=2450K
        WHY: Prevents AL from going too cool (above new preference)
        """
        new_min, new_max = calculate_color_temp_bounds(
            current_min=2250,
            current_max=2950,
            adjustment=-500,
        )

        assert new_min == 2250, f"Expected min unchanged at 2250K, got {new_min}K"
        assert new_max == 2450, f"Expected max=2450K, got {new_max}K"

    def test_extreme_positive_clamps_at_6500(self):
        """Extreme positive adjustment should clamp at 6500K.

        REAL SCENARIO: Zone min=6000K, user presses cooler (+1000K)
        EXPECTED: min=6500K (clamped), not 7000K
        """
        new_min, new_max = calculate_color_temp_bounds(
            current_min=6000,
            current_max=6500,
            adjustment=1000,
        )

        assert new_min == 6500, f"Expected min clamped at 6500K, got {new_min}K"
        assert new_max == 6500

    def test_extreme_negative_clamps_at_1500(self):
        """Extreme negative adjustment should clamp at 1500K.

        REAL SCENARIO: Zone max=2000K, user presses warmer (-1000K)
        EXPECTED: max=1500K (clamped), not 1000K
        """
        new_min, new_max = calculate_color_temp_bounds(
            current_min=1500,
            current_max=2000,
            adjustment=-1000,
        )

        assert new_min == 1500
        assert new_max == 1500, f"Expected max clamped at 1500K, got {new_max}K"


@pytest.mark.unit
@pytest.mark.adjustment_engine
class TestBoundaryCollapse:
    """Test boundary collapse scenarios - THE CRITICAL OVERFLOW TESTS."""

    def test_normal_zone_with_moderate_boost(self):
        """Normal zone (55% range) handles moderate boost (20%) safely.

        REAL SCENARIO: Zone min=45, max=100 (55% range), env boost=20%
        EXPECTED: min=65, max=100, range=35% (AL still has room to vary)
        WHY: This is typical foggy day, should work perfectly
        """
        zone_config = {
            "brightness_min": 45,
            "brightness_max": 100,
            "color_temp_min": 2250,
            "color_temp_max": 2950,
        }

        boundaries = calculate_boundaries(zone_config, brightness_offset=20, warmth_offset=0)

        assert boundaries.min_brightness == 65, f"Expected min=65, got {boundaries.min_brightness}"
        assert boundaries.max_brightness == 100, f"Expected max=100, got {boundaries.max_brightness}"

        # Verify AL has usable range
        range_remaining = boundaries.max_brightness - boundaries.min_brightness
        assert range_remaining == 35, f"Expected 35% range remaining, got {range_remaining}%"

    def test_narrow_zone_with_extreme_boost_should_collapse_to_min_equals_max(self):
        """Narrow zone (35% range) + extreme boost (37%) → min=max → COLLAPSE.

        REAL SCENARIO: Foggy winter sunset (THE OVERFLOW WE DISCOVERED)
        CONDITIONS:
        - Zone: min=45, max=80 (35% range)
        - Environmental: fog(20) + lux(12) + winter(8) = 40% → 25% clamped
        - Sunset: elevation 0°, lux 600, boost = 12%
        - Combined: 25% + 12% = 37%

        CALCULATION: new_min = 45 + 37 = 82 > max(80) → collapse to 80

        THE BUG: Without boundary protection, AL would try to set min=82, max=80
        THE FIX: Boundary protection clamps min to max when min > max

        RESULT: min=80, max=80 → AL has 0% range to vary (lights stuck at 80%)

        THIS IS ACCEPTABLE COLLAPSE - extreme conditions, narrow zone config
        User should have configured wider range OR we should cap combined boost at 30%
        """
        zone_config = {
            "brightness_min": 45,
            "brightness_max": 80,  # Only 35% range
            "color_temp_min": 2250,
            "color_temp_max": 2950,
        }

        # Apply the combined boost we discovered in testing
        boundaries = calculate_boundaries(zone_config, brightness_offset=37, warmth_offset=0)

        # Verify boundary protection kicked in
        assert boundaries.min_brightness == 80, (
            f"Expected min=80 (clamped to max), got {boundaries.min_brightness}. "
            f"Boundary protection should prevent min > max."
        )
        assert boundaries.max_brightness == 80

        # Verify collapse occurred (0% range for AL)
        range_remaining = boundaries.max_brightness - boundaries.min_brightness
        assert range_remaining == 0, (
            f"Expected 0% range (COLLAPSE), got {range_remaining}%. "
            f"This zone configuration cannot handle 37% boost. "
            f"Either increase zone range to 40%+ OR cap combined boost at 30%."
        )

    def test_adequate_zone_with_extreme_boost_maintains_minimum_range(self):
        """Adequate zone (40% range) + extreme boost (37%) → 3% range → MINIMAL but OK.

        REAL SCENARIO: Same foggy winter sunset, but zone configured properly
        CONDITIONS:
        - Zone: min=45, max=85 (40% range)
        - Combined boost: 37%

        CALCULATION: new_min = 45 + 37 = 82, max = 85
        RESULT: min=82, max=85 → AL has 3% range to vary

        THIS IS ACCEPTABLE - minimal but still functional
        AL can vary brightness 82-85% following natural curve
        User explicitly configured zone to handle extreme scenarios
        """
        zone_config = {
            "brightness_min": 45,
            "brightness_max": 85,  # 40% range
            "color_temp_min": 2250,
            "color_temp_max": 2950,
        }

        boundaries = calculate_boundaries(zone_config, brightness_offset=37, warmth_offset=0)

        assert boundaries.min_brightness == 82, f"Expected min=82, got {boundaries.min_brightness}"
        assert boundaries.max_brightness == 85, f"Expected max=85, got {boundaries.max_brightness}"

        range_remaining = boundaries.max_brightness - boundaries.min_brightness
        assert range_remaining == 3, (
            f"Expected 3% range remaining, got {range_remaining}%. "
            f"This is minimal but acceptable - zone can handle extreme boost."
        )

    def test_wide_zone_with_extreme_boost_plus_manual(self):
        """Wide zone (45% range) handles WORST CASE: env + sunset + manual = 42%.

        REAL SCENARIO: Foggy winter sunset, user presses "brighter"
        CONDITIONS:
        - Zone: min=45, max=90 (45% range)
        - Environmental: 25%
        - Sunset: 12%
        - Manual: +5%
        - Total: 42%

        CALCULATION: new_min = 45 + 42 = 87, max = 90
        RESULT: min=87, max=90 → AL has 3% range

        THIS IS ACCEPTABLE - user explicitly requested MORE brightness
        System honors user preference while maintaining minimal AL variation
        """
        zone_config = {
            "brightness_min": 45,
            "brightness_max": 90,  # 45% range
            "color_temp_min": 2250,
            "color_temp_max": 2950,
        }

        # Total offset: env(25) + sunset(12) + manual(5)
        boundaries = calculate_boundaries(zone_config, brightness_offset=42, warmth_offset=0)

        assert boundaries.min_brightness == 87, f"Expected min=87, got {boundaries.min_brightness}"
        assert boundaries.max_brightness == 90, f"Expected max=90, got {boundaries.max_brightness}"

        range_remaining = boundaries.max_brightness - boundaries.min_brightness
        assert range_remaining == 3, (
            f"Expected 3% range remaining, got {range_remaining}%. "
            f"Even worst-case scenario (42% total boost) works with proper zone config."
        )


@pytest.mark.unit
@pytest.mark.adjustment_engine
class TestBoundaryValidation:
    """Test boundary validation logic."""

    def test_valid_brightness_range(self):
        """Valid brightness ranges should pass validation."""
        assert validate_brightness_range(0, 100) is True
        assert validate_brightness_range(45, 100) is True
        assert validate_brightness_range(1, 2) is True

    def test_invalid_brightness_range_min_equals_max(self):
        """Brightness range where min=max should fail validation."""
        assert validate_brightness_range(50, 50) is False

    def test_invalid_brightness_range_min_exceeds_max(self):
        """Brightness range where min>max should fail validation."""
        assert validate_brightness_range(80, 45) is False

    def test_invalid_brightness_range_out_of_bounds(self):
        """Brightness values outside 0-100 should fail validation."""
        assert validate_brightness_range(-1, 100) is False
        assert validate_brightness_range(0, 101) is False

    def test_valid_color_temp_range(self):
        """Valid color temp ranges should pass validation."""
        assert validate_color_temp_range(1500, 6500) is True
        assert validate_color_temp_range(2250, 2950) is True
        assert validate_color_temp_range(2000, 2001) is True

    def test_invalid_color_temp_range_min_equals_max(self):
        """Color temp range where min=max should fail validation."""
        assert validate_color_temp_range(2500, 2500) is False

    def test_invalid_color_temp_range_min_exceeds_max(self):
        """Color temp range where min>max should fail validation."""
        assert validate_color_temp_range(3000, 2500) is False

    def test_invalid_color_temp_range_out_of_bounds(self):
        """Color temp values outside 1500-6500 should fail validation."""
        assert validate_color_temp_range(1499, 6500) is False
        assert validate_color_temp_range(1500, 6501) is False


@pytest.mark.unit
@pytest.mark.adjustment_engine
class TestCombinedAdjustments:
    """Test combined brightness + color temp adjustments."""

    def test_positive_brightness_and_warmth_both_raise_mins(self):
        """Positive adjustments should raise both minimums.

        REAL SCENARIO: User wants brighter AND cooler
        EXPECTED: Both mins increase, both maxs unchanged
        """
        zone_config = {
            "brightness_min": 45,
            "brightness_max": 100,
            "color_temp_min": 2250,
            "color_temp_max": 2950,
        }

        boundaries = calculate_boundaries(
            zone_config,
            brightness_offset=20,
            warmth_offset=500,
        )

        # Brightness: min should increase
        assert boundaries.min_brightness == 65, f"Expected brightness min=65, got {boundaries.min_brightness}"
        assert boundaries.max_brightness == 100, "Brightness max should be unchanged"

        # Color temp: min should increase (cooler)
        assert boundaries.min_color_temp == 2750, f"Expected color temp min=2750K, got {boundaries.min_color_temp}K"
        assert boundaries.max_color_temp == 2950, "Color temp max should be unchanged"

    def test_negative_brightness_and_warmth_both_lower_maxs(self):
        """Negative adjustments should lower both maximums.

        REAL SCENARIO: User wants dimmer AND warmer
        EXPECTED: Both maxs decrease, both mins unchanged
        """
        zone_config = {
            "brightness_min": 45,
            "brightness_max": 100,
            "color_temp_min": 2250,
            "color_temp_max": 2950,
        }

        boundaries = calculate_boundaries(
            zone_config,
            brightness_offset=-20,
            warmth_offset=-500,
        )

        # Brightness: max should decrease
        assert boundaries.min_brightness == 45, "Brightness min should be unchanged"
        assert boundaries.max_brightness == 80, f"Expected brightness max=80, got {boundaries.max_brightness}"

        # Color temp: max should decrease (warmer)
        assert boundaries.min_color_temp == 2250, "Color temp min should be unchanged"
        assert boundaries.max_color_temp == 2450, f"Expected color temp max=2450K, got {boundaries.max_color_temp}K"

    def test_brightness_only_zone_ignores_warmth(self):
        """Brightness-only zone should ignore warmth adjustments.

        REAL SCENARIO: Recessed ceiling lights (brightness only, no color temp)
        EXPECTED: Warmth offset ignored, only brightness adjusted
        """
        zone_config = {
            "brightness_min": 45,
            "brightness_max": 100,
            # No color_temp_min/max - brightness only
        }

        boundaries = calculate_boundaries(
            zone_config,
            brightness_offset=20,
            warmth_offset=500,  # Should be ignored
        )

        # Brightness applied
        assert boundaries.min_brightness == 65
        assert boundaries.max_brightness == 100

        # Color temp should be None (not supported)
        assert boundaries.min_color_temp is None
        assert boundaries.max_color_temp is None
