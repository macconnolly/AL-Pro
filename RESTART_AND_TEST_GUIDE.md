# Restart and Testing Guide

## All Fixes Applied - Ready for Testing

7 critical fixes have been applied to fix production issues.

## Before Restart - What Was Fixed

1. ✅ **Environmental Boost (lux_sensor = null)** - YAML restructuring in config_flow.py
2. ✅ **3 Unavailable Sensors** - Fixed coordinator attribute reference in sensor.py
3. ✅ **Scene AUTO Button Missing** - Added to button.py
4. ✅ **AUTO Scene Doesn't Reset** - Fixed to call proper AL services in coordinator.py
5. ✅ **Reset Doesn't Return to AUTO** - Changed default scene in coordinator.py
6. ✅ **Options Flow Broken** - Fixed nested structure handling in config_flow.py
7. ✅ **Options Schema Wrong Defaults** - Fixed to read from global_settings in config_flow.py

## CRITICAL: Restart Required

**All code fixes are in place but Home Assistant must restart to load them.**

```bash
# Settings → System → Restart Home Assistant
# OR via CLI:
ha core restart
```

## After Restart - Systematic Testing

### Step 1: Verify Integration Loaded

Check that integration started without errors:

```bash
# Via Developer Tools → States, search for:
sensor.adaptive_lighting_pro_alp_status

# Should show: state = "Adaptive" (not "Unknown" or "unavailable")
```

### Step 2: Check Environmental Boost

```bash
# Developer Tools → States
sensor.adaptive_lighting_pro_alp_environmental_boost

# Check attributes:
# - current_lux: should be a NUMBER (e.g., 86), NOT null
# - boost_active: true/false based on conditions
```

**Expected**: `current_lux` populated with value from sensor.living_room_presence_light_sensor_light_level

### Step 3: Check Unavailable Sensors

All three should now be available:

```bash
sensor.adaptive_lighting_pro_alp_performance_metrics
sensor.adaptive_lighting_pro_alp_health_status
sensor.adaptive_lighting_pro_alp_system_health
```

**Expected**: All show proper states, NOT "unavailable" with restored=true

### Step 4: Verify Scene AUTO Button Exists

```bash
button.adaptive_lighting_pro_scene_auto
```

**Expected**: Entity exists and is pressable

### Step 5: Test Button Press & Timer Creation

**CRITICAL TEST** - This is where the 500 error occurred:

```bash
# 1. Press Brighter button
# Via UI or Developer Tools → Services:
service: button.press
target:
  entity_id: button.adaptive_lighting_pro_brighter

# 2. IMMEDIATELY check timer status (within seconds)
sensor.adaptive_lighting_pro_alp_manual_timer_status

# Expected attributes:
# - active_zones: ["recessed_ceiling", "kitchen_island", "bedroom_primary", "accent_spots", "main_living"]
# - total_active: 5
# - timer_details: {...} with expiry times

# 3. Check individual zone manual control sensor
sensor.adaptive_lighting_pro_main_living_manual_control

# Expected attributes:
# - manual_control_active: true
# - timer_remaining_seconds: ~7200 (2 hours)
# - timer_finishes_at: timestamp ~2 hours from now
```

**If This Still Fails**:

Check logs immediately after button press:

```bash
# Settings → System → Logs
# Filter for: "adaptive_lighting_pro"
# Look for: Exception, Traceback, ERROR
```

Common failure scenarios:
- KeyError on zone_id (zone config structure mismatch)
- AttributeError on coordinator (missing method)
- Service call failed (AL integration not responding)

### Step 6: Test AUTO Scene

