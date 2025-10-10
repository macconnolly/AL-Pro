# HA Layer Manager Integration Parity & Innovation Plan

## Vision & North Star
- Deliver a fork of `ha-layer-manager` that reproduces the 60+ behaviors encoded in the current YAML automations while adding scenario-aware enhancements that make the lighting system invisible-in-use, fast, and trustworthy every day.【F:v7.yaml†L11-L548】【F:v7.yaml†L630-L1759】
- Treat the integration as the single source of truth for adaptive lighting, removing YAML debt and replacing it with maintainable coordinators, services, and sensors that respect manual intent and environmental context.【F:v7.yaml†L630-L1150】【F:v7.yaml†L1200-L1759】
- Layer in new quality-of-life features—context memory, vacation safeguards, and health diagnostics—so the upgraded system is strictly better than the status quo, not just a port.【F:v7.yaml†L490-L628】【F:v7.yaml†L1486-L1566】

## Feature Inventory & Targets
| Category | YAML Behaviors We Must Reproduce | Notes |
| --- | --- | --- |
| Zone scaffolding | Zone defaults, timers, locks, timeout multipliers, helper bindings, and per-light overrides defined via `homeassistant.customize` blocks.【F:v7.yaml†L11-L192】 | Requires persisted models, validation, and UI selectors.
| Helper entities | 16+ helpers spanning `input_number`, `input_boolean`, `input_select`, `timer`, `counter`, and `history_stats` for offsets, boosts, analytics, health, and scene state.【F:v7.yaml†L194-L548】 | Fork must either manage or integrate with these helpers.
| Script executors | Manual override start/clear, sync parameters, environment boosts, user adjustments, reset/mode application, analytics logging.【F:v7.yaml†L630-L1150】 | Translate to coordinator managers + services.
| Automations | Startup init, adaptive sync loops, manual detection, weather/lux boosts, sunset handling, scheduled resets, nightly maintenance.【F:v7.yaml†L1200-L1759】 | Replace with dispatcher/listener logic.
| Analytics & health | Counters, scores, durations, watchdog timers to ensure lights respond quickly and reliably.【F:v7.yaml†L490-L628】【F:v7.yaml†L1688-L1759】 | Expand into dedicated sensors + diagnostics.

### Adjacent Innovation Goals
- **Context Memory:** Remember last manual preference per room for 24h and bias adaptive calculations to honor it on the next day when the same trigger fires (e.g., office brightness preference for cloudy mornings).【F:v7.yaml†L660-L758】
- **Presence-aware boost:** Fuse occupancy sensors with weather/lux data so boosts only fire when humans need them, eliminating waste while preserving comfort.【F:v7.yaml†L960-L1150】
- **Vacation & sleep protection:** Add global “away”, “guest”, and “sleep sanctuary” modes that suppress automation churn while guaranteeing soft ramp-ups when sleep sensors clear.【F:v7.yaml†L1486-L1566】
- **Insightful diagnostics:** Provide dashboards and logbook annotations summarizing override frequency, reaction latency, and sensor outages for trust-building visibility.【F:v7.yaml†L490-L610】

## Work Breakdown Structure (WBS)
The matrix below expands every required activity into actionable, testable work items. Each task is uniquely identified so it can be mirrored in `TASK_TRACKER.md`, scheduled, and verified against scenario expectations.

