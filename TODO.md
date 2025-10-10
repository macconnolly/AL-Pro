# TODO

## Implementation_1 Feature Parity Checklist

### Foundation & Zones
- [x] Zone definitions align with Adaptive Lighting switches and grouped lights
- [x] Manual control timers per zone with centralized timer math
- [x] Configurable zone multipliers and sunrise offsets
- [x] Global pause toggle equivalent to `input_boolean.al_globally_paused`
- [x] Support configuration.yaml import paths that normalize nested sensor/controller mappings before invoking the config flow

### Manual Adjustments & Modes
- [x] Manual detection with 500 ms debounce and smart timeout recovery
- [x] Manual adjustment services for brightness and color temperature deltas
- [x] Auto-switch to adaptive mode on manual interaction with previous-mode restoration
- [x] Expose configurable adjustment step entities mirroring YAML input_numbers
- [x] Mode select with parity coverage for adaptive, work, focus, relax, movie, late_night profiles

### Environmental & Sunset Logic
- [x] Lux, weather, and sun observers driving environmental boost events
- [x] Sunset fade cadence requesting sync near horizon transitions
- [x] Per-zone environmental boost enablement flags
- [x] Respect `sunset_boost_enabled` when applying boost payloads and expose corresponding runtime adjustments
- [x] Implement sunset boost as positive brightness support instead of dimming fallback, matching YAML intent

### Scenes & Intents
- [x] Scene executor presets for default, evening comfort, ultra dim, all lights, and no spots
- [x] Scene application guardrails enforcing adaptive mode and manual-safe behavior
- [x] Manual scenes trigger timer events for all_lights, no_spots, and evening_comfort with per-zone durations
- [x] Default scene selection clears manual states and resyncs baseline automation
- [x] Restore "Scene 1: All Lights" payload parity (high brightness, neutral warmth across zones) using integration presets while launching manual timers for each affected zone
- [x] Restore "Scene 2: No Spotlights" parity (accent lights off, +15% compensation elsewhere) with coordinated manual timers and direct light service calls where required
- [x] Restore "Scene 3: Evening Comfort" parity (pendant emphasis, -5% brightness, -500K warmth) including specific light groups and manual control hand-off
- [x] Expose configurable scene offset controls equivalent to YAML input_numbers
- [x] Parameterize scene brightness and warmth offsets via config flow/options instead of hard-coded presets
- [x] Provide scene reset affordance surfaced to Zen32 and services for parity with YAML "Scene 0" behavior

### Controllers & Physical Interfaces
- [x] Zen32 button mapping for scene cycling, manual adjustments, reset, and toggles
- [x] Surface manual adjustment state indicators similar to legacy input_booleans

### Sonos & Sunrise Coordination
- [x] Sonos alarm parsing with sun fallback and skip-next clearing
- [x] Per-zone sunrise offsets with anchor-triggered syncs

### Observability & Robustness
- [x] Rate limiter, retry, nightly sweep, and watchdog heartbeat coverage
- [x] Health and analytics sensors summarizing performance counters
- [x] Detailed legacy telemetry equivalents (real-time monitor, manual status aggregates)
- [x] Map extended mode aliases (Bright Focus, Dim Relax, Warm Evening, Cool Energy) to integration modes for UI parity

## Implementation_2 Companion Package
- [x] Draft `implementation_2.yaml` skeleton that calls Adaptive Lighting Pro public services instead of replicating logic
- [x] Provide example dashboard/scripts mirroring legacy helpers using integration entities and services
- [x] Document Sonos wake skip toggles and other optional lifestyle automations to include in the companion YAML once services are finalized

## Notes
- Update this tracker and README whenever tasks are completed or new gaps are identified.
- Environmental observer now mirrors Implementation_1 lux/weather logic, persists manual timer state, and exposes the new `set_zone_boost` service for per-zone boost control parity.
- Weather observer now includes canonical Home Assistant states plus regional aliases (rain showers, thunderstorm, mostly clear, etc.) so boost parity holds for diverse weather providers.
- Scenario validation traces documented in `docs/SCENARIO_VALIDATION.md`; architectural guardrails captured in `AGENTS.md`.
- Runtime API hardened for platform access (mode/scene options, zone tuning) to comply with guardrails added in this iteration.
- Verified scene presets reference valid Implementation_1 light groups and ensured rate-limit telemetry remains asserted while any zone is throttled.
- Companion package now mirrors Implementation_1 lifestyle helpers with group definitions, script wrappers, and automations for startup restore, movie bridging, sunset nudges, rate-limit alerts, nightly backups, and manual recovery, all backed by integration services.
- Updated runtime and test timekeeping to use timezone-aware `datetime.now(UTC)` so Home Assistant 2025.8+ compatibility warnings are eliminated.
- Added Sonos skip-next service, binary sensor, helper boolean automation loop, and dashboard snippet so sunrise deferrals mirror the legacy experience without bypassing integration guardrails.
- Added regression tests exercising every public service used by `implementation_2.yaml`, verified full-scene parity, and captured the completed migration in `YAML_MIGRATION_COMPLETE.md` with open enhancements tracked in `KNOWN_ISSUES.md`.
- Delivered `sensor.alp_sonos_anchor`, runtime anchor snapshots, and reminder automations so sunrise coordination is fully observable and actionable from dashboards.
- Restored presence-aware pausing, arrival recovery, holiday scheduling, and sunset scene logic inside `implementation_2.yaml`, aligned with integration services only.
- Expanded Lovelace examples and scenario validation docs to include analytics+scene stacks and sunrise monitoring guidance.
- Fired `adaptive_lighting_calculation_complete` events from runtime operations and restored the legacy status/realtime monitoring sensors with equivalent attributes and manual adjustment telemetry.
- Documented the calculation event, status/realtime sensors, and regression coverage across README, PROJECT_PLAN.md, YAML_MIGRATION_COMPLETE.md, KNOWN_ISSUES.md, and docs/SCENARIO_VALIDATION.md for long-term parity tracking.
- Runtime now persists the latest calculation payload and replays it to realtime/status entities so dashboards reflect manual adjustments even when Home Assistant listeners miss the event bus tick.
- Test harness now drains and cancels pending event-bus tasks after each scenario so pytest exits without lingering async warnings.
