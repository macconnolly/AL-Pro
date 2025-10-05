# Adaptive Lighting Pro

Adaptive Lighting Pro (ALP) is a Home Assistant custom integration that orchestrates Adaptive Lighting zones, manual overrides, environmental adjustments, and controller integrations using an event-driven runtime. The integration targets Home Assistant 2025.8+ and Python 3.12.

## Features
- Multi-zone orchestration that delegates light control to Adaptive Lighting switches
- Manual detection timers with dynamic duration based on mode, environment, and zone multiplier
- Environmental boosts driven by lux, weather, and sun position with positive sunset brightness support
- Mode and scene management with configurable offsets, timed presets, and a one-press reset back to adaptive mode
- Scene brightness and warmth offsets persist via config entry options and reapply automatically when scenes change
- Zen32 controller event handling with per-button debounce
- Sonos-aware sunrise coordination with per-zone offsets and skip-next support
- Retry, rate limiting, nightly sweep, watchdog, and observability metrics
- Manual adjustment state sensors mirroring the legacy input booleans for brighter/dimmer/warmer/cooler actions

## Home Assistant Compatibility
- Targets Home Assistant 2025.8+ and Python 3.12 runtimes.
- Component platforms live under `custom_components/adaptive_lighting_pro/`; no symlinks are needed for Home Assistant to discover them.
- Config flow uses modern selectors and validation helpers so the full setup experience remains UI-driven and restart-safe.

## Scenario Validation
See [`docs/SCENARIO_VALIDATION.md`](docs/SCENARIO_VALIDATION.md) for end-to-end logic traces covering manual overrides, environmental boosts, scenes, controllers, sunrise coordination, and failure handling.

## Implementation Roadmap
- [`PROJECT_PLAN.md`](PROJECT_PLAN.md) captures the architectural vision, open parity themes, and how Adaptive Lighting Pro replaces the YAML package.
- [`docs/IMPLEMENTATION_2_PLAN.md`](docs/IMPLEMENTATION_2_PLAN.md) details which legacy `implementation_1.yaml` behaviors remain in the integration and which will graduate to a slimmer `implementation_2.yaml` built on top of public services.
- [`implementation_2.yaml`](implementation_2.yaml) ships a ready-to-use companion package with declarative scene scripts, adjustment helpers, and post-movie reset automations powered entirely by public services.

## Installation
1. Copy the `custom_components/adaptive_lighting_pro` directory to your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Add the integration via the UI and configure zones and sensors.

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
