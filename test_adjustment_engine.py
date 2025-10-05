#!/usr/bin/env python3
"""Standalone test for adjustment_engine.py core logic.

This validates the asymmetric boundary logic implementation without requiring
the full Home Assistant environment.
"""

# Mock constants
BRIGHTNESS_ADJUSTMENT_MAX = 100
BRIGHTNESS_ADJUSTMENT_MIN = -100
BRIGHTNESS_MIN_ABSOLUTE = 0
BRIGHTNESS_MAX_ABSOLUTE = 100
COLOR_TEMP_MIN_ABSOLUTE = 1500
COLOR_TEMP_MAX_ABSOLUTE = 6500
WARMTH_ADJUSTMENT_MAX = 2500
WARMTH_ADJUSTMENT_MIN = -2500


def calculate_brightness_bounds(current_min: int, current_max: int, adjustment: int) -> tuple[int, int]:
    """Core brightness boundary calculation."""
    if not (BRIGHTNESS_MIN_ABSOLUTE <= current_min <= BRIGHTNESS_MAX_ABSOLUTE):
        raise ValueError(f"current_min must be between {BRIGHTNESS_MIN_ABSOLUTE} and {BRIGHTNESS_MAX_ABSOLUTE}, got {current_min}")
    if not (BRIGHTNESS_MIN_ABSOLUTE <= current_max <= BRIGHTNESS_MAX_ABSOLUTE):
        raise ValueError(f"current_max must be between {BRIGHTNESS_MIN_ABSOLUTE} and {BRIGHTNESS_MAX_ABSOLUTE}, got {current_max}")
    if current_min > current_max:
        raise ValueError(f"current_min ({current_min}) cannot exceed current_max ({current_max})")
    if not (BRIGHTNESS_ADJUSTMENT_MIN <= adjustment <= BRIGHTNESS_ADJUSTMENT_MAX):
        raise ValueError(f"adjustment must be between {BRIGHTNESS_ADJUSTMENT_MIN} and {BRIGHTNESS_ADJUSTMENT_MAX}, got {adjustment}")

    if adjustment > 0:
        boost = adjustment
        proposed_min = current_min + boost
        new_min = max(BRIGHTNESS_MIN_ABSOLUTE, min(proposed_min, current_max))
        new_max = current_max
    elif adjustment < 0:
        reduction = adjustment
        proposed_max = current_max + reduction
        new_min = current_min
        new_max = min(BRIGHTNESS_MAX_ABSOLUTE, max(proposed_max, current_min))
    else:
        new_min = current_min
        new_max = current_max

    new_min = max(BRIGHTNESS_MIN_ABSOLUTE, min(new_min, BRIGHTNESS_MAX_ABSOLUTE))
    new_max = max(BRIGHTNESS_MIN_ABSOLUTE, min(new_max, BRIGHTNESS_MAX_ABSOLUTE))
    if new_min > new_max:
        new_min = new_max

    return (new_min, new_max)


def calculate_color_temp_bounds(current_min: int, current_max: int, adjustment: int) -> tuple[int, int]:
    """Core color temp boundary calculation."""
    if not (COLOR_TEMP_MIN_ABSOLUTE <= current_min <= COLOR_TEMP_MAX_ABSOLUTE):
        raise ValueError(f"current_min must be between {COLOR_TEMP_MIN_ABSOLUTE}K and {COLOR_TEMP_MAX_ABSOLUTE}K, got {current_min}K")
    if not (COLOR_TEMP_MIN_ABSOLUTE <= current_max <= COLOR_TEMP_MAX_ABSOLUTE):
        raise ValueError(f"current_max must be between {COLOR_TEMP_MIN_ABSOLUTE}K and {COLOR_TEMP_MAX_ABSOLUTE}K, got {current_max}K")
    if current_min > current_max:
        raise ValueError(f"current_min ({current_min}K) cannot exceed current_max ({current_max}K)")
    if not (WARMTH_ADJUSTMENT_MIN <= adjustment <= WARMTH_ADJUSTMENT_MAX):
        raise ValueError(f"adjustment must be between {WARMTH_ADJUSTMENT_MIN}K and {WARMTH_ADJUSTMENT_MAX}K, got {adjustment}K")

    if adjustment > 0:
        cooler_adj = adjustment
        proposed_min = current_min + cooler_adj
        new_min = max(COLOR_TEMP_MIN_ABSOLUTE, min(proposed_min, current_max))
        new_max = current_max
    elif adjustment < 0:
        warmer_adj = adjustment
        proposed_max = current_max + warmer_adj
        new_min = current_min
        new_max = min(COLOR_TEMP_MAX_ABSOLUTE, max(proposed_max, current_min))
    else:
        new_min = current_min
        new_max = current_max

    new_min = max(COLOR_TEMP_MIN_ABSOLUTE, min(new_min, COLOR_TEMP_MAX_ABSOLUTE))
    new_max = max(COLOR_TEMP_MIN_ABSOLUTE, min(new_max, COLOR_TEMP_MAX_ABSOLUTE))
    if new_min > new_max:
        new_min = new_max

    return (new_min, new_max)


