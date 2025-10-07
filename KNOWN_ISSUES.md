# Known Issues & Future Enhancements

All previously tracked gaps have been closed in this iteration. The integration and companion package now provide:

- **Sonos anchor visibility** – `sensor.alp_sonos_anchor` exposes the next alarm or sunrise anchor, skip flag, and countdown timers for dashboards and automations.
- **Presence & holiday lifestyle automations** – `implementation_2.yaml` restores advanced away-mode pausing, arrival recovery, seasonal scheduling, and sunset holiday scenes while staying on the public API surface.
- **Expanded analytics guidance** – The README and scenario validation docs include Lovelace card stacks and usage recipes that visualize manual overrides, analytics counters, and scene controls without additional YAML.
- **Status & realtime sensors restored** – `sensor.alp_status` and `sensor.alp_realtime_monitor` replicate the legacy templates while the runtime fires `adaptive_lighting_calculation_complete` for downstream automations.

No open issues remain. Record any future discoveries in this file so the history stays transparent.
