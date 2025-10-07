# Pre-Restart Verification & Action Plan

## Current Status (2025-10-06)

All code fixes from the production issue list have been completed. The integration is currently **NOT loaded** in Home Assistant, so all entities are missing.

## Verification Checklist ✓

### Code Changes Complete

- [x] **Environmental boost fix** - YAML import restructuring (config_flow.py:200-251)
- [x] **Unavailable sensors fix** - Coordinator attribute correction (sensor.py:807,816)
- [x] **AUTO scene button** - Added to button platform (button.py:68)
- [x] **AUTO scene restoration** - Calls AL services (coordinator.py:1555-1572)
- [x] **Reset to AUTO** - Default scene fixed (coordinator.py:1763)
- [x] **Options flow nested structure** - Proper save/load (config_flow.py:922-950)
- [x] **Options flow schema** - Environmental sensors added (config_flow.py:1003-1020)
- [x] **Timer entity definitions** - 5 timers in YAML (implementation_2.yaml:45-69)
- [x] **Timer start service calls** - ZoneManager calls timer.start (zone_manager.py:303-320)
- [x] **Timer cancel service calls** - ZoneManager calls timer.cancel (zone_manager.py:357-373)
- [x] **Timer event listener** - Handles timer.finished events (__init__.py:256-286)

### YAML Configuration Ready

- [x] Timer entities defined in implementation_2.yaml (lines 45-69)
  - timer.alp_manual_recessed_ceiling
  - timer.alp_manual_kitchen_island
  - timer.alp_manual_bedroom_primary
  - timer.alp_manual_accent_spots
  - timer.alp_manual_main_living

### Python Syntax Validated

All files compile without syntax errors:
```bash
python3 -m py_compile custom_components/adaptive_lighting_pro/*.py
python3 -m py_compile custom_components/adaptive_lighting_pro/platforms/*.py
python3 -m py_compile custom_components/adaptive_lighting_pro/features/*.py
```

## Required Actions

### Step 1: Reload YAML Configuration
**WHY**: Create the 5 timer entities defined in implementation_2.yaml

**HOW**:
- Developer Tools → YAML → Check Configuration
- Developer Tools → YAML → Reload: Timer Entities

**EXPECTED RESULT**: 5 new timer entities appear:
- timer.alp_manual_recessed_ceiling
- timer.alp_manual_kitchen_island
- timer.alp_manual_bedroom_primary
- timer.alp_manual_accent_spots
- timer.alp_manual_main_living

### Step 2: Restart Home Assistant
**WHY**: Load all code changes in custom_components/adaptive_lighting_pro/

**HOW**:
- Developer Tools → System → Restart Home Assistant
- OR Settings → System → Restart

**EXPECTED RESULT**: ALP integration loads and creates all entities

### Step 3: Verify Integration Loaded
**WHY**: Confirm no startup errors

**CHECK**:
- Settings → Devices & Services → Integrations
- Look for "Adaptive Lighting Pro (YAML)"
- Status should be "OK" not "Failed to load"

**IF FAILED**:
- Check logs: Settings → System → Logs
- Look for "adaptive_lighting_pro" errors
- Check YAML syntax in implementation_2.yaml

## Post-Restart Testing Sequence

### Test 1: Timer Entities Exist
**Goal**: Verify all 5 timer entities were created

**Steps**:
1. Developer Tools → States
2. Search for "timer.alp_manual"
3. Should see 5 entities

**Expected State**: All timers in "idle" state

**Files**: implementation_2.yaml:45-69

---

### Test 2: ALP Entities Created
**Goal**: Verify integration loaded successfully

**Steps**:
1. Developer Tools → States
2. Search for "adaptive_lighting_pro"
3. Count entities

**Expected Entities**:
- Sensors (environmental boost, performance, health, manual control per zone, etc.)
- Buttons (brighter, dimmer, warmer, cooler, reset, scene buttons)
- Numbers (brightness adjustment, warmth adjustment, timeouts)
- Select (current scene)

**Files**: sensor.py, button.py, number.py, select.py

