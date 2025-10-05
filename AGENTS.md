# Agent Guidelines for Adaptive Lighting Pro

## Scope
These instructions apply to the entire repository. Follow them in addition to any higher-priority user or system directives.

## Architectural Rules
- Do **not** access `AdaptiveLightingProRuntime` internals from platforms, services, or integrations. Always use its public methods.
- Before adding consumer logic, add or extend the runtime API first, complete with validation, logging, and tests.
- After implementing a feature, run:
  - `rg "coordinator\.data\[" custom_components/adaptive_lighting_pro` (must return no matches).
  - `rg "coordinator\._" custom_components/adaptive_lighting_pro` (must return no matches).
- Executors are the only layer allowed to call state-changing services except for the permitted light group toggles in the scene system.

## Development Workflow
1. Understand the daily-life scenario the change supports.
2. Implement runtime APIs **before** updating Home Assistant platforms or services.
3. Mirror existing patterns for naming, logging, and observability.
4. Keep the event-driven model intact—observers post events, executors handle service calls.
5. Update `TODO.md` and any relevant documentation for every change, recording completed tasks and new gaps.
6. Run `pytest` before committing.

## Testing Expectations
- Write scenario-driven tests that reflect real household workflows (morning wake, cloudy day boost, scenes, etc.).
- Maintain >80% coverage on critical paths; add regression tests when fixing bugs.
- Prefer async test helpers that mimic HA behavior; avoid brittle mocks of internals.

## File Organization
- Home Assistant platform modules (`switch.py`, `sensor.py`, etc.) stay in `custom_components/adaptive_lighting_pro/`; symlinks are not required.
- Shared docs belong in `docs/` with scenario traces and test plans.
- Ignore IDE caches, coverage artifacts, and archived status updates per repository `.gitignore` rules.

## Documentation Standards
- Keep `README.md` accurate for setup, architecture, and compatibility with Home Assistant 2025.8+.
- Track outstanding feature-parity items in `TODO.md` under the appropriate section.
- Document scenario validation traces (entry points, data flow, state changes, exit outcomes) when verifying complex behavior.
