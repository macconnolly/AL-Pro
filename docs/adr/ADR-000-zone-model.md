# ADR-000: Zone Model Architecture

## Status
Accepted 2024-05-16

## Context
The legacy YAML implementation orchestrates lighting behavior per-room with duplicated helper wiring. We require a typed representation capturing lights, helper bindings, manual behavior parameters, and environmental constraints for deterministic automation.

## Decision
Adopt a dataclass-driven domain model composed of `ZoneModel`, `ManualBehaviorProfile`, and `EnvironmentProfile`. Each zone persists in integration storage and drives coordinator orchestration.

## Consequences
- Enables schema validation and migrations.
- Supports asymmetric boundary enforcement ensuring manual boosts do not collapse adaptive ranges.
- Simplifies test fixture generation via dataclass factories.
