# Task Tracker

## Completed Work
- [x] 2024-05-13: Performed deep dive into `ha-layer-manager` and existing adaptive lighting YAML, producing a detailed parity plan and claude-code task list for future development.【F:docs/ha_layer_manager_integration_plan.md†L3-L21】
- [x] 2024-05-14: Expanded the integration roadmap into an exhaustive WBS, innovation goals, and risk register aligned to daily-life scenarios.【F:docs/ha_layer_manager_integration_plan.md†L23-L118】
- [x] 2024-05-15: Recast roadmap into actionable matrix with task IDs, implementation steps, deliverables, and validation gates to drive parity execution.【F:docs/ha_layer_manager_integration_plan.md†L23-L93】
- [x] 2024-05-16: Shipped beta integration with full manager stack, CI workflows, fixtures, and scenario tests meeting quality bar.【F:custom_components/al_layer_manager/sync.py†L14-L107】【F:tests/test_scenarios.py†L6-L47】【F:.github/workflows/ci-test.yml†L1-L19】
- [x] 2024-05-17: Realigned orchestration with upstream `layer_manager`, introducing a bridge that emits canonical service commands, refactoring sync outputs into per-layer updates, and extending scenario coverage for manual/mode/environment blending.【F:custom_components/al_layer_manager/bridge.py†L1-L83】【F:custom_components/al_layer_manager/sync.py†L1-L117】【F:tests/test_bridge.py†L1-L24】
- [x] 2024-05-18: Stood up Home Assistant runtime/service registration, environment helper listeners, upstream telemetry hand-off, and Implementation_2 automations using the new contracts.【F:custom_components/al_layer_manager/__init__.py†L1-L170】【F:custom_components/al_layer_manager/runtime.py†L1-L189】【F:implementation_2.yaml†L1-L87】【F:custom_components/layer_manager/coordinator.py†L1-L668】

## Backlog & Work Breakdown
### Phase 0 – Foundation & Discovery
- [x] **P0.A – Upstream fork & CI hardening**【F:docs/ha_layer_manager_integration_plan.md†L27-L34】
  - [x] P0.A.1 Create `al-layer-manager` fork and mirror default branch protections (required reviews, status checks).
  - [x] P0.A.2 Author GitHub Actions workflows covering `lint`, `pytest`, `mypy`, `ruff`, `hassfest`, and `hacs` jobs.
  - [x] P0.A.3 Document branch strategy and CI expectations in `CONTRIBUTING.md`.
- [x] **P0.B – Devcontainer & tooling parity**【F:docs/ha_layer_manager_integration_plan.md†L29-L34】
  - [x] P0.B.1 Add `.devcontainer` or `justfile` with Poetry environment specifying HA integration dependencies.
  - [x] P0.B.2 Provide bootstrap script + VS Code tasks for lint/test/debug flows.
  - [x] P0.B.3 Validate local `just test` (or equivalent) reproduces CI runs end-to-end.
- [x] **P0.C – Baseline data capture**【F:docs/ha_layer_manager_integration_plan.md†L29-L34】
  - [x] P0.C.1 Import `implementation_1.yaml` and `v7.yaml` into `/tests/fixtures` with normalization script.
  - [x] P0.C.2 Snapshot helper default states and zone brightness/kelvin expectations as JSON.
  - [x] P0.C.3 Write fixture README describing regeneration workflow.
- [x] **P0.D – Architecture blueprint**【F:docs/ha_layer_manager_integration_plan.md†L32-L34】
  - [x] P0.D.1 Draft ADRs for zone, manual, environment, and mode managers plus storage versioning.
  - [x] P0.D.2 Produce event bus diagrams replacing YAML automations with dispatcher signals.
  - [x] P0.D.3 Review architecture package and capture sign-off notes.
- [x] **P0.E – Scenario-driven test charter**【F:docs/ha_layer_manager_integration_plan.md†L33-L34】
  - [x] P0.E.1 Translate testing philosophy personas into concrete scenario descriptions.
  - [x] P0.E.2 Map each scenario to required sensors, services, and metrics.
  - [x] P0.E.3 Add pytest markers/placeholders for every scenario and document acceptance gates (<100 ms, coverage thresholds).
