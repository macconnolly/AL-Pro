# Adaptive Lighting Pro

Adaptive Lighting Pro (ALP) is a Home Assistant custom integration that orchestrates Adaptive Lighting zones, manual overrides, environmental adjustments, and controller integrations using an event-driven runtime. The integration targets Home Assistant 2025.8+ and Python 3.12.

## Features
- Multi-zone orchestration that delegates light control to Adaptive Lighting switches
- Manual detection timers with dynamic duration based on mode, environment, and zone multiplier
- Environmental boosts driven by lux, weather, and sun position with positive sunset brightness support
- Mode and scene management with configurable offsets, timed presets, and a one-press reset back to adaptive mode
- Scene brightness and warmth offsets persist via config entry options and reapply automatically when scenes change
- Zen32 controller event handling with per-button debounce
- Sonos-aware sunrise coordination with per-zone offsets, skip-next service, and binary sensor status
- Retry, rate limiting, nightly sweep, watchdog, and observability metrics
- Manual adjustment state sensors mirroring the legacy input booleans for brighter/dimmer/warmer/cooler actions
- Status and realtime monitor sensors that replicate the original template sensors with calculation summaries and context
- Emits the legacy `adaptive_lighting_calculation_complete` Home Assistant event for every sync, adjustment, or environmental up
  date so downstream automations remain compatible
- Upcoming sunrise anchor sensor with countdown attributes, skip toggles, and reminder automations

## Home Assistant Compatibility
- Targets Home Assistant 2025.8+ and Python 3.12 runtimes.
- Component platforms live under `custom_components/adaptive_lighting_pro/`; no symlinks are needed for Home Assistant to discover them.
- Config flow uses modern selectors and validation helpers so the full setup experience remains UI-driven and restart-safe.

## Scenario Validation
See [`docs/SCENARIO_VALIDATION.md`](docs/SCENARIO_VALIDATION.md) for end-to-end logic traces covering manual overrides, environmental boosts, scenes, controllers, sunrise coordination, and failure handling.

## Observability & Events
- `sensor.alp_status` summarizes mode, scene, manual adjustments, timers, and health context for quick diagnostics.
- `sensor.alp_realtime_monitor` mirrors the legacy realtime monitor sensor, exposing the latest calculation payload, trigger source, and resulting brightness/color-temperature adjustments, even after restarts thanks to the runtime caching the most recent `adaptive_lighting_calculation_complete` event.
- Every runtime sync, manual adjustment, environmental update, or scene application fires the `adaptive_lighting_calculation_complete` event with serialized telemetry so dashboards and downstream automations continue to react instantly.

## Implementation Roadmap
- [`PROJECT_PLAN.md`](PROJECT_PLAN.md) captures the architectural vision, open parity themes, and how Adaptive Lighting Pro replaces the YAML package.
- [`docs/IMPLEMENTATION_2_PLAN.md`](docs/IMPLEMENTATION_2_PLAN.md) details which legacy `implementation_1.yaml` behaviors remain in the integration and which land in the companion package built on public services.
- [`implementation_2.yaml`](implementation_2.yaml) now includes scene wrappers, manual adjustment helpers, zone reset/enable tooling, lifestyle automations (startup restore, movie bridge, nightly backup, Sonos skip toggles), and notifications driven exclusively through public APIs.
- Presence-aware pausing, holiday scheduling, and sunrise reminders are implemented in the companion package so daily routines remain frictionless without touching integration internals.

## Companion Package Highlights
- Defines the `group.all_lights` and `group.no_spots` helpers required by the scene presets baked into the integration.
- Provides scripts for the full household scene set, manual adjustments, force-sync/reset workflows, zone enable/disable helpers, and backup/restore affordances.
- Ships lifestyle automations covering startup restoration, movie-mode bridging, manual decay reversion, global pause recovery, nightly backups, rate-limit notifications, Sonos skip toggle synchronization, presence-based pausing/resume, seasonal holiday scenes, and sunrise anchor reminders.
- Keeps configuration thin by delegating timers, calculations, and boosts to the integration runtime while exposing Lovelace-friendly entry points.
- Validated against new regression tests that exercise all scenes plus force-sync/reset/backup/restore services so the companion package only relies on supported APIs.

## Service & Migration Parity
- `tests/test_service_api_parity.py` verifies that public services used by `implementation_2.yaml` (force sync, enable/disable/reset zone, backup/restore) behave correctly, including manual skip handling and option persistence.
- `tests/test_adjust_and_scenes.py` now covers the full scene catalog (Full Bright, No Spots, Evening Comfort, Ultra Dim) ensuring manual timers, offsets, and group toggles all behave exactly like Implementation_1.
- [`YAML_MIGRATION_COMPLETE.md`](YAML_MIGRATION_COMPLETE.md) documents the final parity audit and references where each legacy capability lives.
- [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) tracks deferred enhancements (e.g., future Sonos anchor sensor and richer analytics views) so follow-on work is transparent.
- `KNOWN_ISSUES.md` now lists zero open items because the sunrise anchor sensor, presence/holiday automations, and dashboard polish all landed in this release.

