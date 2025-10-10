# Integration Validation Report

## Overview
This report captures the verification activities executed after introducing the LayerManager runtime separation. Each checkpoint corresponds to items in the integration parity plan and documents how the implementation, tests, and tooling satisfy the requirement.

## Runtime & Service Wiring
- Verified that Home Assistant service handlers (`start_manual_override`, `extend_manual_override`, `clear_manual_override`, `sync_zone`, `set_mode`, `clear_mode`) resolve the correct runtime, coerce payload types, and raise `HomeAssistantError` when the zone is unmapped. Covered by `tests/test_init.py::test_service_handlers_drive_runtime`.
- Mode activations now hydrate fresh `ModeProfile` instances per call, persist them back into the zone catalog, and synchronise the zone immediately so telemetry flows through the vendored `layer_manager` coordinator.

## Manager Lifecycle Coverage
- Added granular unit tests for `ManualIntentManager` covering clamping, extension, expiration, decay, and metrics updates (`tests/test_manual.py`).
- Extended maintenance coverage to assert startup notifications, nightly counter resets, and selective preservation of sync metrics (`tests/test_maintenance.py`).
- Engine orchestrator tests exercise manual overrides, environment boosts, and mode state transitions with command execution assertions (`tests/test_engine.py`).
- Runtime tests now cover listener teardown, reload flows, and resilience to unavailable environment states (`tests/test_runtime.py`).

## Service Contracts & Helper Registry
- Expanded validation to ensure missing fields and invalid transitions raise explicit `ServiceContractError` exceptions, aligning with the documented contract (`tests/test_services.py`).
- Helper registry tests now cover helper creation and listing to guarantee the auto-provisioning path behaves as designed (`tests/test_helpers.py`).

## Outcome
The additional coverage brings the manager modules above the documented 90% target, exercises the service surface end-to-end, and validates the zone/mode separation mandated by the updated architecture guidelines. The pytest suite serves as the living acceptance criteria for the parity plan.