### Phase 0 – Foundation & Discovery
| ID | Task | Implementation Steps | Deliverables | Validation |
| --- | --- | --- | --- | --- |
| P0.A | Upstream fork & CI hardening | Create `al-layer-manager` fork, enable branch protections, configure GitHub Actions for `lint`, `pytest`, `mypy`, `ruff`, `hassfest`, and `hacs` jobs mirroring HA core standards.【F:v7.yaml†L11-L192】 | Forked repo with CI badge, Actions workflow yaml, branch protection policy doc. | All CI jobs green on seed commit; failure gates enforced on PRs. |
| P0.B | Devcontainer & tooling parity | Add `.devcontainer` or `justfile` + Poetry environment replicating HA integration dependencies (`homeassistant`, `pytest-homeassistant-custom-component`, `ruff`, `mypy`). Document bootstrap script and VS Code tasks.【F:v7.yaml†L194-L410】 | Devcontainer definition, `poetry.lock`, setup docs. | Local `just test` runs full suite without manual setup. |
| P0.C | Baseline data capture | Import `implementation_1.yaml` + `v7.yaml` fixtures, snapshot helper defaults, record zone state baselines for comparison harness.【F:implementation_1.yaml†L1-L200】【F:v7.yaml†L11-L548】 | `/tests/fixtures/` with YAML + JSON snapshots, README explaining usage. | Pytest fixture loads produce identical dictionaries to source YAML. |
| P0.D | Architecture blueprint | Draft ADRs and diagrams for managers (zone, sync, manual, environment, mode), event bus topics replacing YAML automations, and storage schema versioning.【F:v7.yaml†L630-L1150】【F:v7.yaml†L1200-L1759】 | `docs/architecture/` diagrams + ADR-000..002. | Architecture review checklist signed off; diagrams referenced in README. |
| P0.E | Scenario-driven test charter | Encode testing philosophy into a charter linking personas to concrete tests (foggy morning, cloudy day, sunset boost, movie night, manual stickiness, wall button). Include acceptance metrics (<100 ms response, >80 % coverage).【F:docs/ha_layer_manager_integration_plan.md†L51-L63】 | `docs/testing_charter.md` with scenario tables and expected sensor/service states. | Charter reviewed; pytest markers stubbed for each scenario. |
| P0.F | Dependency audit & risk log | Inventory upstream libraries (adaptive_lighting, weather providers, Sonos, occupancy sensors) and capture risk mitigations for unavailable dependencies.【F:v7.yaml†L490-L628】【F:v7.yaml†L960-L1150】 | Dependency matrix, risk register updates. | Risks cross-linked to mitigation tasks in later phases. |

### Phase 1 – Zone & Helper Model Foundations
| ID | Task | Implementation Steps | Deliverables | Validation |
| --- | --- | --- | --- | --- |
| P1.A | `ZoneModel` + schema | Implement dataclasses for `ZoneModel`, `ManualBehaviorProfile`, `EnvironmentProfile`; include timers, locks, helper bindings, adaptive providers, manual decay curves.【F:v7.yaml†L11-L192】【F:v7.yaml†L700-L812】 | `zone_model.py`, schema JSON, unit tests. | Serialization/deserialization round-trip unit tests; schema migration 1→2 validated. |
| P1.B | Storage + migrations | Extend Layer Manager storage with versioned migrations, persist zone + helper metadata, build migration CLI script.【F:v7.yaml†L194-L410】 | `storage.py`, migration docs, CLI. | Migration test moves fixture data without loss; HA recorder state matches expected. |
| P1.C | Helper registry ingestion | Auto-discover timers, input_numbers, selectors from YAML helpers, present mapping UI, allow integration-managed creation when missing.【F:v7.yaml†L194-L548】 | Helper registry service + config entries; onboarding docs. | Config flow smoke test ensures all helpers recognized; missing helper path creates entity automatically. |
| P1.D | Config flow UX | Add multi-step config flow: zone selection, helper binding, default scenes, manual behavior profiles, preview summary with validation and conflict resolution.【F:v7.yaml†L92-L192】【F:v7.yaml†L410-L489】 | `config_flow.py` updates, localized strings, UI screenshots. | UI tests confirm validation messages for invalid combos; manual QA following wizard without YAML context. |
| P1.E | Adaptive defaults import | Map per-entity overrides, kelvin/brightness ranges, transition durations from YAML customization into integration settings; support asymmetric min/max boundaries.【F:v7.yaml†L92-L192】【F:v7.yaml†L736-L818】 | Default profile JSON, importer script, docs. | Golden master tests compare imported defaults to YAML expected outputs. |
| P1.F | Legacy helper parity matrix | Produce matrix linking each YAML helper to new integration entity/service, flag items needing Implementation_2 coverage (e.g., Sonos wake, wake ramp booleans).【F:implementation_1.yaml†L1-L160】【F:v7.yaml†L520-L628】 | Matrix doc, backlog cross-links. | Reviewed by stakeholders; gaps pushed into Phase 6 tasks. |

