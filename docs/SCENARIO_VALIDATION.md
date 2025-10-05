# Scenario Validation & Logic Tracing

This document proves key Adaptive Lighting Pro behaviors using concrete code references. Each feature trace follows the format requested in the deep implementation analysis brief.

## Feature: Manual Control Timer Lifecycle
**User Story**: As a homeowner, my manual dimming/brightening should hold for the smart timeout and recover without conflicts.

**Logic Trace**:
1. Entry Point: Manual observer debounces light changes for each zone before emitting an `alp_manual_detected` event (`features/manual_control.py` L39-L74).
2. Data Flow: The runtime subscribes to this event, records metrics, computes adaptive-mode switching, and starts timers via the timer manager (`core/runtime.py` L585-L608).
3. State Changes: `ZoneManager.set_manual` persists the manual flag while `TimerManager.start` arms the per-zone expiry and records callbacks (`core/zone_manager.py` L84-L101, `core/timer_manager.py` L78-L125).
4. Exit Point: Entities read `zone_states()` for UI and timer callbacks clear overrides on expiry (`core/runtime.py` L1019-L1090, `core/runtime.py` L616-L624).

**✅ VERIFIED**

## Feature: Environmental Boost Calculation
**User Story**: When clouds roll in or the sun sets, boosts should help only when automation is in charge.

**Logic Trace**:
1. Entry Point: Lux/weather/sun observers recalculate boost state and post `alp_environmental_changed` events when thresholds change (`features/environmental.py` L24-L129).
2. Data Flow: Runtime handler rejects boosts outside adaptive mode and logs why, otherwise updates timer multipliers and honors per-zone opt-outs (`core/runtime.py` L655-L700).
3. State Changes: Timer manager stores environmental state and multiplier, limiting boosts to adaptive zones that allow them (`core/timer_manager.py` L63-L110).
4. Exit Point: Manual durations now incorporate environmental factors only when eligible, keeping mode intent intact (`core/timer_manager.py` L78-L110).

**✅ VERIFIED**

## Feature: Scene System + Manual Adjustment Layering
**User Story**: Scenes should apply rich presets without stomping on manual adjustments.

**Logic Trace**:
1. Entry Point: Scene selections validate the requested preset and trigger application (`features/scenes.py` L114-L130).
2. Data Flow: Scene execution skips manual zones, optionally toggles whole-house groups, posts manual timer events, and builds Adaptive Lighting payloads (`features/scenes.py` L133-L213).
3. State Changes: Runtime records the scene change, clears manual states before default scene resets, and refreshes telemetry (`core/runtime.py` L642-L646, L870-L886, L520-L533).
4. Exit Point: Zones without manual overrides receive the new preset via `adaptive_lighting.apply` through the executor pipeline (`core/executors.py` L71-L95).

**✅ VERIFIED**

## Feature: Button Press → State Change → Adaptive Lighting Update
**User Story**: The Zen32 keypad must provide immediate, mode-aware reactions.

**Logic Trace**:
1. Entry Point: Controller events with 250 ms debounce map to `alp_button_pressed` events (`devices/zen32_handler.py` L21-L112).
2. Data Flow: Runtime normalizes button/action pairs, enforces adaptive-mode restrictions, and delegates to scene cycling or manual adjustments (`core/runtime.py` L704-L803).
3. State Changes: Manual adjustments call `adjust(...)`, triggering timers and Adaptive Lighting apply calls, while resets clear manual state across all zones (`core/runtime.py` L520-L533, L771-L799).
4. Exit Point: Watchdog heartbeats, telemetry, and entity notifications keep UI feedback synchronized (`core/runtime.py` L300-L343, L312-L320).

**✅ VERIFIED**

## Feature: Startup Initialization & Restart Safety
**User Story**: After Home Assistant restarts—especially before sunrise—the integration must recover observers and timers.

**Logic Trace**:
1. Entry Point: `async_setup_entry` instantiates the runtime and forwards all platforms (`__init__.py` L15-L24).
2. Data Flow: Runtime setup loads zones, options, observers, watchdog, nightly sweep, and Sonos coordinator (`core/runtime.py` L218-L312).
3. State Changes: Sonos evaluation derives anchors from alarms or sun fallback with skip-next handling (`features/sonos_integration.py` L90-L170).
4. Exit Point: Startup events, telemetry snapshots, and heartbeat calls keep entities consistent, even after restarts during active sequences (`core/runtime.py` L278-L320, L655-L700).

**✅ VERIFIED**

## Feature: Timer Expiry & State Restoration
**User Story**: Late-night overrides should seamlessly hand control back to Adaptive Lighting once timers finish.