---

### Test 3: Environmental Boost Active
**Goal**: Verify lux_sensor loaded from YAML config

**Steps**:
1. Find environmental boost sensor: `sensor.adaptive_lighting_pro_environmental_boost`
2. Check attributes

**Expected Attributes**:
```yaml
current_lux: 123  # Real value, NOT null
lux_sensor: sensor.living_room_presence_light_sensor_light_level
weather_condition: rainy
environmental_multiplier: 1.XX
```

**Files**: config_flow.py:200-251 (YAML restructuring)

---

### Test 4: Performance Sensors Available
**Goal**: Verify coordinator attribute fixes

**Steps**:
1. Find performance metrics sensor
2. Check state

**Expected State**: "Active" or "Idle" (NOT "unavailable")

**Expected Attributes**:
```yaml
last_calculation: 2025-10-06T...  # ISO timestamp, NOT null
zones_managed: 5
```

**Files**: sensor.py:807,816

---

### Test 5: AUTO Scene Button Exists
**Goal**: Verify scene button added

**Steps**:
1. Developer Tools → States
2. Search for "button.adaptive_lighting_pro_scene"
3. Count scene buttons

**Expected Buttons**:
- button.adaptive_lighting_pro_scene_auto ← NEW
- button.adaptive_lighting_pro_scene_all_lights
- button.adaptive_lighting_pro_scene_no_spotlights
- button.adaptive_lighting_pro_scene_evening_comfort
- button.adaptive_lighting_pro_scene_ultra_dim

**Files**: button.py:68

---

### Test 6: Button Press Starts Timer
**Goal**: Verify timer.start service called

**Steps**:
1. Developer Tools → States
2. Find timer: timer.alp_manual_main_living
3. Note state: "idle"
4. Press button: button.adaptive_lighting_pro_brighter
5. Immediately check timer state

**Expected State**: "active"
**Expected Attributes**:
```yaml
duration: 7200  # 2 hours default
remaining: 7199
```

**Expected Logs**:
```
INFO: Started HA timer entity: timer.alp_manual_main_living for 7200s
```

**Files**: zone_manager.py:303-320

---

### Test 7: Timer Expiry Restores Control
**Goal**: Verify timer.finished event triggers restoration

**THIS TEST TAKES 2 HOURS - SKIP IN INITIAL VERIFICATION**

**Alternative Quick Test**:
1. Press button to start timer
2. Developer Tools → Services
3. Call service: timer.cancel
   - entity_id: timer.alp_manual_main_living
4. Check logs immediately

**Expected Logs**:
```
INFO: Timer finished for zone main_living, restoring adaptive control
INFO: Restoring adaptive control for zone: main_living
INFO: Clearing manual control for zone main_living
```

**Expected AL Service Calls**:
- adaptive_lighting.set_manual_control (manual_control: false)

**Files**: __init__.py:256-286

---

### Test 8: AUTO Scene Restores All Zones
**Goal**: Verify AUTO scene calls _restore_adaptive_control for all zones

**Steps**:
1. Press any scene button (e.g., "Ultra Dim")
2. Verify current_scene sensor shows "ultra_dim"
3. Press "Auto" scene button
4. Check logs

**Expected Logs**:
```
INFO: Restoring adaptive control for zone: recessed_ceiling
INFO: Restoring adaptive control for zone: kitchen_island
INFO: Restoring adaptive control for zone: bedroom_primary
INFO: Restoring adaptive control for zone: accent_spots
INFO: Restoring adaptive control for zone: main_living
```

**Expected State**:
- current_scene sensor: "auto"
- brightness_adjustment: 0
- warmth_adjustment: 0

**Files**: coordinator.py:1555-1572

---

### Test 9: Reset Button Returns to AUTO
**Goal**: Verify reset sets scene to AUTO (not DEFAULT)

**Steps**:
1. Set any scene (e.g., "All Lights")
2. Set brightness adjustment to 10
3. Press "Reset" button
4. Check current_scene sensor