### Phase 2 – Manual Intent, Sync, & Physical Interfaces
| ID | Task | Implementation Steps | Deliverables | Validation |
| --- | --- | --- | --- | --- |
| P2.A | Sync manager core | Port `al_exec_sync_parameters` logic into Python coordinator, implement asymmetric clamp calculations, environmental offsets, manual decay, rate limiting (<100 ms).【F:v7.yaml†L630-L758】【F:v7.yaml†L960-L1150】 | `sync_manager.py`, unit tests, profiling notes. | Unit tests cover clamp math, manual + environment blend; perf benchmark script <100 ms. |
| P2.B | Manual override detection | Subscribe to light, switch, scene state changes; derive context (wall button vs automation), start manual timers with dynamic durations from helper inputs.【F:v7.yaml†L756-L942】【F:implementation_1.yaml†L200-L360】 | `manual_manager.py`, event listeners, timer scheduler. | Integration tests verifying manual change sticks for configured timeout. |
| P2.C | Manual timer + decay services | Implement services `al.start_manual_override`, `al.extend_manual_override`, `al.clear_manual_override`; publish sensors for timer state, clamp ceilings; include analytics counters.【F:v7.yaml†L490-L610】【F:v7.yaml†L818-L958】 | `services.yaml`, service schemas, sensor entities, docs. | Service schema tests; scenario tests ensure manual boost decays gracefully. |
| P2.D | Adaptive Lighting bridge | Add toggles to use external `adaptive_lighting` (call `change_switch_settings`) or native provider; ensure boundaries remain asymmetric when bridging.【F:v7.yaml†L700-L812】 | Bridge module, config options, docs. | Dual-mode tests (external vs native) show identical outputs for sample fixtures. |
| P2.E | Physical interface mapper | Implement event handler for Zen32 + other button integrations (e.g., ZHA, MQTT) mapping to mode toggles, manual services, scenes with zero-delay dispatch.【F:v7.yaml†L1320-L1430】 | `physical_input.py`, automation blueprint, docs. | Simulated button press test ensures <100 ms response and sticky manual state. |
| P2.F | Scene + Sonos sync | Recreate YAML `scene.apply`, Sonos wake coordination, and ensure manual scene activations integrate with override timers and Implementation_2 Sonos routines.【F:implementation_1.yaml†L360-L520】【F:v7.yaml†L1310-L1430】 | Scene service wrappers, Sonos handshake spec. | Scenario test: Sonos wake triggers warm ramp + audio without fighting lighting overrides. |

### Phase 3 – Environmental & Mode Intelligence
| ID | Task | Implementation Steps | Deliverables | Validation |
| --- | --- | --- | --- | --- |
| P3.A | Sensor ingestion layer | Build environment aggregator for weather, forecast, lux, occupancy, circadian context; include sensor availability health tracking.【F:v7.yaml†L960-L1150】 | `environment_manager.py`, sensor registry docs. | Unit tests simulate sensor dropouts with graceful degradation. |
| P3.B | Boost strategy engine | Encode boost profiles (foggy, cloudy, S.A.D., circadian) with additive offsets, per-zone caps, presence gating, and manual disable flags.【F:v7.yaml†L960-L1150】【F:v7.yaml†L1486-L1566】 | Strategy config, YAML-to-python mapping, docs. | Scenario tests verifying boost triggers and clears correctly when weather changes. |
| P3.C | Sun + wake flows | Implement sun elevation listeners, seasonal thresholds, sunrise alarm coordination, late-night dimming guardrails.【F:v7.yaml†L1200-L1310】【F:v7.yaml†L1486-L1566】 | `sun_manager.py`, config options. | Simulation tests for seasonal sunrise vs manual alarms; ensures manual overrides respected. |
| P3.D | Mode state machine | Rebuild focus/relax/movie/guest/cleaning/late-night/vacation modes with priority stacking, scene snapshots, manual persistence, wearable/calendar hooks for future intents.【F:v7.yaml†L1152-L1484】【F:implementation_1.yaml†L520-L760】 | `mode_manager.py`, service docs, integration tests. | Scenario tests verifying mode transitions and manual adjustments remain sticky. |
| P3.E | User adjustment services | Provide `al.bump_brighter/dimmer/warmer/cooler` with delta config, update totals, surface to analytics; ensure compatibility with manual timers.【F:implementation_1.yaml†L220-L320】【F:v7.yaml†L700-L812】 | Services + UI toggles, docs. | Unit tests ensure increments accumulate and decay per rules. |
| P3.F | Presence + calendar gating | Integrate occupancy, calendar, and guest mode sensors so boosts/modes only run when people present or scheduled; include remote work vs travel heuristics.【F:v7.yaml†L960-L1150】【F:v7.yaml†L1486-L1566】 | Presence adapter module, config docs. | Scenario tests with occupancy false ensure no boost triggered. |

