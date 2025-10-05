"""Service schema definitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(slots=True)
class ServiceCall:
    name: str
    payload: Dict[str, Any]


class ServiceContractError(ValueError):
    pass


def validate_manual_service(payload: Dict[str, Any]) -> None:
    required = {"zone_id", "brightness", "kelvin"}
    missing = required - payload.keys()
    if missing:
        raise ServiceContractError(f"Missing fields: {', '.join(sorted(missing))}")
    if not 0 <= float(payload["brightness"]) <= 1:
        raise ServiceContractError("Brightness must be between 0 and 1")
    if not 1800 <= int(payload["kelvin"]) <= 7000:
        raise ServiceContractError("Kelvin out of range")


def validate_mode_service(payload: Dict[str, Any]) -> None:
    required = {"mode", "brightness_multiplier", "kelvin_adjustment"}
    missing = required - payload.keys()
    if missing:
        raise ServiceContractError(f"Missing fields: {', '.join(sorted(missing))}")
    if float(payload["brightness_multiplier"]) <= 0:
        raise ServiceContractError("Brightness multiplier must be positive")
    if not -2000 <= int(payload["kelvin_adjustment"]) <= 2000:
        raise ServiceContractError("Kelvin adjustment out of range")
