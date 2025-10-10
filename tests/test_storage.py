from __future__ import annotations

import json

from custom_components.al_layer_manager.storage import read_storage, serialize_zone, write_storage


def test_storage_round_trip(tmp_path, sample_zone) -> None:
    path = tmp_path / "storage.json"
    write_storage(path, [sample_zone])
    zones = read_storage(path)
    assert zones[0].zone_id == sample_zone.zone_id
    assert zones[0].manual.decay_rate == sample_zone.manual.decay_rate


def test_migration_adds_missing_fields(tmp_path, sample_zone) -> None:
    path = tmp_path / "storage.json"
    payload = serialize_zone(sample_zone)
    payload["storage_version"] = 1
    payload["manual"].pop("max_extra_brightness")
    payload.pop("asymmetric_floor", None)
    payload.pop("asymmetric_ceiling", None)
    data = {"storage_version": 1, "zones": [payload]}
    path.write_text(json.dumps(data), encoding="utf-8")
    zones = read_storage(path)
    assert zones[0].manual.max_extra_brightness == sample_zone.manual.max_extra_brightness
    assert zones[0].asymmetric_floor == sample_zone.asymmetric_floor
