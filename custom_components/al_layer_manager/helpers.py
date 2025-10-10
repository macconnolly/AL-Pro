"""Helper registry ingestion stubs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(slots=True)
class HelperEntity:
    entity_id: str
    domain: str
    description: str


class HelperRegistry:
    """In-memory helper catalog representing HA registry."""

    SUPPORTED_DOMAINS = {"input_boolean", "input_number", "input_select", "input_datetime"}

    def __init__(self, helpers: Iterable[HelperEntity]) -> None:
        self._helpers: Dict[str, HelperEntity] = {helper.entity_id: helper for helper in helpers}

    def validate(self, bindings: Dict[str, str]) -> List[str]:
        errors: List[str] = []
        for name, entity_id in bindings.items():
            helper = self._helpers.get(entity_id)
            if helper is None:
                errors.append(f"Helper {entity_id} missing for {name}")
                continue
            if helper.domain not in self.SUPPORTED_DOMAINS:
                errors.append(f"Helper {entity_id} unsupported domain {helper.domain}")
        return errors

    def ensure_helper(self, entity_id: str, domain: str, description: str) -> HelperEntity:
        helper = HelperEntity(entity_id=entity_id, domain=domain, description=description)
        self._helpers[entity_id] = helper
        return helper

    def list(self) -> List[HelperEntity]:
        return list(self._helpers.values())
