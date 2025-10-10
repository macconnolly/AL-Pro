from __future__ import annotations

from custom_components.al_layer_manager.bridge import LayerManagerBridge
from custom_components.al_layer_manager.models import LayerUpdate


def test_bridge_generates_insert_and_remove(sample_zone) -> None:
    bridge = LayerManagerBridge()
    update = LayerUpdate(
        layer_id=f"{sample_zone.zone_id}_manual",
        priority=40,
        brightness=0.8,
        kelvin=3400,
        transition=1,
        reason="test",
    )
    commands = bridge.sync_zone(sample_zone, [update])
    assert all(command.service == "layer_manager.insert_state" for command in commands)
    assert commands[0].data["attributes"]["brightness"] == round(0.8 * 255)

    removal_commands = bridge.sync_zone(sample_zone, [])
    assert all(command.service == "layer_manager.remove_layer" for command in removal_commands)
    assert removal_commands[0].data["id"].endswith("manual")
