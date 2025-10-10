# ADR-002: Environment & Boost Manager

## Status
Accepted 2024-05-16

## Context
Environmental adaptation requires layering weather, lux, occupancy, and seasonal signals. YAML automation relies on manual conditions lacking resilience.

## Decision
Create an `EnvironmentManager` that aggregates sensor inputs, applies boost strategies, and coordinates decay once conditions normalize. Integrate availability tracking and fallback defaults.

## Consequences
- Resilient boosts when sensors offline.
- Consistent layering of foggy, cloudy, and S.A.D. profiles.
- Observability via counters and diagnostics.
