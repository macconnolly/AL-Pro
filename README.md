# AL Layer Manager Beta

Adaptive lighting integration delivering manual intent respect, environmental boosts, and scenario-driven automation parity with the legacy YAML suite.

## Features
- Zone modeling with asymmetric boundaries and helper registry validation.
- Manual override engine with start/extend/clear services.
- Environment manager layering foggy/cloudy/S.A.D. boosts with availability tracking.
- Mode state machine powering relax, focus, late-night, and guest flows.
- Bridge that emits canonical `layer_manager.insert_state`/`remove_layer` commands so upstream priority semantics remain intact.
- Analytics suite exposing counters, health scores, and diagnostics snapshots.

## Getting Started
1. Install dependencies via `poetry install --with dev`.
2. Generate fixtures with `poetry run python scripts/prepare_fixtures.py`.
3. Run `just test` to execute full unit and scenario suite.
4. Deploy both `custom_components/layer_manager` (upstream fork) and `custom_components/al_layer_manager` into Home Assistant to exercise the bridge end-to-end.

## Scenario Validation
Use `pytest -m scenario` to execute daily-life scenario tests reflecting the testing philosophy.
