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
1. **Lifestyle Extensions** – Evaluate optional Sonos skip/acknowledge services and other lifestyle hooks that could land in a future release.
2. **Dashboard Polish** – Continue refining scenario validation docs and Lovelace guidance so Implementation_2 users can drop in dashboards without bespoke YAML.
3. **Feedback Loop** – Monitor manual sensor usage, analytics, and watchdog metrics to identify future enhancements beyond the legacy parity scope.

## Implementation_2 YAML Roadmap
A complementary automation package (`implementation_2.yaml`) will leverage the integration’s services rather than duplicating logic. Key goals include:
- Expose the three household scenes (Full Bright, No Track Lights, Dim Relax) via declarative calls to `adaptive_lighting_pro.select_scene` while layering manual timers.
- Provide dashboard-facing scripts/buttons that call integration services (mode selection, manual resets, adaptive force-sync) for user convenience.
- Offer opt-in automations that react to lifestyle signals (e.g., media center, bedtime) using public integration services instead of touching internals.

Details live in `docs/IMPLEMENTATION_2_PLAN.md`, which maps every retained YAML feature to its new home.

## Next Steps
- Finalize scene configuration APIs and document how per-zone payloads are defined.
- Deliver the implementation_2 YAML alongside migration guidance so existing dashboards transition smoothly.
- Continue closing TODO items while expanding regression coverage for each resolved gap.
