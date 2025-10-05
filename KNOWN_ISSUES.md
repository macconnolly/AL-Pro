# Known Issues & Future Enhancements

Adaptive Lighting Pro meets the legacy feature set, but a few enhancements remain on the radar. Track each item here so future contributors can prioritize them without re-reading historical PRs.

1. **Upcoming Sonos Anchor Sensor** – The runtime exposes skip-next controls, but dashboards still lack a dedicated sensor for the next alarm timestamp. Add a read-only sensor once the Sonos coordinator publishes anchor metadata. *(Owner: Integration; File: `features/sonos_integration.py`)*
2. **Advanced Presence/Holiday Automations** – Implementation_1 shipped seasonal/presence experiments that were intentionally deferred. Capture user feedback before reintroducing them using the public service layer. *(Owner: Companion Package; File: `implementation_2.yaml`)*
3. **Extended Analytics Visualization** – Health and analytics sensors provide raw metrics, but richer Lovelace examples (graphs/alerts) should be added as future iterations to aid operators. *(Owner: Documentation; File: `README.md` + `docs/SCENARIO_VALIDATION.md`)*

No blocking defects are currently known; all essential workflows pass automated tests and scenario validation. Update this list whenever new gaps surface.
