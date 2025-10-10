from __future__ import annotations

import pytest

from custom_components.al_layer_manager.services import (
    ServiceContractError,
    validate_manual_service,
    validate_mode_service,
)


def test_validate_manual_service() -> None:
    validate_manual_service({"zone_id": "office", "brightness": 0.5, "kelvin": 3200})
    with pytest.raises(ServiceContractError):
        validate_manual_service({"zone_id": "office", "brightness": 1.5, "kelvin": 3200})
    with pytest.raises(ServiceContractError):
        validate_manual_service({"brightness": 0.5, "kelvin": 3200})


def test_validate_mode_service() -> None:
    validate_mode_service({"zone_id": "office", "mode": "focus", "brightness_multiplier": 1.1, "kelvin_adjustment": 300})
    with pytest.raises(ServiceContractError):
        validate_mode_service({"zone_id": "office", "mode": "focus", "brightness_multiplier": 0, "kelvin_adjustment": 300})
    with pytest.raises(ServiceContractError):
        validate_mode_service({"zone_id": "office", "mode": "focus", "brightness_multiplier": 1.1, "kelvin_adjustment": 300, "transition_seconds": 0})