## Installation
1. Copy the `custom_components/adaptive_lighting_pro` directory to your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Add the integration via the UI and configure zones and sensors.

## Configuration Options
- **UI Flow (recommended):** Use Settings → Devices & Services → Add Integration → Adaptive Lighting Pro to launch the selector-driven config flow. Zones, sensors, and controllers are validated against live entities before the entry is created.
- **configuration.yaml import (new in this release):** Define one or more entries under the `adaptive_lighting_pro:` key. On startup the integration normalizes the YAML payload, promotes nested `sensors`/`controllers` mappings to the format expected by the config flow, and imports each entry via the same validation path as the UI. Example:

  ```yaml
  adaptive_lighting_pro:
    zones:
      - zone_id: living
        al_switch: switch.living_room_adaptive
        lights:
          - light.living_room_floor_lamp
          - light.living_room_ceiling
    sensors:
      lux_entity: sensor.outdoor_lux
      weather_entity: weather.home
    controllers:
      zen32_device_id: 1234abcd5678
  ```

- The YAML import is optional—the integration still exposes the full options flow for runtime adjustments (timeouts, rate limits, environmental multiplier, scene presets).
- Regardless of setup method, zone validation ensures each Adaptive Lighting switch exists, every light entity ID is scoped correctly, and duplicate `zone_id` values are rejected so parity with `implementation_1.yaml` remains intact.

## Development
Install dev dependencies (requires Home Assistant core development environment) and run tests with `pytest`.

## Task Tracker
- [x] Scaffold integration structure and runtime orchestrator
- [x] Implement manual detection, environmental observer, Sonos parser, and watchdog
- [x] Wire Home Assistant platforms (switch, sensors, numbers, selects, buttons)
- [x] Provide config flow, options flow, and public services
- [x] Expand scene executors with richer group handling
- [x] Implement full adjustment logic for incremental brightness/CT steps
- [x] Wire watchdog heartbeats from observers/executors so routine ticks do not trigger constant resets
- [x] Surface the rate-limit binary sensor entity defined in constants
- [x] Honor the env_multiplier_boost option when updating timer multipliers
- [x] Provide Sonos sunrise fallback behavior when no alarms are scheduled
- [x] Implement global pause switch, configurable adjustment steps, and Zen32 button mapping
- [x] Add telemetry snapshot sensor mirroring legacy dashboards
- [x] Upgrade config flow with selectors for zones, sensors, controllers, and expose environmental boost option
- [x] Align manual scene presets with timer lifecycle and provide adaptive reset handling when returning to default
- [x] Deliver Sonos skip-next service, binary sensor, and companion automations for sunrise deferrals
- [x] Publish sunrise anchor sensor/notifications and integrate presence/holiday lifestyle automations in the companion package

## Lovelace Quick Start Stack
Paste the snippet below into the UI editor’s "Manual" tab to surface the most useful controls and telemetry on a single dashboard column:

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Adaptive Lighting Pro Controls
    entities:
      - entity: select.alp_mode
        name: Mode
      - entity: select.alp_scene
        name: Scene
      - entity: number.alp_brightness_step
        name: Brightness Step
      - entity: number.alp_color_temp_step
        name: Color Temp Step
      - entity: binary_sensor.alp_sonos_skip_next
        name: Skip Next Sunrise (Active)
      - entity: input_boolean.alp_skip_next_sunrise
        name: Toggle Skip Sunrise
      - entity: button.alp_backup_and_sync
        name: Backup & Sync
  - type: entity
    entity: sensor.alp_sonos_anchor
    name: Sunrise Anchor
    secondary_info: last-updated
  - type: gauge
    entity: sensor.alp_health_score
    name: ALP Health
    min: 0
    max: 100
  - type: entities
    title: Manual Override Watch
    entities:
      - binary_sensor.alp_manual_main_living
      - binary_sensor.alp_manual_kitchen_island
      - binary_sensor.alp_manual_bedroom_primary
      - binary_sensor.alp_manual_accent_spots
      - binary_sensor.alp_manual_recessed_ceiling
  - type: entities
    title: Analytics Snapshot
    entities:
      - sensor.alp_system_snapshot
      - sensor.alp_analytics_summary
      - binary_sensor.alp_rate_limit_reached
  - type: entities
    title: Presence & Holiday Controls
    entities:
      - group.alp_presence_household
      - input_boolean.alp_holiday_mode
      - automation.alp_presence_pause_when_away
      - automation.alp_presence_resume_when_home
      - automation.alp_holiday_evening_scene
```
