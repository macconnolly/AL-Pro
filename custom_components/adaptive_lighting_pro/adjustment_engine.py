"""Adjustment engine for Adaptive Lighting Pro.

This module implements the core asymmetric boundary logic for manual brightness
and color temperature adjustments. This is the key innovation that allows users
to make manual adjustments while preserving adaptive lighting behavior.

Asymmetric Boundary Logic:
-------------------------
The asymmetric approach adjusts ONLY one boundary (min or max) based on the
direction of the adjustment:

Brightness:
- Positive adjustment (brighter) → Raise MIN only, keep MAX
- Negative adjustment (dimmer) → Lower MAX only, keep MIN

Color Temperature:
- Positive adjustment (cooler/higher K) → Raise MIN only
- Negative adjustment (warmer/lower K) → Lower MAX only

This prevents the adaptive lighting from working against user preferences while
still allowing natural variation within the adjusted range.

Ported from implementation_1.yaml lines 1845-1881.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TypedDict

from .const import (
    BRIGHTNESS_ADJUSTMENT_MAX,
    BRIGHTNESS_ADJUSTMENT_MIN,
    CONF_BRIGHTNESS_MAX,
    CONF_BRIGHTNESS_MIN,
    CONF_COLOR_TEMP_MAX,
    CONF_COLOR_TEMP_MIN,
    WARMTH_ADJUSTMENT_MAX,
    WARMTH_ADJUSTMENT_MIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class Boundaries:
    """Calculated brightness and color temperature boundaries for a zone.

    This represents the final min/max values that should be applied to an
    Adaptive Lighting switch after applying all offsets and mode configurations.
    """
    min_brightness: int
    max_brightness: int
    min_color_temp: int | None
    max_color_temp: int | None


class AdjustedZoneConfig(TypedDict, total=False):
    """Type definition for adjusted zone configuration."""

    brightness_min: int
    brightness_max: int
    color_temp_min: int | None
    color_temp_max: int | None


def calculate_brightness_bounds(
    current_min: int,
    current_max: int,
    adjustment: int,
) -> tuple[int, int]:
    """Calculate new brightness bounds using asymmetric adjustment.

    Implements the asymmetric boundary logic from implementation_1.yaml:1845-1857

    Args:
        current_min: Current minimum brightness (0-100)
        current_max: Current maximum brightness (0-100)
        adjustment: Brightness adjustment in percent (-100 to +100)

    Returns:
        Tuple of (new_min, new_max)

    Raises:
        ValueError: If inputs are invalid

    Examples:
        >>> calculate_brightness_bounds(45, 100, 20)
        (65, 100)  # Positive: raise min only

        >>> calculate_brightness_bounds(45, 100, -20)
        (45, 80)  # Negative: lower max only

        >>> calculate_brightness_bounds(45, 100, 0)
        (45, 100)  # Zero: no change
    """
    # Validate inputs
    if not (0 <= current_min <= 100):
        raise ValueError(f"Invalid current_min: {current_min}")
    if not (0 <= current_max <= 100):
        raise ValueError(f"Invalid current_max: {current_max}")
    if current_min > current_max:
        raise ValueError(f"Min {current_min} exceeds max {current_max}")
    if not (BRIGHTNESS_ADJUSTMENT_MIN <= adjustment <= BRIGHTNESS_ADJUSTMENT_MAX):
        raise ValueError(f"Invalid adjustment: {adjustment}")

    # Apply asymmetric logic
    if adjustment > 0:
        # Positive adjustment: raise minimum only
        new_min = min(current_min + adjustment, 100)
        new_max = current_max

        # Boundary protection: prevent min > max
        if new_min > new_max:
            new_min = new_max

        _LOGGER.debug(
            "Brightness positive adjustment: min %d→%d, max %d (unchanged), adj=%d",
            current_min,
            new_min,
            new_max,
            adjustment,
        )

    elif adjustment < 0:
        # Negative adjustment: lower maximum only
        new_min = current_min
        new_max = max(current_max + adjustment, 0)

        # Boundary protection: prevent max < min
        if new_max < new_min:
            new_max = new_min

        _LOGGER.debug(
            "Brightness negative adjustment: min %d (unchanged), max %d→%d, adj=%d",
            new_min,
            current_max,
            new_max,
            adjustment,
        )

    else:
        # Zero adjustment: no change
        new_min = current_min
        new_max = current_max

    return (new_min, new_max)


def calculate_color_temp_bounds(
    current_min: int,
    current_max: int,
    adjustment: int,
) -> tuple[int, int]:
    """Calculate new color temperature bounds using asymmetric adjustment.

    Implements the asymmetric boundary logic from implementation_1.yaml:1859-1879

    Args:
        current_min: Current minimum color temp in Kelvin (1500-6500)
        current_max: Current maximum color temp in Kelvin (1500-6500)
        adjustment: Color temp adjustment in Kelvin (-2500 to +2500)
                   Positive = cooler, Negative = warmer

    Returns:
        Tuple of (new_min, new_max)

    Raises:
        ValueError: If inputs are invalid

    Examples:
        >>> calculate_color_temp_bounds(2250, 2950, 500)
        (2750, 2950)  # Positive (cooler): raise min only

        >>> calculate_color_temp_bounds(2250, 2950, -500)
        (2250, 2450)  # Negative (warmer): lower max only
    """
    # Validate inputs
    if not (1500 <= current_min <= 6500):
        raise ValueError(f"Invalid current_min: {current_min}K")
    if not (1500 <= current_max <= 6500):
        raise ValueError(f"Invalid current_max: {current_max}K")
    if current_min > current_max:
        raise ValueError(f"Min {current_min}K exceeds max {current_max}K")
    if not (WARMTH_ADJUSTMENT_MIN <= adjustment <= WARMTH_ADJUSTMENT_MAX):
        raise ValueError(f"Invalid adjustment: {adjustment}K")

    # Apply asymmetric logic
    if adjustment > 0:
        # Positive adjustment (cooler): raise minimum only
        new_min = min(current_min + adjustment, 6500)
        new_max = current_max

        # Boundary protection: prevent min > max
        if new_min > new_max:
            new_min = new_max

        _LOGGER.debug(
            "Color temp positive adjustment (cooler): min %dK→%dK, max %dK (unchanged), adj=%+dK",
            current_min,
            new_min,
            new_max,
            adjustment,
        )

    elif adjustment < 0:
        # Negative adjustment (warmer): lower maximum only
        new_min = current_min
        new_max = max(current_max + adjustment, 1500)

        # Boundary protection: prevent max < min
        if new_max < new_min:
            new_max = new_min

        _LOGGER.debug(
            "Color temp negative adjustment (warmer): min %dK (unchanged), max %dK→%dK, adj=%+dK",
            new_min,
            current_max,
            new_max,
            adjustment,
        )

    else:
        # Zero adjustment: no change
        new_min = current_min
        new_max = current_max

    return (new_min, new_max)


def validate_brightness_range(min_val: int, max_val: int) -> bool:
    """Validate brightness range.

    Args:
        min_val: Minimum brightness (0-100)
        max_val: Maximum brightness (0-100)

    Returns:
        True if valid, False otherwise
    """
    return 0 <= min_val < max_val <= 100


def validate_color_temp_range(min_val: int, max_val: int) -> bool:
    """Validate color temperature range.

    Args:
        min_val: Minimum color temp in Kelvin
        max_val: Maximum color temp in Kelvin

    Returns:
        True if valid, False otherwise
    """
    return 1500 <= min_val < max_val <= 6500


def apply_adjustment_to_zone(
    zone_config: dict,
    brightness_adjustment: int,
    warmth_adjustment: int,
) -> AdjustedZoneConfig:
    """Apply manual adjustments to a zone configuration.

    This is the main entry point for applying asymmetric adjustments to a zone.
    It handles both brightness and color temperature adjustments simultaneously.

    Args:
        zone_config: Zone configuration dict with current bounds
        brightness_adjustment: Brightness adjustment in percent (-100 to +100)
        warmth_adjustment: Color temp adjustment in Kelvin (-2500 to +2500)

    Returns:
        Updated zone configuration with adjusted bounds

    Raises:
        ValueError: If current bounds or adjustments are invalid
    """
    # Extract current bounds
    current_brightness_min = zone_config.get(CONF_BRIGHTNESS_MIN, 0)
    current_brightness_max = zone_config.get(CONF_BRIGHTNESS_MAX, 100)
    current_color_temp_min = zone_config.get(CONF_COLOR_TEMP_MIN)
    current_color_temp_max = zone_config.get(CONF_COLOR_TEMP_MAX)

    # Apply brightness adjustment
    new_brightness_min, new_brightness_max = calculate_brightness_bounds(
        current_brightness_min,
        current_brightness_max,
        brightness_adjustment,
    )

    # Apply color temp adjustment (if zone supports color temp)
    if current_color_temp_min is not None and current_color_temp_max is not None:
        new_color_temp_min, new_color_temp_max = calculate_color_temp_bounds(
            current_color_temp_min,
            current_color_temp_max,
            warmth_adjustment,
        )
    else:
        # Brightness-only zone (e.g., recessed ceiling)
        new_color_temp_min = None
        new_color_temp_max = None
        if warmth_adjustment != 0:
            _LOGGER.warning(
                "Zone %s is brightness-only, ignoring warmth adjustment %d",
                zone_config.get("zone_id", "unknown"),
                warmth_adjustment,
            )

    _LOGGER.info(
        "Applied adjustments to zone %s: brightness [%d,%d]→[%d,%d], color_temp [%s,%s]→[%s,%s]",
        zone_config.get("zone_id", "unknown"),
        current_brightness_min,
        current_brightness_max,
        new_brightness_min,
        new_brightness_max,
        current_color_temp_min,
        current_color_temp_max,
        new_color_temp_min,
        new_color_temp_max,
    )

    return AdjustedZoneConfig(
        brightness_min=new_brightness_min,
        brightness_max=new_brightness_max,
        color_temp_min=new_color_temp_min,
        color_temp_max=new_color_temp_max,
    )


def calculate_boundaries(
    zone_config: dict,
    brightness_offset: int,
    warmth_offset: int,
) -> Boundaries:
    """Calculate final boundaries for a zone with all offsets applied.

    This is the primary interface used by the coordinator to calculate the
    boundaries that should be applied to an Adaptive Lighting switch.

    Args:
        zone_config: Zone configuration dict with base min/max values
        brightness_offset: Total brightness offset in percent (-100 to +100)
        warmth_offset: Total warmth offset in Kelvin (-2500 to +2500)

    Returns:
        Boundaries object with final min/max values

    Examples:
        >>> zone = {"brightness_min": 45, "brightness_max": 100, "color_temp_min": 2250, "color_temp_max": 2950}
        >>> calculate_boundaries(zone, 20, -500)
        Boundaries(min_brightness=65, max_brightness=100, min_color_temp=2250, max_color_temp=2450)
    """
    # Extract base bounds from zone config
    base_brightness_min = zone_config.get(CONF_BRIGHTNESS_MIN, 0)
    base_brightness_max = zone_config.get(CONF_BRIGHTNESS_MAX, 100)
    base_color_temp_min = zone_config.get(CONF_COLOR_TEMP_MIN)
    base_color_temp_max = zone_config.get(CONF_COLOR_TEMP_MAX)

    # Apply asymmetric brightness adjustment
    final_brightness_min, final_brightness_max = calculate_brightness_bounds(
        base_brightness_min,
        base_brightness_max,
        brightness_offset,
    )

    # Apply asymmetric color temp adjustment (if zone supports it)
    if base_color_temp_min is not None and base_color_temp_max is not None:
        final_color_temp_min, final_color_temp_max = calculate_color_temp_bounds(
            base_color_temp_min,
            base_color_temp_max,
            warmth_offset,
        )
    else:
        # Brightness-only zone
        final_color_temp_min = None
        final_color_temp_max = None

    return Boundaries(
        min_brightness=final_brightness_min,
        max_brightness=final_brightness_max,
        min_color_temp=final_color_temp_min,
        max_color_temp=final_color_temp_max,
    )
