"""Fixture preparation utilities for tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)


def main() -> None:
    sources = {
        "implementation_1.json": REPO_ROOT / "implementation_1.yaml",
        "v7.json": REPO_ROOT / "v7.yaml",
    }
    for target_name, source_path in sources.items():
        if not source_path.exists():
            raise SystemExit(f"Missing source fixture: {source_path}")
        data = _load_yaml(source_path)
        _write_json(FIXTURE_DIR / target_name, data)

    readme_path = FIXTURE_DIR / "README.md"
    readme_path.write_text(
        """# Fixture Regeneration\n\n"
        "Fixtures are generated from the canonical YAML implementations to enable golden\n"
        "master comparisons. Run `poetry run python scripts/prepare_fixtures.py` whenever\n"
        "the YAML sources change.\n"
        """,
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