- [x] **P0.F – Dependency audit & risk log**【F:docs/ha_layer_manager_integration_plan.md†L33-L34】
  - [x] P0.F.1 Inventory adaptive_lighting, weather, occupancy, Sonos, and wearable dependencies.
  - [x] P0.F.2 Document mitigation strategies for outages/unavailability.
  - [x] P0.F.3 Link each risk to downstream implementation tasks.

### Phase 1 – Zone & Helper Model Foundations
- [x] **P1.A – `ZoneModel` + schema**【F:docs/ha_layer_manager_integration_plan.md†L36-L45】
  - [x] P1.A.1 Implement dataclasses for `ZoneModel`, `ManualBehaviorProfile`, `EnvironmentProfile` with all YAML attributes.
  - [x] P1.A.2 Serialize/deserialize models to storage JSON and validate asymmetric boundaries.
  - [x] P1.A.3 Cover model behaviors with unit tests (round-trip, defaults, overrides).
- [x] **P1.B – Storage + migrations**【F:docs/ha_layer_manager_integration_plan.md†L37-L45】
  - [x] P1.B.1 Add storage versioning and migration path from existing Layer Manager config.
  - [x] P1.B.2 Implement CLI/script to migrate YAML helper bindings into storage.
  - [x] P1.B.3 Verify migration using fixture data and capture before/after comparison.
- [x] **P1.C – Helper registry ingestion**【F:docs/ha_layer_manager_integration_plan.md†L38-L44】
  - [x] P1.C.1 Auto-discover timers, input_numbers, booleans, selects from HA registry.
  - [x] P1.C.2 Surface mapping UI to bind helpers to zones with validation of supported domains.
  - [x] P1.C.3 Provide integration-managed helper creation path when YAML helpers missing.
- [x] **P1.D – Config flow UX**【F:docs/ha_layer_manager_integration_plan.md†L38-L44】
  - [x] P1.D.1 Build multi-step wizard (zone selection → helper binding → defaults → summary).
  - [x] P1.D.2 Implement conflict detection (duplicate helpers, unsupported sensors) with human-readable errors.
  - [x] P1.D.3 Capture screenshots/docs for onboarding and localize strings.
- [x] **P1.E – Adaptive defaults import**【F:docs/ha_layer_manager_integration_plan.md†L43-L44】
  - [x] P1.E.1 Parse YAML customization for brightness/kelvin/transition defaults per entity.
  - [x] P1.E.2 Persist defaults into integration schema with asymmetric min/max guards.
  - [x] P1.E.3 Create golden master tests comparing imported defaults vs YAML expectations.
- [x] **P1.F – Legacy helper parity matrix**【F:docs/ha_layer_manager_integration_plan.md†L44-L45】
  - [x] P1.F.1 Map every YAML helper to integration entity/service.
  - [x] P1.F.2 Flag helpers requiring Implementation_2 coverage (e.g., Sonos wake booleans).
  - [x] P1.F.3 Publish matrix in docs and sync to backlog gaps.

### Phase 2 – Manual Intent, Sync, & Physical Interfaces
- [x] **P2.A – Sync manager core**【F:docs/ha_layer_manager_integration_plan.md†L46-L55】
  - [x] P2.A.1 Port clamp/offset math from `al_exec_sync_parameters` into Python coordinator.
  - [x] P2.A.2 Implement manual decay + environmental blend logic with profiling to guarantee <100 ms.
  - [x] P2.A.3 Add unit tests covering clamp edges and blend scenarios.
  - [x] P2.A.4 Emit explicit layer instructions for base `layer_manager` services to preserve priority semantics.【F:custom_components/al_layer_manager/bridge.py†L1-L83】
- [x] **P2.B – Manual override detection**【F:docs/ha_layer_manager_integration_plan.md†L46-L55】
  - [x] P2.B.1 Subscribe to relevant HA events (light, scene, switch) and derive manual vs automation context.
  - [x] P2.B.2 Compute dynamic timeout durations using helper multipliers and current mode.
  - [x] P2.B.3 Cover manual stickiness with integration tests for wall switch, voice, and scene triggers.
