# Deployment Instructions - Adaptive Lighting Pro

## Overview

All code fixes are complete. This guide walks through deploying the integration to your Home Assistant instance.

## Prerequisites

- [ ] Home Assistant instance accessible
- [ ] File access to HA configuration directory (usually `/config/`)
- [ ] Developer Tools access in HA UI

## Deployment Steps

### Step 1: Deploy Custom Component Code

**Source**: `/home/mac/dev/HA/custom_components/adaptive_lighting_pro/`
**Destination**: Your HA instance at `/config/custom_components/adaptive_lighting_pro/`

**Files to deploy**:
```
custom_components/adaptive_lighting_pro/
├── __init__.py          ← Event listener for timer.finished
├── manifest.json
├── const.py
├── coordinator.py       ← AUTO scene and reset fixes
├── config_flow.py       ← YAML import and options flow fixes
├── services.py
├── button.py            ← AUTO scene button added
├── sensor.py            ← Performance sensor fixes
├── select.py
├── number.py
├── switch.py
├── entity.py
└── features/
    └── zone_manager.py  ← Timer start/cancel service calls
```

**How to deploy**:

**Option A - SSH/SCP** (if you have SSH access):
```bash
scp -r /home/mac/dev/HA/custom_components/adaptive_lighting_pro/ \
  user@homeassistant:/config/custom_components/
```

**Option B - Samba/File Share** (if using Samba add-on):
1. Connect to HA file share
2. Navigate to `/config/custom_components/`
3. Delete existing `adaptive_lighting_pro/` folder
4. Copy new `adaptive_lighting_pro/` folder

**Option C - Studio Code Server** (if using add-on):
1. Open Studio Code Server
2. Delete `/config/custom_components/adaptive_lighting_pro/`
3. Upload new folder

---

### Step 2: Deploy YAML Configuration

**Source**: `/home/mac/dev/HA/implementation_2.yaml`
**Destination**: Your HA instance (integration method varies)

**CRITICAL**: This file contains the timer entity definitions required for the integration to work.

**Timer definitions** (must be included):
```yaml
timer:
  alp_manual_recessed_ceiling:
    name: "ALP Timer: Recessed Ceiling"
    icon: mdi:timer-sand
    restore: true

  alp_manual_kitchen_island:
    name: "ALP Timer: Kitchen Island"
    icon: mdi:timer-sand
    restore: true

  alp_manual_bedroom_primary:
    name: "ALP Timer: Bedroom"
    icon: mdi:timer-sand
    restore: true

  alp_manual_accent_spots:
    name: "ALP Timer: Accent Spots"
    icon: mdi:timer-sand
    restore: true

  alp_manual_main_living:
    name: "ALP Timer: Main Living"
    icon: mdi:timer-sand
    restore: true
```

**Integration options**:

**Option A - Package** (recommended):
1. Copy `implementation_2.yaml` to `/config/packages/adaptive_lighting_pro.yaml`
2. Ensure `configuration.yaml` has:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

**Option B - Direct include**:
1. Copy `implementation_2.yaml` to `/config/adaptive_lighting_pro.yaml`
2. Add to `configuration.yaml`:
   ```yaml
   adaptive_lighting_pro: !include adaptive_lighting_pro.yaml
   ```

**Option C - Inline** (if you prefer):
1. Copy timer definitions directly into `configuration.yaml`
2. Copy other sections as needed

**Note**: The ALP integration itself is configured via UI (config flow), but the timer entities MUST be defined in YAML.

---

### Step 3: Validate YAML Configuration

**Before restarting**, validate your YAML:

1. Open Home Assistant UI
2. Navigate to: **Developer Tools → YAML**
3. Click: **"Check Configuration"**
4. Expected: ✅ **"Configuration valid!"**

**If invalid**:
- Check error message
- Verify timer syntax matches exactly
- Ensure no tab characters (use spaces only)
- Verify indentation (2 spaces per level)

---

### Step 4: Reload Timer Entities

**Create the timer entities** without full restart:

1. Navigate to: **Developer Tools → YAML**
2. Find section: **"Timer Entities"**
3. Click: **"Reload"**
4. Expected: Success message

**Verify timers created**:
1. Navigate to: **Developer Tools → States**
2. Search: `timer.alp_manual`
3. Expected: See 5 timer entities in "idle" state

