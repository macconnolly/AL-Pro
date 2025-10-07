# CRITICAL: Button 500 Error - Timer Creation Failure

## Problem Statement

Buttons throw HTTP 500 error when pressed, preventing manual control timers from being created.

## Evidence

1. **Buttons show last press times** but no timers created
2. **Manual timer status sensor** shows "No Active Timers" at all times
3. **Manual control sensors** all show "No manual control" and timer_remaining=0
4. **HTTP 500 error** when calling button.press via API

## Root Cause Analysis

### What SHOULD Happen (Expected Flow)

```
User presses Brighter button
  ↓
ALPBrighterButton.async_press()
  ↓
coordinator.set_brightness_adjustment(value, start_timers=True)
  ↓
FOR EACH zone_id in coordinator.zones:
    coordinator.start_manual_timer(zone_id, skip_refresh=True)
      ↓
      coordinator._mark_zone_lights_as_manual(zone_id)
        → Calls adaptive_lighting.set_manual_control with manual_control=True
      ↓
      zone_manager.async_start_manual_timer(zone_id, ...)
        → Sets state.manual_control_active = True
        → Sets state.timer_expiry = now + timedelta(seconds=7200)
        → Persists state to hass.data
      ↓
coordinator.async_request_refresh()
  → Updates all sensor entities
```

### What's ACTUALLY Happening

**500 error** means an unhandled exception is being raised somewhere in this chain.

## Possible Failure Points

### 1. Zone Iteration Issue (Most Likely)

**Hypothesis**: `coordinator.zones` structure doesn't match what's expected.

**Check in coordinator.__init__**:
```python
zones_config = config_entry.data.get("zones", [])
for zone in zones_config:
    zone_id = zone.get("id", zone.get("zone_id", ""))  # <-- CRITICAL
    if zone_id:
        self.zones[zone_id] = zone
```

**Potential Problem**: YAML zones use `"zone_id"` but UI zones might use `"id"`. The fallback should handle this, but what if both are missing?

**Test**:
```python
# In Developer Tools → Template
{{ state_attr('sensor.adaptive_lighting_pro_alp_zone_health', 'zones').keys() }}
# Should show: ['recessed_ceiling', 'kitchen_island', 'bedroom_primary', 'accent_spots', 'main_living']
```

### 2. Zone Configuration Missing Required Field

**Hypothesis**: Zone config missing `adaptive_lighting_switch` or `lights` field.

**Check**: Zone health sensor shows all zones have these fields correctly.

**Status**: ✅ NOT THE ISSUE (zone health shows all fields present)

### 3. ZoneManager Initialization Failure

**Hypothesis**: ZoneManager's `_zone_states` dict not properly initialized for all zones.

**Check in zone_manager.__init__**:
```python
zones_config = config_entry.data.get(CONF_ZONES, [])  # <-- Uses CONF_ZONES constant
for zone_config in zones_config:
    zone_id = zone_config["zone_id"]  # <-- Direct access, will KeyError if missing!
    self._zone_states[zone_id] = ZoneState(zone_id=zone_id)
```

**Potential Problem**: If YAML restructuring uses `"id"` instead of `"zone_id"`, this will KeyError!

### 4. Global Settings Not in Nested Structure

**Hypothesis**: `config_entry.data` doesn't have `global_settings{}` nested dict.

**Evidence**:
- `number.brightness_increment` shows `20.0` (not the YAML value of `5`)
- This suggests it's using DEFAULT values, not loaded values

**Check what coordinator actually loads**:
```python
global_settings = config_entry.data.get("global_settings", {})
self._brightness_increment = global_settings.get(
    CONF_BRIGHTNESS_INCREMENT, DEFAULT_BRIGHTNESS_INCREMENT
)
```

If `global_settings` is empty dict, it falls back to `DEFAULT_BRIGHTNESS_INCREMENT = 20`.

## THE SMOKING GUN

**The brightness increment is 20, not 5 from YAML.**

This means one of two things:
1. YAML config didn't import at all (still using old UI config)
2. YAML import happened but `global_settings` structure is wrong

## Diagnostic Commands to Run

### 1. Check if YAML import created a config entry

```bash
# In Developer Tools → States
# Search for: adaptive_lighting_pro
# Check: How many config entries exist?
```

### 2. Check Home Assistant logs for import

```bash
grep "Importing Adaptive Lighting Pro" home-assistant.log
grep "YAML config restructured" home-assistant.log
grep "ERROR.*adaptive_lighting_pro" home-assistant.log
```

### 3. Check for exceptions during button press

```bash
# Press Brighter button
# Immediately check logs:
grep -A 20 "Exception\|Traceback\|ERROR" home-assistant.log | tail -50
```

### 4. Check zone_manager initialization

```bash
grep "ZoneManager initialized" home-assistant.log
# Should show: ZoneManager initialized with 5 zones: [...]
```

### 5. Verify zone_id field name in config

Via hass-mcp or Developer Tools, check:
```python
{{ state_attr('sensor.adaptive_lighting_pro_alp_status', 'managed_zones') }}
```

## FIX REQUIRED

Based on analysis, the issue is likely in `async_step_import()` zone handling:

**Current YAML format**:
```yaml
zones:
  - zone_id: "recessed_ceiling"  # <-- Uses "zone_id"
    adaptive_lighting_switch: ...
```

**What coordinator.__init__ expects**:
```python
zone_id = zone.get("id", zone.get("zone_id", ""))  # Checks "id" FIRST, "zone_id" second
```

**What zone_manager.__init__ expects**:
```python
zone_id = zone_config["zone_id"]  # Direct access to "zone_id"
```

**CONFLICT**: If YAML uses `"zone_id"` but something renamed it to `"id"` during import, zone_manager will crash!

## Recommended Fix

Need to ensure YAML import preserves exact field names:

```python
# In async_step_import():
restructured_data = {
    CONF_NAME: "Adaptive Lighting Pro (YAML)",
    CONF_ZONES: import_data.get(CONF_ZONES, []),  # <-- Pass zones AS-IS, don't transform
    "global_settings": global_settings,
    "environmental": environmental_settings,
    "integrations": integration_settings,
}
```

But verify each zone dict has `"zone_id"` field (not `"id"`).

## Immediate Next Steps

1. **Restart Home Assistant** to apply all code fixes
2. **Check logs** for import messages and errors
3. **Delete integration** completely
4. **Remove adaptive_lighting_pro from configuration.yaml** temporarily
5. **Restart again** (clean slate)
6. **Re-add YAML config** to configuration.yaml
7. **Restart** and watch logs during import
8. **Test button press** and capture any errors

## If Still Failing After Restart

The user should provide:
1. Full exception traceback from logs when pressing button
2. Output of: `{{ state_attr('sensor.adaptive_lighting_pro_alp_zone_health', 'zones') }}`
3. Confirmation of how many ALP config entries exist in Integrations UI
4. Value of `number.adaptive_lighting_pro_brightness_increment` (should be 5 from YAML, not 20)
