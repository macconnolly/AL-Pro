"""Manual control detection for Adaptive Lighting Pro.

This module detects when lights have been manually controlled and calculates
smart timeout durations before returning to adaptive control.

Ported from implementation_1.yaml lines 721-862, 1715-1843.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ManualControlDetector:
    """Detect manual control and calculate smart timeouts.

    This detector monitors Adaptive Lighting switches to identify zones with
    manual control, then calculates context-aware timeout durations.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize manual control detector.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass

    def check_zone(self, zone_id: str) -> list[str]:
        """Check if zone has manually controlled lights.

        Queries the Adaptive Lighting switch's manual_control attribute to
        identify lights that have been manually adjusted.

        Args:
            zone_id: Zone identifier (e.g., "main_living")

        Returns:
            List of manually controlled light entity IDs

        Examples:
            >>> detector.check_zone("main_living")
            ["light.living_room_couch_lamp", "light.living_room_floor_lamp"]
        """
        switch_entity_id = f"switch.adaptive_lighting_{zone_id}"
        switch_state = self.hass.states.get(switch_entity_id)

        if not switch_state or switch_state.state not in ("on", "off"):
            _LOGGER.debug("Switch %s not available", switch_entity_id)
            return []

        # Get manual_control attribute (list of entity IDs)
        manual_control_lights = switch_state.attributes.get("manual_control", [])

        if manual_control_lights:
            _LOGGER.debug(
                "Zone %s has %d manually controlled lights: %s",
                zone_id,
                len(manual_control_lights),
                manual_control_lights,
            )
        else:
            _LOGGER.debug("Zone %s has no manual control", zone_id)

        return manual_control_lights

    def calculate_smart_timeout(
        self,
        zone_id: str,
        sun_elevation: float | None = None,
        env_boost: int = 0,
    ) -> int:
        """Calculate smart timeout duration for manual control.

        Simplified logic for mode-less architecture:
        - Base timeout: 30 minutes (1800s)
        - Extended at night (sun below horizon): 1.5x
        - Extended in dim conditions (environmental boost active): 1.3x
        - Maximum: 2 hours (7200s)

        Args:
            zone_id: Zone identifier
            sun_elevation: Sun elevation in degrees (None = unknown)
            env_boost: Environmental brightness boost percentage (0-25)

        Returns:
            Timeout duration in seconds (1800-7200)

        Examples:
            >>> detector.calculate_smart_timeout("main_living", -10, 15)
            3510  # Night (1.5x) with dim conditions (1.3x) = 1800 * 1.95 = 3510s

            >>> detector.calculate_smart_timeout("kitchen_island", 45, 0)
            1800  # Daytime, clear conditions = 30 minutes base
        """
        # Base timeout: 30 minutes
        base_timeout = 1800

        # Multiplier adjustments
        multiplier = 1.0

        # Night extension (sun below -6° = astronomical dusk/dawn)
        if sun_elevation is not None and sun_elevation < -6:
            multiplier *= 1.5
            _LOGGER.debug("Night condition (sun < -6°) → timeout multiplier: 1.5x")

        # Dim conditions extension (environmental boost > 10%)
        if env_boost > 10:
            multiplier *= 1.3
            _LOGGER.debug("Dim conditions (boost > 10%%) → timeout multiplier: 1.3x")

        # Calculate final timeout
        final_timeout = int(base_timeout * multiplier)

        # Clamp to maximum 2 hours
        final_timeout = min(final_timeout, 7200)

        _LOGGER.info(
            "Smart timeout for zone %s: %ds (base=%ds, multiplier=%.2fx, sun_elev=%s, env_boost=%d%%)",
            zone_id,
            final_timeout,
            base_timeout,
            multiplier,
            f"{sun_elevation:.1f}°" if sun_elevation is not None else "unknown",
            env_boost,
        )

        return final_timeout
