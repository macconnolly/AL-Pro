"""Storage helpers and migrations."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List

from .models import EnvironmentProfile, ManualBehaviorProfile, ModeProfile, ZoneModel

STORAGE_VERSION = 2


def _serialize_mode(mode: ModeProfile) -> Dict[str, object]:
    return {
        "brightness_multiplier": mode.brightness_multiplier,
        "kelvin_adjustment": mode.kelvin_adjustment,
        "transition_seconds": mode.transition_seconds,
    }


def _deserialize_mode(data: Dict[str, object]) -> ModeProfile:
    return ModeProfile(
        brightness_multiplier=float(data.get("brightness_multiplier", 1.0)),
        kelvin_adjustment=int(data.get("kelvin_adjustment", 0)),
        transition_seconds=int(data.get("transition_seconds", 2)),
    )


def serialize_zone(zone: ZoneModel) -> Dict[str, object]:
    payload = asdict(zone)
    payload.update(
        {
            "manual": asdict(zone.manual),
            "environment": asdict(zone.environment),
            "modes": {key: _serialize_mode(value) for key, value in zone.modes.items()},
            "storage_version": STORAGE_VERSION,
        }
    )
    return payload


def deserialize_zone(data: Dict[str, object]) -> ZoneModel:
    manual = ManualBehaviorProfile(**data["manual"])
    environment = EnvironmentProfile(**data["environment"])
    modes = {key: _deserialize_mode(value) for key, value in data.get("modes", {}).items()}
    return ZoneModel(
        zone_id=str(data["zone_id"]),
        name=str(data["name"]),
        lights=list(data["lights"]),
        helpers=dict(data["helpers"]),
        default_brightness=float(data["default_brightness"]),
        default_kelvin=int(data["default_kelvin"]),
        manual=manual,
        environment=environment,
        modes=modes,
        asymmetric_floor=float(data.get("asymmetric_floor", 0.05)),
        asymmetric_ceiling=float(data.get("asymmetric_ceiling", 1.0)),
    )


def write_storage(path: Path, zones: Iterable[ZoneModel]) -> None:
    payload = {
        "storage_version": STORAGE_VERSION,
        "zones": [serialize_zone(zone) for zone in zones],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_storage(path: Path) -> List[ZoneModel]:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("storage_version", 1)
    records = data.get("zones", [])
    if version < STORAGE_VERSION:
        records = [_migrate_zone(record, version) for record in records]
    return [deserialize_zone(record) for record in records]


def _migrate_zone(record: Dict[str, object], version: int) -> Dict[str, object]:
    migrated = dict(record)
    if version < 2:
        manual = migrated.get("manual", {})
        manual.setdefault("decay_rate", 0.1)
        manual.setdefault("max_extra_brightness", 0.4)
        migrated["manual"] = manual
        migrated.setdefault("asymmetric_floor", 0.05)
        migrated.setdefault("asymmetric_ceiling", 1.0)
    migrated["storage_version"] = STORAGE_VERSION
    return migrated
