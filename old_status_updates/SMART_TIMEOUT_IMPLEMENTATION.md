# Smart Timeout Implementation

## Overview

The smart timeout feature calculates dynamic timer durations for manual control based on environmental conditions. This ensures manual adjustments persist for appropriate durations based on context.

## Implementation

### Files Modified

1. **features/manual_control.py** - Lines 73-134
   - Simplified `calculate_smart_timeout()` to work without mode system
   - Removed mode-based timeout selection
   - Kept conditional logic based on sun elevation and environmental boost

2. **features/zone_manager.py** - Lines 112-128, 232-278
   - Added `manual_detector` parameter to `__init__`
   - Modified `async_start_manual_timer()` to accept `sun_elevation` and `env_boost`
   - Calls `manual_detector.calculate_smart_timeout()` when duration is None
   - Falls back to config default if manual_detector is not available

3. **coordinator.py** - Lines 48, 103-107, 648-682
   - Imports `ManualControlDetector`
   - Initializes `_manual_detector` and passes to ZoneManager
   - Modified `start_manual_timer()` to gather environmental data
   - Passes `sun_elevation` from sun.sun entity and `env_boost` from environmental adapter

## Smart Timeout Logic

### Base Timeout
- **30 minutes (1800 seconds)** - reasonable default for most manual adjustments

### Multipliers

1. **Night Extension (1.5x)**
   - Activated when sun elevation < -6° (astronomical twilight)
   - Rationale: Manual adjustments at night should persist longer as conditions change less

2. **Dim Conditions Extension (1.3x)**
   - Activated when environmental boost > 10%
   - Rationale: Cloudy/dark conditions persist longer, manual adjustment should too

### Maximum Duration
- **2 hours (7200 seconds)** - prevents indefinite manual control

## Examples

### Scenario 1: Daytime, Clear Weather
```python
sun_elevation = 45°  # Midday
env_boost = 0%       # Clear sunny day

timeout = 1800 * 1.0 = 1800s (30 minutes)
```

### Scenario 2: Night, Clear Weather
```python
sun_elevation = -10°  # Night
env_boost = 0%        # Clear (no boost at night due to time multiplier)

timeout = 1800 * 1.5 = 2700s (45 minutes)
```

### Scenario 3: Night, Cloudy (Hypothetical)
```python
sun_elevation = -10°  # Night
env_boost = 15%       # Would be high if calculated during day

timeout = 1800 * 1.5 * 1.3 = 3510s (58.5 minutes)
```

### Scenario 4: Daytime, Very Dark/Cloudy
```python
sun_elevation = 20°  # Daytime
env_boost = 18%      # Foggy/dark

timeout = 1800 * 1.0 * 1.3 = 2340s (39 minutes)
```

## Integration Points

### When Smart Timeout is Used

1. **User presses brightness/warmth buttons** via services
2. **Scene application** triggers manual timer
3. **Any service call** to `start_manual_timer()` without explicit duration

### Data Sources

1. **Sun Elevation**: `sun.sun` entity attribute `elevation`
2. **Environmental Boost**: Calculated by `EnvironmentalAdapter.calculate_boost()`

## Fallback Behavior

If `ManualControlDetector` is not initialized or data is unavailable:
- Falls back to config value `CONF_MANUAL_TIMER_DURATION`
- Default: `DEFAULT_MANUAL_TIMEOUT_SECONDS` (3600s = 1 hour)

## Alignment with Simplified Architecture

✅ **No mode dependency** - Works with automatic/manual state model
✅ **Conditional logic preserved** - Night/dim extensions still active
✅ **Simple and predictable** - Clear base + multipliers model
✅ **Prevents indefinite manual** - 2-hour maximum ensures return to adaptive

## Testing Considerations

1. **Unit tests** should verify multiplier calculations
2. **Integration tests** should verify sun/env data gathering
3. **Real-world testing** should validate timeout feels appropriate in different conditions

