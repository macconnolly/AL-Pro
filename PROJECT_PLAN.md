# Adaptive Lighting Pro Project Plan

## Vision and Quality Bar
Adaptive Lighting Pro replaces the legacy YAML package with a production-grade Home Assistant custom integration that keeps daily lighting effortless. We hold the experience to the standard of "would I want to live with this?"—manual intent always wins, automation never fights back, and the system recovers gracefully after every edge case. The Anthropic-level polish described in `AGENTS.md` guides every change.

## Current Architecture Snapshot
- **Event-driven runtime (`custom_components/adaptive_lighting_pro/core/`)** orchestrates zones, timers, observers, and executors. Manual detection, environmental adaptation, Sonos sunrise anchoring, nightly sweeps, and watchdog resets are already implemented here.
- **Feature packages (`features/`)** encapsulate manual detection, environmental logic, mode enforcement, scene coordination, and Sonos parsing. Each module posts `alp_*` events that the runtime consumes.
- **Robustness layer (`robustness/`)** provides retry, jittered backoff, and sliding-window rate limiting enforced before executor service calls. Health monitoring and analytics summarize runtime behavior for operators.
- **Home Assistant platforms** expose switches, sensors, numbers, selects, buttons, and binary sensors that only rely on public runtime APIs per repository guardrails.
- **Test suite (`tests/`)** covers config validation, Sonos parsing, manual timers, rate limiting, watchdog sweeps, Zen32 inputs, and service orchestration through scenario-driven pytest cases.

## Current Focus Areas
1. **Lifestyle Extensions** – Harden the new Sonos skip-next workflow, sunrise anchor sensor, and upcoming-alarm reminders while identifying adjacent lifestyle hooks worth elevating.
2. **Dashboard Polish** – Continue refining scenario validation docs and Lovelace guidance so Implementation_2 users can drop in dashboards without bespoke YAML.
3. **Feedback Loop** – Monitor manual sensor usage, analytics, and watchdog metrics to identify future enhancements beyond the legacy parity scope, including the new presence/holiday automations.

## Latest Audit
- **Service Coverage** – Added `tests/test_service_api_parity.py` to prove that force sync, enable/disable/reset zone, and backup/restore services (used heavily by `implementation_2.yaml`) behave as expected.
- **Scene Parity** – Extended `tests/test_adjust_and_scenes.py` to validate Full Bright, No Spots, Evening Comfort, and Ultra Dim presets including manual timers, offsets, and group toggles.
- **Documentation** – Published `YAML_MIGRATION_COMPLETE.md` and `KNOWN_ISSUES.md` so migration status and deferred enhancements remain visible to future contributors.
- **Sunrise Visibility** – Introduced `sensor.alp_sonos_anchor`, runtime anchor snapshots, reminder automations, and accompanying regression tests in `tests/test_sonos_parser.py`.
- **Presence & Holiday UX** – Reintroduced advanced away/return, seasonal scheduling, and holiday scene logic in `implementation_2.yaml` using only public services.
- **Observability Parity** – Restored the legacy status/realtime sensors and unified `adaptive_lighting_calculation_complete` event emission across sync, adjust, and environmental flows, with coverage in `tests/test_status_sensors.py`. The runtime now caches the latest calculation payload so entities remain accurate even if Home Assistant misses the live bus event.
- **Configuration Paths** – Added configuration.yaml import support that normalizes nested sensor/controller mappings before invoking the config flow, ensuring UI and YAML setups share the same validation, telemetry, and parity guarantees.

## Implementation_2 Companion Package
The delivered `implementation_2.yaml` leverages the integration’s public APIs without recreating business logic. Highlights include:
- Scene scripts for Full Bright, No Track Lights, Evening Comfort, and Ultra Dim, each restoring adaptive mode before calling `select_scene`.
- Manual adjustment wrappers that read step numbers, global pause toggles, force-sync/reset helpers, and zone enable/disable scripts aligned with runtime zone identifiers.
- Lifestyle automations for startup restoration, movie-mode bridging, sunset boost nudges, manual decay reversion, nightly backups, rate-limit notifications, Sonos skip toggle synchronization, and global pause recovery.
- Template button chaining backup + sync for dashboards while keeping the YAML footprint minimal.

Details live in `docs/IMPLEMENTATION_2_PLAN.md`, which maps every retained YAML feature to its new home.

## Next Steps
- Capture household feedback on the new Implementation_2 automations (movie bridge thresholds, sunset nudge levels, skip toggle cadence) and tune defaults accordingly.
- Observe holiday/presence automation behaviour through the season and calibrate timing offsets or group membership as needed.
- Expand Lovelace examples that pair analytics sensors with the new scripts and automations (README stack published; collect feedback for graphing/alert refinements).
