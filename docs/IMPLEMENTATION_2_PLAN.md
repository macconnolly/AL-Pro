# implementation_2.yaml Planning Guide

## Purpose
The legacy `implementation_1.yaml` bundled every helper, automation, and script required to tame Adaptive Lighting. Adaptive Lighting Pro now absorbs the orchestration core, so the follow-up package must focus on user-facing conveniences that sit on top of the integration’s public services. This guide catalogs the original YAML capabilities, highlights what the integration already covers, and defines what the lean `implementation_2.yaml` should provide.

## Methodology
1. Reviewed the entire `implementation_1.yaml`, identifying each feature class (helpers, automations, scripts, scenes, sensors).
2. Cross-referenced integration modules (`custom_components/adaptive_lighting_pro/**`) to confirm whether functionality moved into code.
3. Documented remaining gaps and determined whether they belong in integration enhancements (tracked via `TODO.md`) or the new YAML companion file.

## Feature Mapping
| Legacy Capability | Status in Integration | implementation_2 Action | Notes |
| --- | --- | --- | --- |
| Zone light groups (`light:` platform group definitions) | Replaced by config-flow-defined zone light lists | Provide optional groups only if dashboards still require entity aggregation | Integration handles per-zone lights and Adaptive Lighting switch mapping internally. |
| Manual timers (`timer.adaptive_lighting_manual_timer_*`) | Superseded by `TimerManager` with persistent state | No YAML timers required | Runtime owns lifecycle; sensors expose timer states. |
| Manual adjustment helpers (`input_number` increment + scripts) | Replaced by `number` entities and `adaptive_lighting_pro.adjust` service | Add dashboard scripts/buttons calling integration services | Provide simple wrappers that call integration services for UI compatibility. |
| Mode select/input booleans (`input_select.current_home_mode`, `input_boolean.*_mode`) | Modes handled by runtime + `select.alp_mode` | Offer optional automations to sync with other systems (e.g., media, bedtime) using `adaptive_lighting_pro.select_mode` | Keep alias mapping gap in TODO for future integration enhancement. |
| Environmental boost toggles (`input_boolean.al_environmental_boost_active`, `input_number.adaptive_lighting_environmental_brightness_offset`) | Environmental observer + options manage boost logic | No YAML automation; add Lovelace card guidance referencing integration entities | Per-zone enablement tracked in TODO. |
| Scene offsets (`input_number.al_scene_*`) and scripts (`apply_lighting_scene`) | Integration ships preset payloads, configurable offsets, and manual-timed execution | Wrap public `select_scene` service inside scripts/buttons; adjust offsets through number entities | Presets persist via entry options and reapply automatically on updates. |
| Sunset fade automations | Integration emits positive-only sunset boosts with zone gating | Implementation_2 may optionally react to telemetry (e.g., switch scenes when boost exceeds threshold) | No YAML fade logic required; automation example `alp_sunset_scene_nudge` covers gentle nudges. |
| Sonos wake sequence automations | Integration `sonos_integration.py` implements anchor parsing | Implementation_2 may include optional automation to surface upcoming alarm or skip toggles | Integration already clears skip flags and schedules sync. |
| Zen32 event automations & scripts | Device handler handles debounce, mapping, and actions | Provide optional YAML example for customizing advanced button remaps using runtime services | Scenes & adjustments now through integration; YAML example can call services if homeowners want alternative mapping. |
| Diagnostics sensors (`Adaptive Lighting Status`, `Real-Time Monitor`) | Integration exposes analytics & health sensors | Provide Lovelace dashboard snippets referencing new entity IDs | YAML sensors no longer required. |
| Global pause script | Integration exposes enable/disable zone services and global pause switch | Add dashboard script that toggles `switch.alp_global_pause` if desired | |
| Manual reset scripts per zone | Integration provides `adaptive_lighting_pro.reset_zone` service and manual sensors | Provide script wrappers that call the service for UI parity | |
| Wake sequence offsets and flags | Runtime tracks via options + Sonos integration | Implementation_2 should include UI wrappers for skip-next controls using integration services once exposed | Skip flag service request tracked in TODO. |

## Scene Parity Tasks
The original YAML delivered four human-friendly scenes. The integration covers default/ultra dim, but we must explicitly restore the following behaviors:
1. **Scene 1 – Full Bright (All Lights)**
   - Turn on all zones at neutral warmth and high brightness.
   - Start manual timers for each affected zone so user adjustments persist.
   - Re-enable adaptation once the “Default” scene is chosen again.
2. **Scene 2 – No Track Lights**
   - Turn off accent spot lights while boosting remaining zones by ~15%.
   - Trigger manual timers for affected zones to respect user intent.
3. **Scene 3 – Dim Relax (Evening Comfort)**
   - Reduce brightness ~5%, warm by ~500K, favor lamps over ceiling/recessed fixtures.
   - Maintain manual timers while still allowing environmental boosts once adaptation resumes.

These behaviors are now baked into the integration presets. Implementation_2 scripts simply call `adaptive_lighting_pro.select_scene` and rely on the runtime for manual timers, offsets, and per-zone actions.

## Proposed implementation_2.yaml Structure
1. **Helpers (Optional)**
   - Re-create only the Lovelace-facing helpers still needed for dashboards (e.g., toggles or selects that users manually interact with). Most numeric controls are now provided by integration entities.
2. **Scripts**
   - Thin wrappers that call integration services (`force_sync`, `reset_zone`, `select_mode`, `select_scene`, `adjust`).
   - Dedicated scripts for the three household scenes, each calling `adaptive_lighting_pro.select_scene` with context metadata for analytics.
3. **Automations**
   - Lifestyle hooks (e.g., trigger Late Night mode at `input_datetime.late_night_start` or when `media_player` enters “playing movie”).
   - Optional fallback toggles, such as re-enabling adaptive lighting after power restoration by invoking `adaptive_lighting_pro.enable_zone` for all zones.
4. **Dashboard Guidance**
   - Provide example Lovelace card configuration referencing integration entities (manual sensors, analytics, rate-limit binary sensor).

## Outstanding Integration Work Feeding implementation_2
- Optional Sonos wake skip/acknowledge service for user-driven anchor management.
- Additional dashboards or helpers for summarizing analytics beyond the built-in sensors.
- Future expansion hooks (e.g., holiday or presence-based scenes) as new requirements surface.

## Next Actions
1. Iterate on optional lifestyle automations (e.g., Sonos skip toggles) as supporting services land in the integration.
2. Expand dashboard examples that combine manual sensors, analytics, and scene controls for a turnkey Lovelace experience.
3. Gather household feedback and adjust Implementation_2 defaults (script aliases, trigger thresholds) accordingly.
