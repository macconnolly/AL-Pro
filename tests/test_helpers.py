from __future__ import annotations

from custom_components.al_layer_manager.helpers import HelperEntity, HelperRegistry


def test_helper_registry_validation() -> None:
    registry = HelperRegistry(
        helpers=[
            HelperEntity("input_boolean.office_manual", "input_boolean", "Manual override toggle"),
            HelperEntity("input_number.office_brightness", "input_number", "Brightness helper"),
        ]
    )
    errors = registry.validate({
        "manual_toggle": "input_boolean.office_manual",
        "brightness": "input_number.office_brightness",
    })
    assert not errors

    errors = registry.validate({"unknown": "input_select.unsupported"})
    assert errors

    created = registry.ensure_helper("input_datetime.override", "input_datetime", "Override timer")
    assert created.entity_id == "input_datetime.override"
    assert any(helper.entity_id == "input_datetime.override" for helper in registry.list())
