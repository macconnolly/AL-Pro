# Component Responsibility Charter

## Layer Manager (Upstream Fork)
- Maintains canonical knowledge of layered light states and persists per-entity layer stacks.
- Exposes dispatcher-driven diagnostics (`LayerStatusSensor`) that now aggregate external summaries from the adaptive runtime via `register_external_summary`.
- Owns priority ordering, insert/remove semantics, and adaptive bindings so downstream integrations never bypass standard service contracts.

## AL Layer Manager Integration
- Hosts the adaptive engine (manual, environment, mode managers) and bridges results into `layer_manager` services through the `LayerManagerRuntime`.
- Registers public Home Assistant services (`start_manual_override`, `set_mode`, `sync_zone`, etc.) with rigorous payload validation and telemetry hand-off back into the upstream coordinator.
- Subscribes to helper-defined environment sensors (`helpers.environment_*`) ensuring foggy/cloudy/S.A.D. boosts stay in sync with real-time entities without custom YAML templates.

## Implementation_2 YAML Suite
- Contains scenario automation blueprints and scripts that call the integration services, combining them with non-lighting systems (Sonos wake, occupancy) while leaving actuation to the bridge.
- Demonstrates user-facing routines (wake, evening relax) that respect manual stickiness and mode lifecycles by leveraging the new services plus follow-up `sync_zone` calls.
- Acts as migration scaffolding: once parity is confirmed, helpers can be gradually retired in favor of integration-managed entities while Implementation_2 remains the orchestration layer for cross-domain logic.