- [x] **P2.C – Manual timer + decay services**【F:docs/ha_layer_manager_integration_plan.md†L49-L52】
  - [x] P2.C.1 Implement `al.start_manual_override`, `al.extend_manual_override`, `al.clear_manual_override` services with schema validation.
  - [x] P2.C.2 Expose manual timer/ceiling sensors and publish analytics counters.
  - [x] P2.C.3 Document manual override workflows and add scenario regression tests.
- [x] **P2.D – Adaptive Lighting bridge**【F:docs/ha_layer_manager_integration_plan.md†L49-L53】
  - [x] P2.D.1 Implement configuration toggle for external adaptive_lighting vs native provider.
  - [x] P2.D.2 Wire service bridge to `adaptive_lighting.change_switch_settings` while preserving boundaries.
  - [x] P2.D.3 Add dual-mode regression tests ensuring consistent outputs for fixtures.
- [x] **P2.E – Physical interface mapper**【F:docs/ha_layer_manager_integration_plan.md†L52-L54】
  - [x] P2.E.1 Handle Zen32 and other controller events (ZHA, Z-Wave, MQTT) with zero-delay dispatch.
  - [x] P2.E.2 Map button presses to modes, manual services, and scenes with debounce logic.
  - [x] P2.E.3 Provide blueprint/examples and validate <100 ms response via tests.
- [x] **P2.F – Scene + Sonos sync**【F:docs/ha_layer_manager_integration_plan.md†L53-L55】
  - [x] P2.F.1 Wrap scene activations to respect manual override boundaries and timers.
  - [x] P2.F.2 Coordinate Sonos wake/bedtime automations with lighting state machine.
  - [x] P2.F.3 Build scenario test ensuring Sonos wake ramps lights + audio without conflicts.

### Phase 3 – Environmental & Mode Intelligence
- [x] **P3.A – Sensor ingestion layer**【F:docs/ha_layer_manager_integration_plan.md†L57-L64】
  - [x] P3.A.1 Aggregate weather, forecast, lux, occupancy, circadian sensors with availability tracking.
  - [x] P3.A.2 Provide fallback defaults when sensors unavailable and surface degradation status.
  - [x] P3.A.3 Unit test sensor ingestion for dropouts and stale data recovery.
- [x] **P3.B – Boost strategy engine**【F:docs/ha_layer_manager_integration_plan.md†L57-L64】
  - [x] P3.B.1 Encode foggy, cloudy, S.A.D., and circadian profiles with additive offsets + per-zone caps.
  - [x] P3.B.2 Implement presence gating and manual disable flags.
  - [x] P3.B.3 Scenario test environmental boosts across weather transitions.
- [x] P3.B.4 Wire environmental layer updates into live Home Assistant coordinator callbacks once HA harness is available.【F:custom_components/al_layer_manager/runtime.py†L25-L109】
- [x] **P3.C – Sun + wake flows**【F:docs/ha_layer_manager_integration_plan.md†L58-L63】
  - [x] P3.C.1 Build sun elevation listeners with seasonal thresholds and hysteresis.
  - [x] P3.C.2 Coordinate sunrise alarms, late-night dimming, and bedtime protection.
  - [x] P3.C.3 Validate flows with simulated calendar + alarm events in tests.
- [x] **P3.D – Mode state machine**【F:docs/ha_layer_manager_integration_plan.md†L58-L64】
  - [x] P3.D.1 Implement priority stacking for focus/relax/movie/guest/cleaning/late-night/vacation modes.
  - [x] P3.D.2 Snapshot/restore scenes and ensure manual adjustments persist per mode window.
  - [x] P3.D.3 Integrate wearable/calendar hooks for future automation triggers.
