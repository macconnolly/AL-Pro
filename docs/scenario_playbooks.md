# Scenario Playbooks

## Morning Boost
- Trigger: Alarm set between 5:30–7:00 AM with foggy/cloudy sensors active.
- Actions: `al_layer_manager.start_manual_override` brightness 0.75, kelvin 3600.
- Validation: Ensure override timer extends to 45 minutes; analytics `overrides` counter increments.

## Cloudy Day
- Trigger: Lux sensor < 200 during 9:00–16:00.
- Actions: Environment manager applies cloudy boost, manual timers unchanged.
- Validation: Brightness increases ≤ boost cap; diagnostics shows available sensors.

## Sunset Warm Boost
- Trigger: Sun elevation below -3° with occupancy detected.
- Actions: Mode manager sets `relax`; environment adds warm offset.
- Validation: Color temperature <= 3200K within 1 transition.

## Evening Wind Down
- Trigger: 21:00–23:00 quiet hours, manual override started via voice.
- Actions: Manual override brightness 0.4, kelvin 3000, respect timer 60 minutes.
- Validation: Sync source remains manual, even when adaptive recalculates.

## Manual Stickiness
- Trigger: Zen32 button press toggles manual mode.
- Actions: Start override brightness 0.55; extend timer when additional press occurs.
- Validation: Override persists until explicit clear or timer expiry; health score unaffected.

## Nightlight Safety
- Trigger: After midnight occupancy triggered in hallway.
- Actions: Activate `late_night` mode with brightness multiplier 0.2.
- Validation: Transitions ≤ 5 seconds; analytics records mode activation.
