# Adaptive Lighting Pro - Production Fixes Summary

## Critical Fixes Applied

### 1. YAML Configuration Not Loading (Environmental Boost Broken)
**Issue**: `lux_sensor` and other YAML configs not loading, causing environmental boost to show `current_lux: null`

**Root Cause**: YAML import was passing flat structure, but coordinator expected nested structure:
- YAML: `{"lux_sensor": "...", "zones": [...]}`
- Expected: `{"environmental": {"lux_sensor": "..."}, "zones": [...]}`

**Fix**: [config_flow.py:177-251](config_flow.py#L177-251)
Restructured YAML import to match UI config flow format:
```python
restructured_data = {
    CONF_NAME: "Adaptive Lighting Pro (YAML)",
    CONF_ZONES: import_data.get(CONF_ZONES, []),
    "global_settings": global_settings,
    "environmental": environmental_settings,
    "integrations": integration_settings,
}
```

**Testing**:
1. Restart Home Assistant
2. Check sensor.adaptive_lighting_pro_alp_environmental_boost attributes
3. Verify `current_lux` is no longer null

---

### 2. Three Sensors Unavailable
**Issue**: Performance Metrics, Health Status, System Health sensors showing "unavailable" with restored=true

**Root Cause**: PerformanceMetricsSensor referenced `coordinator.last_updated` which doesn't exist. Correct attribute is `coordinator.last_update_success_time`

**Fix**: [sensor.py:807-816](sensor.py#L807-816)
```python
# Before:
return "Active" if self.coordinator.last_updated else "Idle"
"last_calculation": self.coordinator.last_updated,

# After:
return "Active" if self.coordinator.last_update_success_time else "Idle"
"last_calculation": self.coordinator.last_update_success_time.isoformat() if self.coordinator.last_update_success_time else None,
```

**Testing**:
1. Restart HA
2. Verify all three sensors show proper state (not "unavailable")

---

### 3. Scene AUTO Button Missing
**Issue**: Select dropdown had "auto" option but no button to press it

**Fix**: [button.py:66-73](button.py#L66-73)
Added Scene.AUTO to scene buttons list:
```python
scene_buttons = [
    (Scene.AUTO, "Auto", "mdi:auto-fix"),  # <-- ADDED
    (Scene.ALL_LIGHTS, "All Lights", "mdi:lightbulb-group"),
    ...
]
```

**Testing**:
1. Reload integration or restart HA
2. Verify button.adaptive_lighting_pro_scene_auto exists
3. Press it and verify scene changes to "auto"

---

### 4. AUTO Scene Doesn't Actually Reset
**Issue**: Pressing AUTO scene button didn't restore adaptive control

**Root Cause**: AUTO scene handler called `_clear_zone_manual_control()` which doesn't call AL services, instead of `_restore_adaptive_control()` which does

**Fix**: [coordinator.py:1554-1572](coordinator.py#L1554-1572)
```python
# Before:
for zone_id in list(self.zones.keys()):
    self._clear_zone_manual_control(zone_id)

# After:
for zone_id in list(self.zones.keys()):
    await self._restore_adaptive_control(zone_id)  # Properly calls AL services
```

**Testing**:
1. Press brightness/warmth buttons to make changes
2. Press AUTO scene button
3. Verify:
   - Brightness adjustment = 0
   - Warmth adjustment = 0
   - Scene = "auto"
   - AL manual_control flags cleared
   - Lights return to adaptive behavior

---

### 5. Reset Button Doesn't Return to AUTO Scene
**Issue**: Reset button cleared adjustments but left scene as whatever it was

**Root Cause**: `clear_scene_offsets()` set scene to `Scene.DEFAULT` instead of `Scene.AUTO`

**Fix**: [coordinator.py:1752-1764](coordinator.py#L1752-1764)
```python
# Before:
self._current_scene = Scene.DEFAULT

# After:
self._current_scene = Scene.AUTO
```

**Testing**:
1. Apply a scene (e.g., Evening Comfort)
2. Make brightness/warmth adjustments
3. Press Reset button
4. Verify:
   - Scene returns to "auto"
   - All adjustments = 0
   - Lights return to adaptive

---

### 6. Options Flow Not Working
**Issue**: Couldn't reconfigure integration after initial setup

**Root Cause**: Options flow did shallow merge `{**config_entry.data, **user_input}` which doesn't work with nested structure

**Fix**: [config_flow.py:922-955](config_flow.py#L922-955)
Properly route flat user_input keys to nested dicts:
```python
global_settings = current_data.get("global_settings", {}).copy()
global_settings[CONF_BRIGHTNESS_INCREMENT] = user_input.get(CONF_BRIGHTNESS_INCREMENT)
...
current_data["global_settings"] = global_settings

environmental = current_data.get("environmental", {}).copy()
environmental[CONF_LUX_SENSOR] = user_input.get(CONF_LUX_SENSOR)
...
current_data["environmental"] = environmental
```

**Testing**:
1. Go to Settings → Integrations → ALP → Configure
2. Change brightness increment
3. Change lux sensor
4. Save
5. Verify changes persist after reload

---

## Manual Control Tracking Investigation

**User Report**: AL shows 6 lights in manual_control, but ALP shows manual_control_active=false

**Analysis**:
These are TWO SEPARATE tracking systems:
- **AL's manual_control**: Lights that AL detected were manually changed (via physical switch, app, etc)
- **ALP's manual_control_active**: Whether ALP's manual control TIMER is active

**Expected Behavior**:
1. User presses ALP buttons → ALP starts timers + sets AL manual_control=True
2. After timeout (default 2 hours) → ALP timers expire → ALP calls AL set_manual_control=False
3. User manually changes lights (outside ALP) → AL detects and sets manual_control=True (ALP timers still inactive)

**Current State from hass-mcp**:
- Buttons were pressed at ~23:00-23:08
- Checked at ~23:18 (only 10-18 minutes later)
- Default timeout is 7200 seconds (2 hours)
- **Timers should still be active!**

**Possible Causes**:
1. Timers never started (bug in zone iteration or zone ID mismatch)
2. Timers were manually cancelled
3. Zone manager state not persisting correctly

**Testing Required**:
1. Delete integration completely
2. Re-add from scratch (force fresh state)
3. Press Brighter button
4. Check sensor.adaptive_lighting_pro_*_manual_control immediately
5. Verify timer_remaining_seconds > 0
6. Verify manual_control_active = true

---

## Recommended Testing Sequence

### Complete Integration Test:
```bash
# 1. Remove old integration
# Settings → Integrations → ALP → Delete

# 2. Restart HA to clear all state
# Settings → System → Restart

# 3. Re-add integration
# Settings → Integrations → Add → Adaptive Lighting Pro
# OR let YAML import run

# 4. Test Environmental Boost
# Check sensor.adaptive_lighting_pro_alp_environmental_boost
# Verify current_lux is populated

# 5. Test Manual Control Timers
# Press button.adaptive_lighting_pro_brighter
# Immediately check sensor.adaptive_lighting_pro_main_living_manual_control
# Verify: manual_control_active=true, timer_remaining > 7000

# 6. Test AUTO Scene
# Press button.adaptive_lighting_pro_scene_auto
# Verify: scene="auto", brightness=0, warmth=0

# 7. Test Reset
# Make changes, then press button.adaptive_lighting_pro_reset
# Verify: scene="auto", all adjustments=0

# 8. Test Options Flow
# Settings → Integrations → ALP → Configure
# Change brightness_increment to 10
# Save → Reload
# Verify number.adaptive_lighting_pro_brightness_increment = 10
```

---

## Files Modified

1. [config_flow.py](config_flow.py) - YAML restructuring, options flow nested update
2. [sensor.py](sensor.py) - last_update_success_time fix
3. [button.py](button.py) - Added AUTO scene button
4. [coordinator.py](coordinator.py) - AUTO scene handler, clear_scene_offsets fix

## Next Steps

1. **User must restart Home Assistant** to apply fixes
2. **Delete and re-add integration** recommended for clean slate
3. Test manual control timer persistence
4. Verify all sensors online
5. Test complete automation flow