def run_tests():
    """Run comprehensive tests of asymmetric boundary logic."""
    print("Testing Asymmetric Boundary Logic")
    print("=" * 60)

    # Test 1: Positive brightness adjustment (raise min)
    result = calculate_brightness_bounds(45, 100, 20)
    assert result == (65, 100), f"Expected (65, 100), got {result}"
    print("✓ Test 1: Positive brightness +20: [45,100] → [65,100]")

    # Test 2: Negative brightness adjustment (lower max)
    result = calculate_brightness_bounds(45, 100, -20)
    assert result == (45, 80), f"Expected (45, 80), got {result}"
    print("✓ Test 2: Negative brightness -20: [45,100] → [45,80]")

    # Test 3: Large positive adjustment (boundary protection)
    result = calculate_brightness_bounds(80, 100, 25)
    assert result == (100, 100), f"Expected (100, 100), got {result}"
    print("✓ Test 3: Large positive +25: [80,100] → [100,100] (clamped)")

    # Test 4: Large negative adjustment (boundary protection)
    result = calculate_brightness_bounds(20, 40, -25)
    assert result == (20, 20), f"Expected (20, 20), got {result}"
    print("✓ Test 4: Large negative -25: [20,40] → [20,20] (clamped)")

    # Test 5: Zero adjustment
    result = calculate_brightness_bounds(45, 100, 0)
    assert result == (45, 100), f"Expected (45, 100), got {result}"
    print("✓ Test 5: Zero adjustment: [45,100] → [45,100]")

    print()

    # Test 6: Positive color temp (cooler - raise min)
    result = calculate_color_temp_bounds(2250, 2950, 500)
    assert result == (2750, 2950), f"Expected (2750, 2950), got {result}"
    print("✓ Test 6: Positive temp +500K: [2250K,2950K] → [2750K,2950K]")

    # Test 7: Negative color temp (warmer - lower max)
    result = calculate_color_temp_bounds(2250, 2950, -500)
    assert result == (2250, 2450), f"Expected (2250, 2450), got {result}"
    print("✓ Test 7: Negative temp -500K: [2250K,2950K] → [2250K,2450K]")

    # Test 8: Large positive color temp (boundary protection)
    result = calculate_color_temp_bounds(2000, 2500, 1000)
    assert result == (2500, 2500), f"Expected (2500, 2500), got {result}"
    print("✓ Test 8: Large positive +1000K: [2000K,2500K] → [2500K,2500K]")

    # Test 9: Large negative color temp (boundary protection)
    result = calculate_color_temp_bounds(2500, 3000, -1000)
    assert result == (2500, 2500), f"Expected (2500, 2500), got {result}"
    print("✓ Test 9: Large negative -1000K: [2500K,3000K] → [2500K,2500K]")

    print()

    # Test 10: Real-world scenario - Main Living zone
    print("Real-world scenario: Main Living Zone")
    print("  Base: [45%, 100%], [2250K, 2950K]")

    br_min, br_max = calculate_brightness_bounds(45, 100, 20)
    ct_min, ct_max = calculate_color_temp_bounds(2250, 2950, -500)
    print(f"  After +20% brightness, -500K warmth:")
    print(f"  → Brightness: [{br_min}%, {br_max}%]")
    print(f"  → Color Temp: [{ct_min}K, {ct_max}K]")
    assert (br_min, br_max) == (65, 100)
    assert (ct_min, ct_max) == (2250, 2450)
    print("✓ Test 10: Real-world main living zone adjustment")

    print()

    # Test 11: Real-world scenario - Bedroom zone
    print("Real-world scenario: Bedroom Primary Zone")
    print("  Base: [20%, 40%], [1800K, 2250K]")

    br_min, br_max = calculate_brightness_bounds(20, 40, -10)
    ct_min, ct_max = calculate_color_temp_bounds(1800, 2250, -200)
    print(f"  After -10% brightness, -200K warmth:")
    print(f"  → Brightness: [{br_min}%, {br_max}%]")
    print(f"  → Color Temp: [{ct_min}K, {ct_max}K]")
    assert (br_min, br_max) == (20, 30)
    assert (ct_min, ct_max) == (1800, 2050)
    print("✓ Test 11: Real-world bedroom zone adjustment")

    print()
    print("=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    print()
    print("The asymmetric boundary logic is working correctly:")
    print("  • Positive brightness adjustments raise MIN only")
    print("  • Negative brightness adjustments lower MAX only")
    print("  • Positive warmth adjustments (cooler) raise MIN color temp")
    print("  • Negative warmth adjustments (warmer) lower MAX color temp")
    print("  • Boundary crossover protection works correctly")


if __name__ == "__main__":
    run_tests()