**Logic Trace**:
1. Entry Point: Timer callbacks post `alp_timer_expired` events (`core/timer_manager.py` L117-L124).
2. Data Flow: Runtime clears manual flags, disables Adaptive Lighting manual mode, and queues fresh syncs (`core/runtime.py` L616-L624).
3. State Changes: `_restore_previous_mode_if_idle` reinstates the saved mode only after all zones leave manual state (`core/runtime.py` L544-L560).
4. Exit Point: Fresh sync requests apply baseline Adaptive Lighting settings without race conditions (`core/runtime.py` L626-L635).

**✅ VERIFIED**

## Feature: Configuration → Behavior Validation
**User Story**: UI configuration sliders and selectors must change runtime behavior immediately.

**Logic Trace**:
1. Entry Point: Config flow validates zones, sensors, and controllers with selectors and helper validators (`config_flow.py` L56-L134; `utils/validators.py` L20-L117).
2. Data Flow: Options flow hot-applies timeouts, rate limits, debug toggles, watchdog cadence, and environmental boost multiplier (`config_flow.py` L136-L206; `core/runtime.py` L223-L245).
3. State Changes: Adjustment-step numbers, global pause, and other runtime settings expose getters/setters for platforms without touching internals (`core/runtime.py` L1036-L1120; `number.py` L14-L148; `switch.py` L25-L134).
4. Exit Point: Platforms consume runtime APIs exclusively, satisfying the architectural rule and instantly reflecting new settings in Home Assistant UI (`custom_components/adaptive_lighting_pro/*`).

**✅ VERIFIED**

## Feature: Graceful Degradation & Failure Modes
**User Story**: Sensor outages or configuration gaps should never crash automation.

**Logic Trace**:
1. Entry Point: Environmental observer catches parsing errors and treats unavailable sensors as `None` (`features/environmental.py` L67-L80).
2. Data Flow: Sonos parser falls back to sun-based anchors when no alarms exist or skip flags suppress the next alarm (`features/sonos_integration.py` L110-L167).
3. State Changes: Config validation rejects invalid switches/lights before runtime setup, preventing runtime crashes (`utils/validators.py` L70-L95).
4. Exit Point: Rate-limit binary sensor and health monitor provide visibility instead of silent failure, while nightly sweep clears orphans (`binary_sensor.py` L20-L47; `core/runtime.py` L344-L366).

**✅ VERIFIED**

## Feature: Sonos Skip Toggle Lifecycle
**User Story**: When I tap "Skip next sunrise" in the dashboard, the sunrise sequence should defer once and automatically resume afterward.

**Logic Trace**:
1. Entry Point: The new `adaptive_lighting_pro.skip_next_alarm` service receives boolean `skip` requests from scripts, automations, or the helper boolean (`core/runtime.py` L872-L896; `implementation_2.yaml` L206-L260, L332-L382).
2. Data Flow: Runtime delegates to the Sonos coordinator, whose skip callback persists the flag to config entry options and logs the event before re-evaluating the anchor (`features/sonos_integration.py` L48-L170; `core/runtime.py` L312-L339).
3. State Changes: The dedicated binary sensor reflects the current skip state while the helper boolean automation mirrors the integration flag for dashboards (`binary_sensor.py` L14-L101; `implementation_2.yaml` L332-L382).
4. Exit Point: Once the anchor passes, the coordinator clears the flag, triggering the callback and automation to reset the helper, ensuring the next alarm resumes automatically (`features/sonos_integration.py` L152-L170; `tests/test_sonos_parser.py` L63-L131).

**✅ VERIFIED**

## Feature: Sunset Boost with Per-Zone Gating
**User Story**: Near sunset, lights should brighten only in zones that allow boosts, using positive offsets instead of dimming.

**Logic Trace**:
1. Entry Point: The environmental observer samples sun elevation every five minutes and calculates a positive-only boost based on elevation, lux, and cloudiness (`features/environmental.py` L24-L149).
2. Data Flow: Runtime receives the `sunset_boost_pct` payload, records the active percentage, and updates zone boundaries while respecting mode checks (`core/runtime.py` L655-L694).
3. State Changes: Zones with `sunset_boost_enabled=False` keep their baseline boundaries, while eligible zones raise their minimum brightness via `change_switch_settings` (`core/runtime.py` L460-L498).
4. Exit Point: Telemetry exposes the active boost for dashboards and the Implementation_2 automations (`core/runtime.py` L808-L843).

**✅ VERIFIED**

## Feature: Scene Offsets, Reset, and Manual Action Sensors
**User Story**: Household scenes should carry configurable offsets, surface manual state, and offer a one-button reset to adaptive lighting.

**Logic Trace**:
1. Entry Point: Scene selection loads presets, applies configured offsets, fires manual timers, and logs offsets for context (`features/scenes.py` L60-L213).
2. Data Flow: Runtime captures scene offsets, updates manual action flags, and exposes them to number entities and binary sensors (`core/runtime.py` L320-L397, L1051-L1090).
3. State Changes: Manual action binary sensors mirror legacy input_booleans by reading runtime flags (`binary_sensor.py` L14-L89), while scene offset numbers drive runtime setters and persist options (`number.py` L14-L109; `core/runtime.py` L1054-L1091).
4. Exit Point: The dedicated scene reset button and Zen32 handler call `select_scene('default')`, clearing timers, offsets, and manual flags before requesting a sync (`button.py` L14-L61; `core/runtime.py` L786-L795).