**Expected State**:
- current_scene: "auto" ← NOT "default"
- brightness_adjustment: 0
- warmth_adjustment: 0

**Files**: coordinator.py:1763

---

### Test 10: Options Flow Reconfiguration
**Goal**: Verify can reconfigure integration after setup

**Steps**:
1. Settings → Devices & Services → Integrations
2. Find "Adaptive Lighting Pro (YAML)"
3. Click "Configure"
4. Should see form with:
   - Brightness Increment (slider)
   - Color Temp Increment (box)
   - Manual Control Timeout (box)
   - Lux Sensor (entity selector) ← NEW
   - Weather Entity (entity selector) ← NEW

**Test Changes**:
1. Change Brightness Increment to 10
2. Change Lux Sensor to different sensor
3. Click "Submit"

**Expected Result**:
- Configuration saves successfully
- Integration reloads
- New values reflected in entity attributes

**Files**: config_flow.py:922-950, 962-1020

---

### Test 11: Manual Control Tracking
**Goal**: Understand dual tracking system (not a bug)

**Expected Behavior**:

**Adaptive Lighting Manual Control** (base AL integration):
- Tracks: Lights manually changed outside AL
- Sensor: switch.adaptive_lighting_main_living (attributes)
- Set by: AL detecting unexpected light state
- Cleared by: AL service call or timeout

**ALP Manual Control** (our integration):
- Tracks: ALP button press timers active
- Sensor: sensor.adaptive_lighting_pro_manual_control_main_living
- Set by: Button press starting timer
- Cleared by: Timer expiry or AUTO scene

**These are INDEPENDENT systems and may show different states** - this is correct.

---

## Known Non-Issues

### Issue: AL vs ALP Manual Control Mismatch
**NOT A BUG** - These are two separate tracking systems:
- AL tracks lights manually changed
- ALP tracks button adjustment timers
- They can disagree and that's correct behavior

---

## If Tests Fail

### Environmental Boost Shows null
**Symptoms**: current_lux: null

**Diagnosis**:
1. Check YAML import loaded: Developer Tools → States → search integration entities
2. Check logs for "Failed to restructure YAML config"

**Fix**: Restart integration or check YAML syntax

---

### Timers Don't Start
**Symptoms**: Button press doesn't change timer state

**Diagnosis**:
1. Check timer entities exist: Developer Tools → States
2. Check logs for "Failed to start HA timer"

**Fix**: Verify timer entity IDs match zone IDs

---

### Timer Expiry Doesn't Restore
**Symptoms**: Timer finishes but lights stay manual

**Diagnosis**:
1. Check logs for "Timer finished for zone"
2. Check logs for AL service call errors

**Fix**: Verify AL switch entity exists for zone

---

## Success Criteria

✅ All 5 timer entities exist
✅ ALP integration loads without errors
✅ Environmental boost shows real lux values (not null)
✅ Performance sensors show "Active" (not unavailable)
✅ AUTO scene button exists
✅ Button press starts timer entity
✅ Timer expiry restores adaptive control
✅ AUTO scene restores all zones
✅ Reset returns to AUTO scene
✅ Options flow allows reconfiguration

---

## Next Steps After Successful Tests

1. **Monitor production usage** - Watch for edge cases
2. **Test Sonos wake sequence** - Separate feature to verify
3. **Test complex scenarios** - Multiple overlapping adjustments
4. **Performance monitoring** - Check coordinator update frequency
5. **User documentation** - Create setup guide

---

## Quick Reference: Zone → Timer Mapping

| Zone ID | Timer Entity |
|---------|--------------|
| recessed_ceiling | timer.alp_manual_recessed_ceiling |
| kitchen_island | timer.alp_manual_kitchen_island |
| bedroom_primary | timer.alp_manual_bedroom_primary |
| accent_spots | timer.alp_manual_accent_spots |
| main_living | timer.alp_manual_main_living |

**Format**: `timer.alp_manual_{zone_id}`

**Used in**:
- zone_manager.py:308 (start)
- zone_manager.py:362 (cancel)
- __init__.py:266 (event listener)
