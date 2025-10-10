# ADR-001: Manual Intent Engine

## Status
Accepted 2024-05-16

## Context
Manual adjustments to lighting must be respected with smart decay curves while coexisting with adaptive behavior. The YAML version encodes this across scattered automations and helpers.

## Decision
Centralize manual overrides via a `ManualIntentManager` responsible for detecting manual events, computing dynamic timers, and blending outputs with adaptive targets. Provide integration services for start/extend/clear to enable automation interoperability.

## Consequences
- Consistent override state machine with analytics instrumentation.
- Deterministic boundaries preventing manual collapse.
- Simplified service contract for wall controllers, voice, and scenes.
