# Scenario Test Charter

## Personas & Scenarios
- **Morning Boost**: Foggy winter morning requires +25% brightness boost and warmer temperature for wakefulness.
- **Cloudy Workday**: Midday ambient lux drops triggering moderate brightness lift without exceeding manual boundaries.
- **Sunset Warm Boost**: At dusk, color temperature warms quickly to preserve circadian rhythm while respecting manual dimming.
- **Evening Wind Down**: Relax mode dims lights and lengthens transitions, persisting manual tweaks.
- **Manual Stickiness**: Physical button sets custom brightness that remains until timer expiry.
- **Nightlight Safety**: After midnight, occupancy triggers low brightness ensuring safe navigation.

## Mapping
| Scenario | Sensors | Services | Metrics |
| --- | --- | --- | --- |
| Morning Boost | weather, lux, occupancy, alarm | `al.start_manual_override`, `al.apply_zone_state` | boost latency, override duration |
| Cloudy Workday | lux, weather | `al.apply_environment_profile` | boost magnitude, decay profile |
| Sunset Warm Boost | sun, weather | `al.mode.set` | transition duration, color temp |
| Evening Wind Down | presence, mode helpers | `al.mode.set_relax` | manual stickiness, override timer |
| Manual Stickiness | controller events | manual services | override counter increments |
| Nightlight Safety | occupancy, bedtime | `al.mode.set_late_night` | health score, latency |

## Acceptance Gates
- Manual override response < 100 ms end-to-end.
- Scenario tests require coverage instrumentation for managers (>90%).
- Failing sensors degrade gracefully with warnings logged and health scores reduced but no automation crash.
