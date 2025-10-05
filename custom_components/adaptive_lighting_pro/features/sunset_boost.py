"""Sunset boost for Adaptive Lighting Pro.

This module provides additional brightness boost on dark/cloudy days during sunset.

Purpose:
- On CLEAR days (lux > 3000): Do nothing - AL handles sunset naturally
- On DARK/CLOUDY days (lux < 3000): Provide extra boost during sunset
  - Already dark due to weather conditions
  - Gets even darker as sun sets
  - Need extra compensation for the "double whammy"

CRITICAL FIX from original YAML:
The original implementation (YAML lines 2414-2455) had this backwards!
- YAML: Dimmed lights during sunset (negative offset -25%)
- Correct: Boost lights on dark days during sunset (positive offset +25%)

This is a fundamental logic correction based on actual user needs.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class SunsetBoostCalculator:
    """Calculate brightness boost on dark days during sunset.

    This calculator provides extra brightness compensation when:
    1. It's already a dark/cloudy day (low lux)
    2. Sun is setting (losing what little natural light exists)
    3. Environmental boost alone isn't enough for the rapid darkening

    Returns POSITIVE offset to raise brightness.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize sunset boost calculator.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass
        self._enabled: bool = False
        self._last_breakdown: dict[str, Any] = {}

    def configure(self, enabled: bool = False) -> None:
        """Configure sunset boost feature.

        Args:
            enabled: Enable sunset boost calculations
        """
        self._enabled = enabled
        _LOGGER.info("Sunset boost calculator configured: enabled=%s", enabled)

    def calculate_boost(self, current_lux: float | None = None) -> tuple[int, dict[str, Any]]:
        """Calculate brightness boost for dark days during sunset with detailed breakdown.

        Logic (CORRECTED from original YAML):
        - Active only when -4° <= elevation <= 4° (sunset window)
        - ONLY applies on dark/cloudy days (lux < 3000)
        - Returns POSITIVE offset (0 to +25%) to boost brightness
        - Formula: boost = ((4 - elevation) / 8 * 25)

        Why this is needed:
        - Dark cloudy day already has environmental boost active
        - But at sunset, it gets EVEN DARKER rapidly
        - Need extra boost to compensate for combined effect

        Args:
            current_lux: Current outdoor lux reading (REQUIRED)

        Returns:
            Tuple of (boost_percentage, breakdown_dict)

        Examples:
            >>> # Clear day (lux=8000), sun at 0° (sunset)
            >>> boost, breakdown = calculator.calculate_boost(current_lux=8000)
            >>> boost
            0

            >>> # Cloudy/stormy day (lux=500), sun at 0° (sunset)
            >>> boost, breakdown = calculator.calculate_boost(current_lux=500)
            >>> boost
            12
        """
        # Build initial breakdown
        breakdown = {
            "boost_pct": 0,
            "lux_value": int(current_lux) if current_lux else 0,
            "sun_elevation": 0.0,
            "in_sunset_window": False,
            "active": False,
            "reason_skipped": None
        }

        if not self.is_available():
            breakdown["reason_skipped"] = "disabled"
            self._last_breakdown = breakdown
            return 0, breakdown

        # CRITICAL: Only apply on dark/cloudy days
        # Clear days don't need sunset boost - AL handles them fine
        if current_lux is None or current_lux >= 3000:
            breakdown["reason_skipped"] = "bright_day"
            _LOGGER.debug(
                "Skipping sunset boost - bright/clear day (lux=%.0f >= 3000). "
                "AL will handle sunset transition naturally.",
                current_lux if current_lux else 0,
            )
            self._last_breakdown = breakdown
            return 0, breakdown

        sun_state = self.hass.states.get("sun.sun")
        if not sun_state:
            breakdown["reason_skipped"] = "sun_unavailable"
            _LOGGER.warning("sun.sun entity not found")
            self._last_breakdown = breakdown
            return 0, breakdown

        elevation = sun_state.attributes.get("elevation")
        if elevation is None:
            breakdown["reason_skipped"] = "elevation_unavailable"
            _LOGGER.warning("Sun elevation not available")
            self._last_breakdown = breakdown
            return 0, breakdown

        try:
            elevation = float(elevation)
            breakdown["sun_elevation"] = round(elevation, 1)
        except (ValueError, TypeError):
            breakdown["reason_skipped"] = "invalid_elevation"
            _LOGGER.warning("Invalid sun elevation: %s", elevation)
            self._last_breakdown = breakdown
            return 0, breakdown

        # Only active in sunset window (-4° to 4°)
        in_window = -4 <= elevation <= 4
        breakdown["in_sunset_window"] = in_window

        if not in_window:
            breakdown["reason_skipped"] = "outside_window"
            self._last_breakdown = breakdown
            return 0, breakdown

        # Calculate boost - LINEAR SCALE
        # elevation 4° = 0%, elevation 0° = +12.5%, elevation -4° = +25%
        # CORRECTED: Positive offset (boost) instead of negative (dim)
        boost = int(((4 - elevation) / 8 * 25))

        breakdown["boost_pct"] = boost
        breakdown["active"] = boost > 0

        if boost > 0:
            _LOGGER.info(
                "Sunset boost: +%d%% (dark day during sunset - sun=%.1f°, lux=%.0f)",
                boost,
                elevation,
                current_lux,
            )

        self._last_breakdown = breakdown
        return boost, breakdown

    def get_breakdown(self) -> dict[str, Any]:
        """Get detailed breakdown of last boost calculation.

        Returns:
            Dictionary with boost components and reason for skipping (if applicable)
        """
        return self._last_breakdown.copy() if self._last_breakdown else {}

    def is_available(self) -> bool:
        """Check if sunset boost is enabled and sun sensor is available.

        Returns:
            True if sunset boost is enabled
        """
        if not self._enabled:
            return False

        sun_state = self.hass.states.get("sun.sun")
        return sun_state is not None and sun_state.state not in ("unknown", "unavailable")