**If timers don't appear**:
- Check YAML validation passed
- Verify timer definitions in correct location
- Check for duplicate entity_id conflicts
- Review logs for errors

---

### Step 5: Restart Home Assistant

**Load the custom component code**:

1. Navigate to: **Settings → System → Restart**
2. Click: **"Restart"**
3. Wait: 2-3 minutes for full restart
4. Expected: HA comes back online

**Alternative**:
- **Developer Tools → System → Restart Home Assistant**

---

### Step 6: Verify Integration Loaded

**Check integration status**:

1. Navigate to: **Settings → Devices & Services → Integrations**
2. Search: "Adaptive Lighting Pro"
3. Expected: Status shows **"OK"** or **"Loaded"**

**If status shows "Failed to load"**:
1. Click on the integration for details
2. Check error message
3. Navigate to: **Settings → System → Logs**
4. Filter: "adaptive_lighting_pro"
5. Look for Python errors or import failures

**Common load failures**:
- **Import error**: File not deployed correctly
- **Syntax error**: Python syntax issue (shouldn't happen - validated)
- **Dependency missing**: Check manifest.json requirements

---

### Step 7: Quick Smoke Test

**Verify basic functionality**:

**Test 1 - Entities exist**:
```
Developer Tools → States → Search "adaptive_lighting_pro"
Expected: See sensors, buttons, numbers, select
```

**Test 2 - Environmental boost active**:
```
Entity: sensor.adaptive_lighting_pro_environmental_boost
Attribute: current_lux (should NOT be null)
Expected: Real number like 123 or 456
```

**Test 3 - Performance sensor available**:
```
Entity: sensor.adaptive_lighting_pro_performance_metrics
State: "Active" or "Idle" (NOT "unavailable")
```

**Test 4 - AUTO scene button exists**:
```
Search: button.adaptive_lighting_pro_scene_auto
Expected: Entity exists
```

**Test 5 - Timer start on button press**:
```
1. Check: timer.alp_manual_main_living → state should be "idle"
2. Press: button.adaptive_lighting_pro_brighter
3. Check: timer.alp_manual_main_living → state should be "active"
4. Check: timer attributes → duration: 7200, remaining: ≈7199
```

---

## Post-Deployment Testing

See **[PRE_RESTART_VERIFICATION.md](PRE_RESTART_VERIFICATION.md)** for complete 11-test verification procedure.

Quick reference: **[RESTART_CHECKLIST.md](RESTART_CHECKLIST.md)**

---

## Configuration After Deployment

### Initial Setup (if fresh install)

The integration uses **config flow** for setup:

1. Navigate to: **Settings → Devices & Services → Integrations**
2. Click: **"+ Add Integration"**
3. Search: "Adaptive Lighting Pro"
4. Follow wizard to configure zones

### Reconfiguration (existing install)

The **options flow** now works properly:

1. Navigate to: **Settings → Devices & Services → Integrations**
2. Find: "Adaptive Lighting Pro"
3. Click: **"Configure"**
4. Available settings:
   - Brightness Increment (slider)
   - Color Temp Increment (number)
   - Manual Control Timeout (seconds)
   - **Lux Sensor** (entity selector) ← NEW
   - **Weather Entity** (entity selector) ← NEW

**Note**: Changes save immediately and integration reloads automatically.

---

## Rollback Plan (if needed)

If deployment fails:

### Rollback Custom Component
1. Delete `/config/custom_components/adaptive_lighting_pro/`
2. Restore previous version (if available)
3. Restart Home Assistant

### Rollback YAML
1. Remove timer entity definitions
2. Run YAML reload for Timer Entities
3. Check configuration validates

### Restore from Backup
Home Assistant automatic backups:
1. Settings → System → Backups
2. Find backup before deployment
3. Restore

---

## Troubleshooting

### Issue: Timer entities not created
**Symptom**: `timer.alp_manual_*` entities don't exist

**Diagnosis**:
```bash
# Check YAML validation
Developer Tools → YAML → Check Configuration

# Check timer reload
Developer Tools → YAML → Timer Entities → Reload
```

**Fix**:
- Verify timer definitions in YAML
- Check for syntax errors
- Ensure no duplicate entity_ids
- Review logs for timer platform errors

---

### Issue: Integration won't load
**Symptom**: "Failed to load" in Integrations page

**Diagnosis**:
```bash
# Check logs
Settings → System → Logs → Filter "adaptive_lighting_pro"

# Common errors:
# - "ModuleNotFoundError" → Files not deployed correctly
# - "SyntaxError" → Python syntax issue
# - "ImportError" → Missing dependency
```

**Fix**:
- Verify all files deployed to correct location
- Check file permissions (should be readable)
- Verify Python syntax: `python3 -m py_compile *.py`
- Check manifest.json requirements installed

---

### Issue: Environmental boost shows null
**Symptom**: `current_lux: null` in environmental boost sensor

**Diagnosis**:
```bash
# Check lux sensor configured
Settings → Devices & Services → Integrations
→ Adaptive Lighting Pro → Configure
→ Verify "Lux Sensor" is set

# Check sensor exists
Developer Tools → States → Search lux sensor entity_id
```

**Fix**:
- Reconfigure via options flow
- Set lux sensor to valid illuminance sensor
- Verify sensor provides numeric state
- Check YAML import restructuring worked

---

### Issue: Timers don't start when buttons pressed
**Symptom**: Button press works but timer stays "idle"

**Diagnosis**:
```bash
# Check logs after button press
Settings → System → Logs → Filter "timer"

# Look for:
# - "Failed to start HA timer" → Timer entity missing
# - "timer entity may not exist in YAML" → Name mismatch
```

**Fix**:
- Verify timer entity naming: `timer.alp_manual_{zone_id}`
- Check zone_id matches timer suffix
- Ensure timer entities exist and are "idle"
- Review zone_manager.py:308 timer entity format

---

### Issue: Timer expiry doesn't restore control
**Symptom**: Timer finishes but lights stay in manual mode

**Diagnosis**:
```bash
# Check logs when timer expires
Settings → System → Logs → Filter "Timer finished"

# Look for:
# - "Timer finished for zone X" → Event received
# - "Restoring adaptive control" → Restore called
# - "Failed to restore adaptive control" → Service call failed
```

**Fix**:
- Verify AL switch exists for zone
- Check AL switch entity_id format
- Ensure adaptive_lighting integration loaded
- Review __init__.py:256 event listener

---

## Success Criteria

✅ Custom component deployed
✅ YAML configuration validated
✅ Timer entities created (5 total)
✅ Home Assistant restarted
✅ Integration loaded successfully
✅ All entities available
✅ Environmental boost active (current_lux not null)
✅ Performance sensors available (not unavailable)
✅ AUTO scene button exists
✅ Button press starts timer
✅ Options flow works for reconfiguration

**Integration is production-ready!**

---

## Files Changed in This Deployment

### Code Files (11 changes)
1. `__init__.py:256-286` - Timer event listener
2. `coordinator.py:1555-1572` - AUTO scene restoration
3. `coordinator.py:1763` - Reset to AUTO scene
4. `config_flow.py:200-251` - YAML import restructuring
5. `config_flow.py:922-950` - Options flow nested save
6. `config_flow.py:962-1020` - Options flow schema with environmental
7. `sensor.py:807` - Performance sensor state
8. `sensor.py:816` - Performance sensor attributes
9. `button.py:68` - AUTO scene button added
10. `zone_manager.py:303-320` - Timer start service calls
11. `zone_manager.py:357-373` - Timer cancel service calls

### Configuration Files (1 addition)
1. `implementation_2.yaml:45-69` - Timer entity definitions

---

## Support

**Documentation**:
- [PRE_RESTART_VERIFICATION.md](PRE_RESTART_VERIFICATION.md) - Complete test suite
- [RESTART_CHECKLIST.md](RESTART_CHECKLIST.md) - Quick reference
- [TIMER_FIXES_COMPLETE.md](TIMER_FIXES_COMPLETE.md) - Timer implementation details

**Logs**:
- Settings → System → Logs
- Filter: "adaptive_lighting_pro"
- Filter: "timer"

**GitHub Issues**:
- https://github.com/adaptive-lighting-pro/adaptive-lighting-pro/issues

---

## Next Steps After Deployment

1. **Monitor in production** - Watch for unexpected behavior
2. **Test edge cases** - Multiple zones, rapid button presses, overlapping timers
3. **Test Sonos integration** - Wake sequence if configured
4. **Performance monitoring** - Coordinator update frequency and CPU usage
5. **User documentation** - Create setup guide for end users
6. **Consider automation** - Automated scene changes based on time/activity

**Deployment complete - enjoy your adaptive lighting! 🎉**
