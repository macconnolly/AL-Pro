# Dependency & Risk Log

| ID | Dependency | Risk | Mitigation | Linked Tasks |
| --- | --- | --- | --- | --- |
| R1 | adaptive_lighting integration | API changes or unavailable service | Provide native adaptive provider fallback; monitor errors via diagnostics | P2.D, P4.A |
| R2 | Weather & forecast sensors | Provider downtime leading to stale boosts | Implement availability tracking + decay to defaults | P3.A, P3.B |
| R3 | Occupancy sensors | False negatives triggering lights off | Introduce hysteresis + manual override precedence | P3.F, P2.B |
| R4 | Sonos speakers | Wake routine fails | Provide manual fallback scenes + health alerts | P2.F, P4.C |
| R5 | Wearable integration | Privacy concerns | Document opt-in, anonymize data, allow disable | P3.D, P6.E |