**✅ VERIFIED**

## Feature: Scene Parity – Full Bright & No Spots
**User Story**: The legacy “All Lights” and “No Track Lights” presets should still run every fixture at the correct levels while starting manual timers.

**Logic Trace**:
1. Entry Point: `select_scene("all_lights" | "no_spots")` flows through the scene manager just like other intents (`features/scenes.py` L114-L213).
2. Data Flow: Group toggles fire through `call_light_service` for `group.all_lights` / `group.no_spots` before per-zone Adaptive Lighting payloads are sent (`features/scenes.py` L120-L176).
3. State Changes: Manual timers start for every affected zone, and offsets raise/lower brightness by the expected percentages (`core/runtime.py` L642-L694, `core/timer_manager.py` L78-L110).
4. Exit Point: Regression test `tests/test_adjust_and_scenes.py::test_additional_scene_presets_cover_full_house` confirms brightness 92% (Full Bright) and 85% (No Spots with +15% offset) and verifies manual flags stay active.

**✅ VERIFIED**

## Feature: Public Service API Parity
**User Story**: Every service exposed to Home Assistant or `implementation_2.yaml` must deliver the same guarantees as the YAML automations.

**Logic Trace**:
1. Entry Point: Services `force_sync`, `reset_zone`, `enable_zone`, `disable_zone`, `backup_prefs`, and `restore_prefs` are invoked directly by Implementation_2 scripts (`implementation_2.yaml` L95-L220).
2. Data Flow: Runtime helpers route through `ZoneManager` and `ExecutorManager` to ensure manual skip behavior, zone enablement, and config persistence are respected (`core/runtime.py` L829-L980).
3. State Changes: Manual flags clear via `set_manual_control(False)`, zone configs update, and restored options trigger a follow-up force sync (`core/runtime.py` L861-L907, L1019-L1060).
4. Exit Point: `tests/test_service_api_parity.py` covers manual skip handling, enable/disable flows, and backup/restore cycles with assertions for service payloads and state flags.

**✅ VERIFIED**

## Feature: Rate Limit Visibility & Persistence
**User Story**: When a burst of events trips the rate limiter, operators need accurate telemetry until all throttling clears.

**Logic Trace**:
1. Entry Point: Executor guardrails return a `RATE_LIMITED` payload when the moving-window threshold is exceeded (`core/executors.py` L40-L94).
2. Data Flow: Runtime aggregation now records a per-sync flag that remains true whenever any zone reports throttling across force-sync or adjust operations (`core/runtime.py` L826-L843, L948-L980).
3. State Changes: The rate-limit binary sensor reads this aggregated flag and exposes window load attributes for dashboards (`binary_sensor.py` L14-L46).
4. Exit Point: Subsequent syncs without throttling reset the telemetry, and scenario tests confirm the flag clears only after all zones succeed (`tests/test_adjust_and_scenes.py` L153-L196).

**✅ VERIFIED**

## Feature: Companion Package Integration Glue
**User Story**: Household automations and scripts built in `implementation_2.yaml` should orchestrate the integration without re-implementing logic.

**Logic Trace**:
1. Entry Point: Scene and adjustment scripts call public services and reference runtime entities (`implementation_2.yaml` L35-L260).
2. Data Flow: Lifestyle automations observe integration sensors/switches and respond with service calls for startup restore, movie bridging, sunset nudges, rate-limit notifications, Sonos skip toggles, and manual recovery (`implementation_2.yaml` L301-L420).
3. State Changes: Zone reset helpers loop through configured zone identifiers and issue `reset_zone` or `enable/disable_zone` calls while force sync ensures parameters refresh (`implementation_2.yaml` L149-L220, L301-L420).
4. Exit Point: Template button, global pause automation, and skip toggle sync use public APIs to keep dashboards and manual interventions in step with runtime state (`implementation_2.yaml` L179-L220, L332-L420, L439-L520).

**✅ VERIFIED**

## Home Assistant 2025.8+ Compliance Notes
- Python 3.12 compatibility with async/await patterns and selectors confirmed (`manifest.json`, `config_flow.py`).
- Platform modules remain in `custom_components/adaptive_lighting_pro/`—no symlinks are required for Home Assistant to discover them (`AGENTS.md`).
- Runtime exposes only public APIs to consumers, enforcing the mandated architecture and easing future HA core changes (`core/runtime.py` public accessors at L1036-L1120).

## Test Execution Path
Run the full suite with:
```bash
pytest
```
This covers config flow validation, Sonos parsing, manual detection timers, executor retry + rate limiting, watchdog/nightly sweep, Zen32 handling, and adjust/scene behaviors (see `tests/` directory).
