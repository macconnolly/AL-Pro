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
| Zone light groups (`light:` platform group definitions) | Replaced by config-flow-defined zone light lists | Provide required helpers `group.all_lights` and `group.no_spots` to back scene toggles and physical fallbacks | Integration handles per-zone lights and Adaptive Lighting switch mapping internally. |
| Manual timers (`timer.adaptive_lighting_manual_timer_*`) | Superseded by `TimerManager` with persistent state | No YAML timers required | Runtime owns lifecycle; sensors expose timer states. |
| Manual adjustment helpers (`input_number` increment + scripts) | Replaced by `number` entities and `adaptive_lighting_pro.adjust` service | Ship scripts `script.alp_adjust_brighter/dimmer/warmer/cooler` that read number entities before calling `adjust` | Preserves dashboard compatibility while honoring dynamic steps. |
| Mode select/input booleans (`input_select.current_home_mode`, `input_boolean.*_mode`) | Modes handled by runtime + `select.alp_mode` | Provide `script.alp_select_mode` plus automations for movie playback resets and adaptive scene alignment | Keep alias mapping gap in TODO for future integration enhancement. |
| Environmental boost toggles (`input_boolean.al_environmental_boost_active`, `input_number.adaptive_lighting_environmental_brightness_offset`) | Environmental observer + options manage boost logic | No YAML automation; add Lovelace card guidance referencing integration entities | Per-zone enablement tracked in TODO. |
| Scene offsets (`input_number.al_scene_*`) and scripts (`apply_lighting_scene`) | Integration ships preset payloads, configurable offsets, and manual-timed execution | Provide scripts for all four household scenes, reset helpers, scene cycle, and Lovelace-friendly wrappers around `select_scene` | Presets persist via entry options and reapply automatically on updates. |
| Sunset fade automations | Integration emits positive-only sunset boosts with zone gating | Automation `alp_sunset_scene_nudge` listens to telemetry and nudges the scene when boost exceeds 15% | Keeps automation thin by relying on runtime telemetry. |
| Sonos wake sequence automations | Integration `sonos_integration.py` implements anchor parsing and exposes `adaptive_lighting_pro.skip_next_alarm` | Implementation_2 ships skip/resume scripts, boolean helper, and automations to keep the toggle aligned with `binary_sensor.alp_sonos_skip_next` | Integration clears skip flags and persists state via options callbacks. |
| Zen32 event automations & scripts | Device handler handles debounce, mapping, and actions | Provide optional YAML example for customizing advanced button remaps using runtime services | Scenes & adjustments now through integration; YAML example can call services if homeowners want alternative mapping. |
| Diagnostics sensors (`Adaptive Lighting Status`, `Real-Time Monitor`) | Integration exposes analytics & health sensors | Provide Lovelace dashboard snippets referencing new entity IDs | YAML sensors no longer required. |
| Global pause script | Integration exposes enable/disable zone services and global pause switch | Ship `script.alp_toggle_global_pause` and automation `alp_global_pause_exit_resync` for recovery | |
| Manual reset scripts per zone | Integration provides `adaptive_lighting_pro.reset_zone` service and manual sensors | Deliver `script.alp_reset_all_zones`, `script.alp_force_sync_zone`, and `script.alp_enable/disable_all_zones` | |
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

## Delivered implementation_2.yaml Structure
1. **Groups**
   - Defines `group.all_lights` and `group.no_spots` so the integration’s scene presets can toggle aggregates without custom YAML elsewhere.
2. **Scripts**
   - Scene wrappers (`script.alp_scene_*`), adjustment helpers, force-sync/reset flows, zone enable/disable helpers, backup/restore affordances, and select/scene cycling wrappers using public services only.
3. **Automations**
   - Startup restoration, movie-mode bridging, adaptive reset, sunset boost nudge, rate-limit notifications, global pause recovery, nightly backups, and manual zone recovery safeguards—all referencing integration entities.
4. **Template Button**
   - `button.alp_backup_and_sync` chains backup + sync for dashboards or quick actions.

## Outstanding Integration Work Feeding implementation_2
- Surface upcoming Sonos alarm metadata as a sensor so dashboards can show the next wake anchor.
- Additional dashboards or helpers for summarizing analytics beyond the built-in sensors.
- Future expansion hooks (e.g., holiday or presence-based scenes) as new requirements surface.

## Next Actions
1. Expand dashboard examples that combine manual sensors, analytics, and scene controls for a turnkey Lovelace experience (initial stack published in README, iterate with feedback).
2. Gather household feedback and adjust Implementation_2 defaults (script aliases, trigger thresholds) accordingly.
3. Evaluate exposing upcoming Sonos anchor times for dashboards once integration sensor lands.
