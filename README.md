# AL Layer Manager Beta

Adaptive lighting integration delivering manual intent respect, environmental boosts, and scenario-driven automation parity with the legacy YAML suite.

## Features
- Zone modeling with asymmetric boundaries and helper registry validation.
- Manual override engine with start/extend/clear services.
- Environment manager layering foggy/cloudy/S.A.D. boosts with availability tracking.
- Mode state machine powering relax, focus, late-night, and guest flows.
- Bridge that emits canonical `layer_manager.insert_state`/`remove_layer` commands so upstream priority semantics remain intact.
- Analytics suite exposing counters, health scores, and diagnostics snapshots.

## Responsibility Model
- **`custom_components/layer_manager`** – Canonical layer execution engine that owns entity state layering, diagnostics, and persistence. Our fork now exposes `register_external_summary` so downstream components can surface telemetry alongside native layers.
- **`custom_components/al_layer_manager`** – Adaptive logic runtime orchestrating manual intent, environment boosts, and mode priorities. The runtime wires calculations into Home Assistant services, exposes a hardened service contract, and feeds telemetry back to the layer manager coordinator via the bridge.
- **`implementation_2.yaml`** – Scenario-focused automations and scripts that call the integration services (e.g., `al_layer_manager.start_manual_override`, `al_layer_manager.set_mode`) while leaning on upstream `layer_manager` for deterministic actuation.

## Getting Started
1. Install dependencies via `poetry install --with dev`.
2. Generate fixtures with `poetry run python scripts/prepare_fixtures.py`.
3. Run `just test` to execute full unit and scenario suite.
4. Deploy both `custom_components/layer_manager` (upstream fork) and `custom_components/al_layer_manager` into Home Assistant to exercise the bridge end-to-end.

## Scenario Validation
Use `pytest -m scenario` to execute daily-life scenario tests reflecting the testing philosophy.

Refer to [`docs/validation_report.md`](docs/validation_report.md) for the latest verification notes tying the automated test suite back to the integration parity plan.