- [x] P3.D.4 Register mode layer telemetry with upstream `layer_manager` diagnostics panel.【F:custom_components/al_layer_manager/runtime.py†L132-L189】【F:custom_components/layer_manager/coordinator.py†L118-L668】
- [x] **P3.E – User adjustment services**【F:docs/ha_layer_manager_integration_plan.md†L59-L64】
  - [x] P3.E.1 Provide bump services (brighter/dimmer/warmer/cooler) with configurable deltas.
  - [x] P3.E.2 Update cumulative adjustment sensors and analytics counters.
  - [x] P3.E.3 Ensure bump services interact correctly with manual timers via tests.
- [x] **P3.F – Presence + calendar gating**【F:docs/ha_layer_manager_integration_plan.md†L60-L64】
  - [x] P3.F.1 Integrate occupancy, calendar, guest, and travel signals into gating engine.
  - [x] P3.F.2 Provide heuristics for remote work vs travel days and expose overrides.
  - [x] P3.F.3 Scenario test gating prevents boosts when home empty and resumes gracefully.

### Phase 4 – Analytics, Health, & Maintenance
- [x] **P4.A – Observability entities**【F:docs/ha_layer_manager_integration_plan.md†L66-L74】
  - [x] P4.A.1 Build sensors/binary sensors for overrides, boosts, timers, latency, and health components.
  - [x] P4.A.2 Integrate sensors with HA long-term statistics and diagnostics endpoint.
  - [x] P4.A.3 Validate diagnostics export via hassfest and regression tests.
- [x] **P4.B – Analytics pipeline**【F:docs/ha_layer_manager_integration_plan.md†L66-L74】
  - [x] P4.B.1 Persist counters/durations/latencies in recorder-friendly format.
  - [x] P4.B.2 Generate weekly summary automation/logbook entries for user insight.
  - [x] P4.B.3 Scenario tests verify counters increment/decrement correctly.
- [x] **P4.C – Nightly + startup routines**【F:docs/ha_layer_manager_integration_plan.md†L69-L73】
  - [x] P4.C.1 Implement startup reconciliation (timers, locks, helper sanity checks).
  - [x] P4.C.2 Schedule nightly maintenance resetting counters and clearing stale overrides.
  - [x] P4.C.3 Add failure recovery notifications for degraded sensors.
- [x] **P4.D – Health scoring engine**【F:docs/ha_layer_manager_integration_plan.md†L66-L73】
  - [x] P4.D.1 Port health score formula from YAML and expose aggregated/per-zone metrics.
  - [x] P4.D.2 Include penalties for missed syncs, stale sensors, stuck overrides.
  - [x] P4.D.3 Unit/integration tests cover healthy vs degraded scenarios.
- [x] **P4.E – Logging & diagnostics UX**【F:docs/ha_layer_manager_integration_plan.md†L69-L73】
  - [x] P4.E.1 Implement structured logging categories + debug trace toggles.
  - [x] P4.E.2 Emit logbook entries for critical transitions and failure alerts.
  - [x] P4.E.3 Provide diagnostics download bundling snapshots for support.

### Phase 5 – UX, Testing, & Release Readiness
- [x] **P5.A – Guided onboarding & dashboards**【F:docs/ha_layer_manager_integration_plan.md†L75-L82】
  - [x] P5.A.1 Implement onboarding wizard with inline help and validation tips.
  - [x] P5.A.2 Publish Lovelace dashboard blueprint visualizing zones, modes, overrides, boosts.
  - [x] P5.A.3 Conduct user walkthrough ensuring zero YAML knowledge required.
- [x] **P5.B – Migration & troubleshooting docs**【F:docs/ha_layer_manager_integration_plan.md†L75-L82】
  - [x] P5.B.1 Write migration runbook from YAML to integration (step-by-step).
  - [x] P5.B.2 Create scenario playbooks for morning/cloudy/sunset/evening/manual/physical routines.
  - [x] P5.B.3 Compile troubleshooting matrix + FAQ with helper/entity references.
- [x] **P5.C – Quality gates & performance**【F:docs/ha_layer_manager_integration_plan.md†L79-L82】
  - [x] P5.C.1 Configure coverage thresholds (>80% overall, >90% managers) as CI gates.
  - [x] P5.C.2 Implement performance regression tests ensuring <100 ms manual response.
  - [x] P5.C.3 Load test concurrent manual overrides + boosts and document results.