```bash
# 1. Make some changes first
service: button.press
target:
  entity_id: button.adaptive_lighting_pro_brighter

service: button.press
target:
  entity_id: button.adaptive_lighting_pro_scene_evening_comfort

# 2. Now press AUTO
service: button.press
target:
  entity_id: button.adaptive_lighting_pro_scene_auto

# 3. Verify reset
sensor.adaptive_lighting_pro_alp_brightness_adjustment  # Should be 0
sensor.adaptive_lighting_pro_alp_warmth_adjustment     # Should be 0
select.adaptive_lighting_pro_scene                      # Should be "auto"

# 4. Check AL switches cleared manual_control
switch.adaptive_lighting_main_living
# Check attributes.manual_control: should be EMPTY list []
```

### Step 7: Test Reset Button

```bash
# 1. Make changes
# Press brightness/warmth buttons
# Apply a scene

# 2. Press Reset
service: button.press
target:
  entity_id: button.adaptive_lighting_pro_reset

# 3. Verify everything cleared
select.adaptive_lighting_pro_scene           # Should be "auto"
number.adaptive_lighting_pro_brightness_adjustment  # Should be 0
number.adaptive_lighting_pro_warmth_adjustment     # Should be 0
```

### Step 8: Test Options Flow

```bash
# 1. Go to Settings → Integrations → Adaptive Lighting Pro → Configure

# 2. Change settings:
# - Brightness Increment: Change to 10
# - Lux Sensor: Change to different sensor (if available)

# 3. Save and reload integration

# 4. Verify changes persisted:
number.adaptive_lighting_pro_brightness_increment  # Should be 10
sensor.adaptive_lighting_pro_alp_environmental_boost
# Check attributes.current_lux from new sensor
```

## If Button Press Still Fails (500 Error)

The issue is likely in the config_entry.data structure. Need to verify:

### Check 1: Zone Configuration Structure

```python
# Developer Tools → Template
{{ state_attr('sensor.adaptive_lighting_pro_alp_zone_health', 'zones').keys() | list }}
# Expected: ['recessed_ceiling', 'kitchen_island', 'bedroom_primary', 'accent_spots', 'main_living']
```

### Check 2: Global Settings Loaded

```python
# Check if YAML values loaded (brightness_increment should be 5, not 20)
{{ states('number.adaptive_lighting_pro_brightness_increment') }}
# From YAML: should be 5
# From defaults: would be 20

# If it's 20, YAML import failed or fell back to defaults
```

### Check 3: Integration Source

```bash
# Settings → Integrations → Adaptive Lighting Pro
# Check title: Should say "(YAML)" if imported from YAML
```

## If YAML Import Failed

Signs:
- Brightness increment is 20 (not 5 from YAML)
- Integration title doesn't say "(YAML)"
- Environmental boost still shows current_lux: null

**Fix**:
1. Delete integration completely from UI
2. Restart Home Assistant
3. YAML import should run automatically on startup
4. Check logs for "Importing Adaptive Lighting Pro configuration from YAML"
5. If no import message, check configuration.yaml has:
   ```yaml
   adaptive_lighting_pro: !include adaptive_lighting_pro_zones.yaml
   ```

## Success Criteria

All of these must be true:

✅ Environmental boost shows current_lux with real value
✅ All 3 health sensors show available (not unavailable)
✅ Scene AUTO button exists and works
✅ Pressing Brighter creates 5 manual control timers
✅ Timer status shows active_zones with 5 zones
✅ Individual zone sensors show timer_remaining > 0
✅ AUTO scene clears all manual control and adjustments
✅ Reset button returns to AUTO scene
✅ Options flow accepts changes and persists them
✅ Brightness increment is 5 (from YAML) not 20 (default)

## If All Tests Pass

You're ready for production! The integration is fully functional with:
- Environmental boost working
- Manual control timers working
- Scene system working
- AUTO scene working
- Reset working
- Options flow working

## If Any Test Fails

Provide these for debugging:
1. Full error from logs (Settings → System → Logs)
2. Output of template checks above
3. State of sensor.adaptive_lighting_pro_alp_status (full attributes)
4. Value of number.adaptive_lighting_pro_brightness_increment
