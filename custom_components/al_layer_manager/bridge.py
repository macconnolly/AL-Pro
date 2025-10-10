"""Bridge between AL layer orchestration and layer_manager services."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .models import LayerUpdate, ZoneModel


@dataclass(slots=True)
class LayerCommand:
    """Encapsulates a layer_manager service invocation."""

    service: str
    data: Dict[str, object]
    description: str | None = None


class LayerManagerBridge:
    """Translates computed layer updates into layer_manager service calls."""

    def __init__(self, layer_domain: str = "layer_manager") -> None:
        self._layer_domain = layer_domain
        self._active_layers: Dict[Tuple[str, str], Tuple[tuple, LayerUpdate]] = {}

    def sync_zone(self, zone: ZoneModel, updates: Iterable[LayerUpdate]) -> List[LayerCommand]:
        desired: Dict[str, LayerUpdate] = {update.layer_id: update for update in updates}
        commands: List[LayerCommand] = []

        current_keys = {
            key: payload
            for key, payload in self._active_layers.items()
            if key[0] == zone.zone_id
        }

        # Determine removals first
        for (zone_id, layer_id), (_, stored_update) in list(current_keys.items()):
            if layer_id not in desired:
                commands.extend(self._remove_layer(zone, layer_id))
                self._active_layers.pop((zone_id, layer_id), None)

        # Determine inserts / updates
        for layer_id, update in desired.items():
            key = (zone.zone_id, layer_id)
            payload_hash = update.payload_hash()
            if key not in self._active_layers or self._active_layers[key][0] != payload_hash:
                commands.extend(self._insert_layer(zone, update))
                self._active_layers[key] = (payload_hash, update)

        return commands

    def _insert_layer(self, zone: ZoneModel, update: LayerUpdate) -> List[LayerCommand]:
        brightness = max(1, min(255, round(update.brightness * 255)))
        attributes: Dict[str, object] = {
            "brightness": brightness,
            "color_temp_kelvin": update.kelvin,
            "transition": update.transition,
        }
        if update.reason:
            attributes["al_reason"] = update.reason

        commands: List[LayerCommand] = []
        for entity_id in zone.lights:
            commands.append(
                LayerCommand(
                    service=f"{self._layer_domain}.insert_state",
                    data={
                        "entity_id": entity_id,
                        "id": update.layer_id,
                        "priority": update.priority,
                        "state": update.state,
                        "attributes": attributes,
                        "clear_layer": True,
                    },
                    description=f"Apply {update.layer_id} to {entity_id}",
                )
            )
        return commands

    def _remove_layer(self, zone: ZoneModel, layer_id: str) -> List[LayerCommand]:
        commands: List[LayerCommand] = []
        for entity_id in zone.lights:
            commands.append(
                LayerCommand(
                    service=f"{self._layer_domain}.remove_layer",
                    data={
                        "entity_id": entity_id,
                        "id": layer_id,
                    },
                    description=f"Remove {layer_id} from {entity_id}",
                )
            )
        return commands

    def snapshot(self) -> Dict[Tuple[str, str], LayerUpdate]:
        return {key: update for key, (_, update) in self._active_layers.items()}