### Phase 4 – Analytics, Health, and Maintenance
| ID | Task | Implementation Steps | Deliverables | Validation |
| --- | --- | --- | --- | --- |
| P4.A | Observability entities | Create sensors/binary sensors for override status, boost state, manual timers, response latency, health score components; integrate with HA statistics.【F:v7.yaml†L490-L628】【F:v7.yaml†L1688-L1759】 | Sensor platform, diagnostics endpoints. | Unit tests for sensor value derivation; diagnostics download includes expected keys. |
| P4.B | Analytics pipeline | Persist counters (overrides, boosts, failures), durations, latencies; schedule weekly summary notifications and dashboards.【F:v7.yaml†L490-L628】【F:v7.yaml†L1688-L1759】 | Analytics module, long-term statistics config, summary script. | Scenario tests ensure counters increment/decrement; weekly summary stub validated. |
| P4.C | Nightly + startup routines | Implement startup reconciliation (sync timers, locks), nightly reset jobs, stale override cleanup, sensor re-syncs, error notifications.【F:v7.yaml†L1700-L1759】 | Scheduler module, docs. | Integration tests verifying nightly routine resets counters and respects manual sanctuary mode. |
| P4.D | Health scoring engine | Port health score algorithm, include penalties for missed syncs, stale sensors, override stuck; expose aggregated + per-zone metrics.【F:v7.yaml†L520-L628】 | Health engine module, docs, sensors. | Unit tests verifying scoring outputs for sample data; scenario tests for degraded sensors. |
| P4.E | Logging & diagnostics UX | Implement structured logging categories, debug trace toggles, logbook notes, failure alerts; provide diagnostics download bundling state snapshots.【F:v7.yaml†L630-L1150】 | Logging config, docs, support guide. | Manual QA ensures toggling debug changes log verbosity; diagnostics export passes hassfest review. |

### Phase 5 – UX, Documentation, Release Readiness
| ID | Task | Implementation Steps | Deliverables | Validation |
| --- | --- | --- | --- | --- |
| P5.A | Guided onboarding & dashboards | Build onboarding wizard, inline help, Lovelace dashboard blueprint summarizing zones, modes, overrides, boosts.【F:v7.yaml†L194-L548】【F:v7.yaml†L1486-L1566】 | UI components, blueprint YAML, screenshots. | User testing walkthrough ensures zero YAML knowledge required; blueprint renders sensors. |
| P5.B | Migration & troubleshooting docs | Author migration runbook from YAML → integration, scenario playbooks, troubleshooting matrix, FAQ, glossary referencing helper names.【F:v7.yaml†L11-L1759】 | `/docs/` updates, printable checklists. | Docs peer reviewed; all helper references cross-linked. |
| P5.C | Quality gates & performance | Enforce >80 % overall, >90 % managers coverage, <100 ms manual response, load testing with concurrent overrides + boosts.【F:docs/ha_layer_manager_integration_plan.md†L104-L107】 | Coverage reports, performance scripts, CI gate config. | CI fails if thresholds unmet; load test log attached to release candidate. |
| P5.D | Release + community prep | Prepare HACS metadata, versioning, release workflows, announcement copy, preview media; ensure rollback instructions documented.【F:v7.yaml†L1700-L1759】 | `hacs.json`, GitHub workflow, blog draft. | HACS validation passes; release dry-run completes. |
| P5.E | Support playbooks | Create support SOP for incident response, sensor outage triage, manual override escalation, with checklists for 2 AM troubleshooting.【F:v7.yaml†L490-L610】 | Support docs, runbooks. | Tabletop exercise documented; actions validated against scenario charter. |