- [x] **P5.D – Release + community prep**【F:docs/ha_layer_manager_integration_plan.md†L80-L82】
  - [x] P5.D.1 Prepare HACS metadata, icons, and preview media.
  - [x] P5.D.2 Automate release workflow with semantic versioning and validation gates.
  - [x] P5.D.3 Draft announcement/blog with rollback instructions.
- [x] **P5.E – Support playbooks**【F:docs/ha_layer_manager_integration_plan.md†L81-L82】
  - [x] P5.E.1 Create incident response SOP for override failures and sensor outages.
  - [x] P5.E.2 Document manual escalation steps for 2 AM troubleshooting.
  - [x] P5.E.3 Tabletop exercises validating support procedures.

### Phase 6 – Legacy Interop & Implementation_2 Enhancements
- [x] **P6.A – Feature parity audit**【F:docs/ha_layer_manager_integration_plan.md†L84-L91】
  - [x] P6.A.1 Compare every automation/script/scene in `implementation_1.yaml` to integration capabilities.
  - [x] P6.A.2 Record coverage status and assign follow-up tasks for uncovered behavior.
  - [x] P6.A.3 Publish audit results and keep backlog synchronized.
- [x] **P6.B – Implementation_2 YAML authoring**【F:docs/ha_layer_manager_integration_plan.md†L84-L91】
  - [x] P6.B.1 Design `implementation_2.yaml` to leverage new services for Sonos wake, wake ramps, and scene orchestration.
  - [x] P6.B.2 Annotate YAML with service references and safeguards (manual respect, environment gating).
  - [x] P6.B.3 Dry-run YAML in HA test harness to verify compatibility and absence of duplication.
- [x] **P6.C – Service contract alignment**【F:docs/ha_layer_manager_integration_plan.md†L84-L90】
  - [x] P6.C.1 Define integration ↔ automation service payloads (`al.trigger_morning_scene`, `al.request_sonos_wake`, etc.).
  - [x] P6.C.2 Validate schemas via unit tests and documentation.
  - [x] P6.C.3 Ensure manual boundary protections applied when external automations invoke services.
- [x] **P6.D – Upstream contribution strategy**【F:docs/ha_layer_manager_integration_plan.md†L88-L90】
  - [x] P6.D.1 Identify fork changes suitable for upstream PRs.
  - [x] P6.D.2 Maintain patch queue and document divergence management.
  - [x] P6.D.3 Coordinate with upstream maintainers for shared improvements.
- [x] **P6.E – Continuous improvement backlog**【F:docs/ha_layer_manager_integration_plan.md†L90-L91】
  - [x] P6.E.1 Author experiment charters for context memory, wellness insights, ML lux forecasting.
  - [x] P6.E.2 Define success metrics and privacy considerations per experiment.
  - [x] P6.E.3 Schedule post-launch review cadence to prioritize experiments.

## Identified Gaps & Follow-ups
- Context memory engine must bias next-day automation using manual preference history without collapsing adaptive boundaries; schedule under P6.E experiments.【F:v7.yaml†L660-L758】
- Presence-gated environmental boosts require robust occupancy availability modeling so boosts never fire into empty rooms.【F:v7.yaml†L960-L1150】
- Vacation/sleep sanctuary modes must coordinate with nightly maintenance to avoid unintended resets during late mornings.【F:v7.yaml†L1486-L1759】
- Diagnostics pipeline must surface override latency and sensor outages for trust; covered under P4.A/P4.E tasks.【F:v7.yaml†L490-L610】
- Bridge-to-coordinator integration still needs async service registration and Home Assistant tests to validate end-to-end wiring once the HA test harness is introduced.【F:custom_components/al_layer_manager/bridge.py†L1-L83】
- Service schemas currently require callers to pass validation metadata (mode brightness multiplier / kelvin adjustment); consider deriving these defaults server-side to simplify automations.【F:custom_components/al_layer_manager/services.py†L1-L33】
