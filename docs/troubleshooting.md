# Troubleshooting Matrix

| Symptom | Possible Cause | Resolution |
| --- | --- | --- |
| Manual override ends early | Timer helper misconfigured | Validate helper binding, extend via `al.extend_manual_override` |
| Lights ignore boosts | Sensor unavailable or stale | Check diagnostics, ensure sensor updates within 30 minutes |
| Mode transitions slow | Transition seconds too high | Adjust mode profile or service payload |
| Health score low | Missed syncs or stuck overrides | Inspect analytics counters, clear overrides, review logs |
| Scene configs flagged | User entities present | Remove user-specific entities before HACS submission |
