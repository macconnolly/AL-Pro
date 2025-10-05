"""Validation utilities for config flow and services."""
from __future__ import annotations

from typing import Iterable, List

from homeassistant.core import HomeAssistant

from ..const import DOMAIN


class ValidationError(Exception):
    """Raised when configuration data is invalid."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def is_adaptive_lighting_switch(hass: HomeAssistant, entity_id: str) -> bool:
    """Return True if entity appears to be an Adaptive Lighting switch."""
    if not entity_id.startswith("switch."):
        return False
    state = hass.states.get(entity_id)
    if state is None:
        return False
    integration = state.attributes.get("integration") or state.attributes.get("source")
    return isinstance(integration, str) and integration.lower().startswith("adaptive_lighting")


def validate_lights(lights: Iterable[str] | str) -> List[str]:
    """Validate that lights are well-formed entity IDs."""
    if isinstance(lights, str):
        candidate_iterable: Iterable[str] = [lights]
    else:
        candidate_iterable = lights
    validated: List[str] = []
    for entity_id in candidate_iterable:
        if not entity_id.startswith("light."):
            raise ValidationError("lights", f"Invalid light entity_id: {entity_id}")
        validated.append(entity_id)
    return validated


def validate_zone_id(zone_id: str, existing: Iterable[str]) -> str:
    """Ensure zone id is unique within config."""
    if not zone_id:
        raise ValidationError("zone_id", "Zone id is required")
    if zone_id in existing:
        raise ValidationError("zone_id", f"Duplicate zone id {zone_id}")
    return zone_id


def ensure_not_empty(value: Iterable[object], field: str) -> None:
    if not list(value):
        raise ValidationError(field, f"{field} cannot be empty")


def ensure_uuid(value: str) -> str:
    """Ensure installation id is a valid UUID string."""
    import uuid

    try:
        uuid.UUID(value)
    except (ValueError, AttributeError) as exc:  # pragma: no cover - defensive
        raise ValidationError("installation_id", "Invalid installation UUID") from exc
    return value


def validate_zone_config(
    hass: HomeAssistant,
    zone: dict,
    existing_ids: Iterable[str],
) -> dict:
    """Validate a zone configuration dict."""
    zone_id = validate_zone_id(zone.get("zone_id", ""), existing_ids)
    al_switch = zone.get("al_switch")
    if not isinstance(al_switch, str) or not is_adaptive_lighting_switch(hass, al_switch):
        raise ValidationError("al_switch", "Switch must be Adaptive Lighting")
    lights = validate_lights(zone.get("lights", []))
    ensure_not_empty(lights, "lights")
    zone_multiplier = float(zone.get("zone_multiplier", 1.0))
    sunrise_offset = int(zone.get("sunrise_offset_min", 0))
    return {
        "zone_id": zone_id,
        "al_switch": al_switch,
        "lights": lights,
        "enabled": bool(zone.get("enabled", True)),
        "zone_multiplier": zone_multiplier,
        "sunrise_offset_min": sunrise_offset,
        "environmental_boost_enabled": bool(
            zone.get("environmental_boost_enabled", True)
        ),
        "sunset_boost_enabled": bool(zone.get("sunset_boost_enabled", True)),
    }


def validate_rate_limit(config: dict) -> dict:
    max_events = int(config.get("max_events", 10))
    window_sec = int(config.get("window_sec", 30))
    if max_events <= 0 or window_sec <= 0:
        raise ValidationError("rate_limit", "Invalid rate limit configuration")
    return {"max_events": max_events, "window_sec": window_sec}


def validate_mode(mode: str) -> str:
    valid = {"adaptive", "work", "focus", "relax", "movie", "late_night"}
    if mode not in valid:
        raise ValidationError("mode", f"Unknown mode {mode}")
    return mode


def validate_scene(scene: str) -> str:
    valid = {"default", "all_lights", "no_spots", "evening_comfort", "ultra_dim"}
    if scene not in valid:
        raise ValidationError("scene", f"Unknown scene {scene}")
    return scene
