# Restart Checklist - Quick Reference

## Before Restart

- [x] All code changes complete
- [x] Python syntax validated
- [x] Timer entities defined in implementation_2.yaml
- [x] Documentation created

## Restart Procedure

### 1. Check YAML Configuration
```
Developer Tools → YAML → Check Configuration
```
**Expected**: "Configuration valid!"

### 2. Reload Timer Entities
```
Developer Tools → YAML → Timer Entities → Reload
```
**Expected**: 5 timer entities created

### 3. Verify Timers Created
```
Developer Tools → States → Search "timer.alp_manual"
```
**Expected**: See 5 timers in "idle" state

### 4. Restart Home Assistant
```
Settings → System → Restart
```
**Wait**: ~2-3 minutes for full restart

### 5. Verify Integration Loaded
```
Settings → Devices & Services → Integrations
Look for: "Adaptive Lighting Pro (YAML)"
```
**Expected**: Status "OK" (not "Failed to load")

## Quick Test After Restart

### ✓ Environmental Boost Working
```bash
# Check lux sensor loaded
Entity: sensor.adaptive_lighting_pro_environmental_boost
Attribute: current_lux should have real value (NOT null)
```

### ✓ Sensors Available
```bash
# Check performance sensors
Entity: sensor.adaptive_lighting_pro_performance_metrics
State: "Active" or "Idle" (NOT "unavailable")
```

### ✓ AUTO Scene Button Exists
```bash
# Check scene buttons
Search: button.adaptive_lighting_pro_scene
Count: Should be 5 buttons (including AUTO)
```

### ✓ Timer Start on Button Press
```bash
# Press any adjustment button
1. Check timer.alp_manual_main_living state before: "idle"
2. Press button.adaptive_lighting_pro_brighter
3. Check timer state after: "active"
4. Check timer attributes: duration=7200, remaining≈7199
```

### ✓ Options Flow Works
```bash
# Reconfigure integration
Settings → Devices & Services → Integrations
→ Adaptive Lighting Pro (YAML) → Configure
Should see: Lux Sensor and Weather Entity selectors
```

## If Something Fails

### Check Logs
```
Settings → System → Logs
Filter: "adaptive_lighting_pro"
```

### Common Issues

**Timer entities don't exist**
→ implementation_2.yaml not loaded
→ Run YAML reload for Timer entities

**Integration failed to load**
→ Check logs for Python errors
→ Verify all files have correct syntax

**Environmental boost null**
→ YAML config not restructured properly
→ Check config_flow.py import logic

**Timers don't start**
→ Timer entity IDs don't match zone IDs
→ Verify naming: timer.alp_manual_{zone_id}

## Full Test Suite

See [PRE_RESTART_VERIFICATION.md](PRE_RESTART_VERIFICATION.md) for complete 11-test verification procedure.

## Success = All Green

- ✅ Timers exist
- ✅ Integration loaded
- ✅ Environmental boost active
- ✅ Sensors available
- ✅ AUTO button exists
- ✅ Timer starts on button press
- ✅ Options flow works

**Ready for production use!**