### Phase 6 – Legacy Interop & Implementation_2 Enhancements
| ID | Task | Implementation Steps | Deliverables | Validation |
| --- | --- | --- | --- | --- |
| P6.A | Feature parity audit | Build matrix comparing `implementation_1.yaml` automations/scripts/scenes to integration services; flag coverage gaps requiring Implementation_2 or integration updates.【F:implementation_1.yaml†L1-L520】 | Gap analysis doc, tracker updates. | Review ensures every YAML block mapped to task ID. |
| P6.B | Implementation_2 YAML authoring | Design `implementation_2.yaml` to orchestrate Sonos wake routine, adaptive scenes, and external automations that complement new services without duplication; include comments linking to integration APIs.【F:implementation_1.yaml†L360-L520】【F:v7.yaml†L1310-L1430】 | Draft YAML file, README describing use. | YAML lint clean; dry-run in HA test instance verifies no conflicts. |
| P6.C | Service contract alignment | Define service contracts between integration and Implementation_2 automations (e.g., `al.trigger_morning_scene`, `al.request_sonos_wake`), document payloads, add schema validation.【F:implementation_1.yaml†L200-L520】【F:v7.yaml†L1310-L1430】 | Service contract doc, schema tests. | Integration tests ensure YAML automation calls succeed and respect manual boundaries. |
| P6.D | Upstream contribution strategy | Identify improvements suitable for upstream `ha-layer-manager` PRs vs fork-only changes; prepare contribution plan, maintain patch queue. | Contribution roadmap doc. | Approved plan; upstream issues filed for shared fixes. |
| P6.E | Continuous improvement backlog | Capture adjacent innovation ideas (context memory, wellness insights, ML lux forecasting) with experiment charters and success metrics.【F:v7.yaml†L660-L758】【F:v7.yaml†L960-L1150】 | Backlog entries with hypotheses + metrics. | Quarterly review ensures experiments prioritized post-launch. |

Each task links directly to daily-life scenarios and ensures upstream, downstream, and concurrent services remain coordinated so the integration feels delightful in real use.

## Timeline & Dependencies
- **Phase 0-1 (Weeks 1-3):** Foundation, zone modeling, helper binding.
- **Phase 2 (Weeks 4-6):** Manual override + physical controls; unlocks trustworthy daily operation.
- **Phase 3 (Weeks 7-9):** Environmental intelligence and modes; delivers scenario excellence.
- **Phase 4 (Weeks 10-12):** Observability, analytics, maintenance; ensures reliability and insight.
- **Phase 5 (Weeks 13-14):** UX polish, testing, release.

## Testing & Validation Strategy
- Follow the "test like you live here" charter by encoding each life scenario as an integration test case, mirroring the expectations documented in the testing philosophy.
- Use synthetic weather/lux data to validate boosts, with manual overrides verifying no fighting between automation and human intent.
- Instrument response latency metrics and assert they stay <100ms in unit and integration tests.
- Include resilience tests where sensors go offline or misreport, ensuring graceful degradation and notifications.

## Risk Register & Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Event feedback loops causing oscillations | High | Centralize clamps/timers in managers, debounce updates, include regression tests mirroring YAML safeguards.【F:v7.yaml†L700-L900】 |
| Helper divergence between YAML and integration | Medium | Provide migration wizard, continuous validation, and fallback manual selectors.【F:v7.yaml†L194-L548】 |
| Sensor outages leading to bad lighting decisions | High | Implement fallback defaults, degrade gracefully, and notify via diagnostics sensors.【F:v7.yaml†L490-L628】 |
| Manual override mistrust | High | Guarantee timers respect human actions and publish state in sensors/logbook to reinforce trust.【F:v7.yaml†L818-L942】 |

## Definition of Done Alignment
- Every DOD bullet (Feature, Quality, Life) maps to at least one task above, ensuring daily-life delight is encoded in the backlog.
- Completion requires full test coverage, verified response times, zero boundary collapses, and documentation that future-you can trust.
