# Sonos Alarm Sensor Fix - Complete Solution

## Problem Identified

**ALP Next Alarm Sensor shows "unknown"** but Sonos has valid alarm data.

**Root Causes**:
1. **Wrong sensor configured**: ALP was reading from broken sensor
2. **Wrong parsing logic**: Integration expected timestamp in **state**, but `sensor.sonos_upcoming_alarms` has timestamp in **attributes**

## Available Sonos Sensors

| Sensor | State | Timestamp Location | Status |
|--------|-------|-------------------|--------|
| `sensor.sonos_upcoming_alarms` | "2 upcoming alarm(s)." | `attributes.earliest_alarm_time` | ✅ Working |
| `sensor.sonos_alarms_for_tomorrow` | "1 alarm(s) scheduled for tomorrow." | `attributes.earliest_alarm_timestamp_tomorrow` | ✅ Working |
| `sensor.soonest_sonos_alarm_info` | "unknown" | N/A | ❌ Broken |

**Next alarm data** (from `sensor.sonos_upcoming_alarms`):
```yaml
earliest_alarm_time: "2025-10-07 04:31:00"
earliest_alarm_timestamp: 1759811460.0
friendly_names: ["Bath Daily alarm 22:31"]
rooms: ["Master Bedroom"]
```

## Fixes Applied

### Fix 1: Update Sonos Integration Parsing Logic

**File**: `custom_components/adaptive_lighting_pro/integrations/sonos.py`
**Lines**: 189-224

**What changed**: Added multi-format alarm parsing to support both attribute-based and state-based sensors.

**New parsing order**:
1. ✅ Try `attributes.earliest_alarm_time` (format: "2025-10-07 04:31:00")
2. ✅ Try `attributes.earliest_alarm_timestamp` (Unix timestamp: 1759811460.0)
3. ✅ Fall back to `state` (ISO format: "2025-10-07T04:31:00+00:00")

**Code**:
```python
# CRITICAL FIX: Try to parse from attributes first (sensor.sonos_upcoming_alarms format)
# Then fall back to state (simple timestamp sensor format)
alarm_time = None

# Try earliest_alarm_time from attributes (format: "2025-10-07 04:31:00")
if "earliest_alarm_time" in attributes:
    alarm_time = self._parse_alarm_time(attributes["earliest_alarm_time"])
    if alarm_time:
        _LOGGER.debug("Parsed alarm time from attributes.earliest_alarm_time: %s", alarm_time.isoformat())

# Try earliest_alarm_timestamp from attributes (Unix timestamp)
if not alarm_time and "earliest_alarm_timestamp" in attributes:
    try:
        timestamp = float(attributes["earliest_alarm_timestamp"])
        alarm_time = datetime.fromtimestamp(timestamp, tz=UTC)
        _LOGGER.debug("Parsed alarm time from attributes.earliest_alarm_timestamp: %s", alarm_time.isoformat())
    except (ValueError, TypeError) as err:
        _LOGGER.debug("Could not parse earliest_alarm_timestamp: %s", err)

# Fall back to parsing state directly (simple sensor format)
if not alarm_time:
    alarm_time = self._parse_alarm_time(state)
    if alarm_time:
        _LOGGER.debug("Parsed alarm time from state: %s", alarm_time.isoformat())
```

**Benefit**: Now supports **both** sensor formats - future-proof!

---

### Fix 2: Configure Sonos Sensor in YAML

**File**: `adaptive_lighting_pro_zones.yaml`
**Lines**: 32-34

**Added**:
```yaml
# Sonos integration (wake sequence alarm monitoring)
sonos_enabled: true
sonos_alarm_sensor: sensor.sonos_upcoming_alarms
```

**This will be imported** when ALP integration loads from YAML configuration.

---

## Deployment Steps

### Step 1: Reload ALP Integration

**Option A - Via UI** (recommended):
```
Settings → Devices & Services → Integrations
→ Adaptive Lighting Pro (YAML)
→ Click "..." menu → Reload
```

**Option B - Restart HA**:
```
Settings → System → Restart
```

---

### Step 2: Verify Configuration Loaded

Check if Sonos sensor is configured:

```
Settings → Devices & Services → Integrations
→ Adaptive Lighting Pro (YAML)
→ Click "Configure" (gear icon)
→ Look for Sonos fields (may not be exposed in options flow)
```

**Alternative**: Check logs after reload:
```
Settings → System → Logs
Filter: "Sonos integration configured"
Expected: "enabled=True, alarm_sensor=sensor.sonos_upcoming_alarms"
```

---

### Step 3: Verify Alarm Detection

Check ALP alarm sensors:

**1. Next Alarm Sensor**:
```
Entity: sensor.adaptive_lighting_pro_alp_next_alarm
Expected state: "2025-10-07T04:31:00+00:00" (or similar timestamp)
Expected attributes:
  target_zone: "bedroom_primary"
  alarm_detected: true
  wake_sequence_active: false (true when within wake window)
```

**2. Wake Start Time Sensor**:
```
Entity: sensor.adaptive_lighting_pro_alp_wake_start_time
Expected state: "2025-10-07T04:16:00+00:00" (alarm - 15 min)
```

**3. Wake Sequence Status**:
```
Entity: sensor.adaptive_lighting_pro_alp_wake_sequence_status
Expected state: "Scheduled for 04:16" or "Not Scheduled"
```

---

### Step 4: Check Logs for Parsing Success

```
Settings → System → Logs
Filter: "Parsed alarm time from attributes"

Expected entries:
- "Parsed alarm time from attributes.earliest_alarm_time: 2025-10-07T04:31:00+00:00"
  OR
- "Parsed alarm time from attributes.earliest_alarm_timestamp: 2025-10-07T04:31:00+00:00"
```

---

## Testing Wake Sequence

### Current Alarm Schedule

From `sensor.sonos_upcoming_alarms`:
- **Next alarm**: 2025-10-07 04:31:00 (Master Bedroom)
- **Wake sequence should start**: 04:16:00 (15 minutes before)
- **Target zone**: bedroom_primary

### Expected Behavior

**At 04:16:00** (15 min before alarm):
1. Wake sequence activates
2. `sensor.adaptive_lighting_pro_alp_wake_sequence_offset` increases gradually
3. Bedroom lights slowly brighten over 15 minutes
4. At 04:31:00, alarm triggers and lights at target brightness

### Manual Test (Immediate)

**Simulate upcoming alarm**:
1. Open Developer Tools → Services
2. Call service: `adaptive_lighting_pro.set_wake_alarm`
   ```yaml
   target:
     entity_id: switch.adaptive_lighting_pro_wake_sequence
   data:
     alarm_time: "{{ (now() + timedelta(minutes=2)).isoformat() }}"
     target_zone: bedroom_primary
   ```
3. Wait 2 minutes
4. Observe bedroom lights gradually brighten

---

## Troubleshooting

### Issue: ALP Next Alarm Still Shows "unknown"

**Check 1**: Verify integration reloaded
```bash
Settings → System → Logs
Search: "Sonos integration"
Expected: Recent log with correct sensor name
```

**Check 2**: Verify sensor entity exists
```bash
Developer Tools → States
Search: sensor.sonos_upcoming_alarms
Expected: State shows "2 upcoming alarm(s)."
```

**Check 3**: Check for errors
```bash
Settings → System → Logs
Filter: "sonos" or "alarm"
Look for: "Failed to parse alarm time" or similar errors
```

**Fix**: Restart HA to fully reload integration

---

### Issue: Parsing Logs Show Errors

**Symptom**: Logs show "Could not parse alarm time"

**Check attributes format**:
```bash
Developer Tools → States → sensor.sonos_upcoming_alarms
Check attributes contain:
  - earliest_alarm_time: "2025-10-07 04:31:00"
  - earliest_alarm_timestamp: 1759811460.0
```

**If missing**: Sonos sensor format changed, may need code update

---

### Issue: Wake Sequence Doesn't Trigger

**Check 1**: Wake sequence enabled
```bash
Entity: switch.adaptive_lighting_pro_wake_sequence
Expected: "on"
```

**Check 2**: Alarm time in future
```bash
Entity: sensor.adaptive_lighting_pro_alp_next_alarm
Expected: Timestamp > current time
```

**Check 3**: Wake window calculation
```bash
Entity: sensor.adaptive_lighting_pro_alp_wake_start_time
Expected: Alarm time - 15 minutes
```

**Check 4**: Target zone configured
```bash
Logs: Search "wake sequence"
Expected: "Wake sequence scheduled for zone: bedroom_primary"
```

---

## Architecture Overview

### Data Flow

```
Sonos Alarm (switch.sonos_alarm_945)
    ↓
Sonos Integration Script (creates sensor)
    ↓
sensor.sonos_upcoming_alarms
  State: "2 upcoming alarm(s)."
  Attributes:
    earliest_alarm_time: "2025-10-07 04:31:00"
    earliest_alarm_timestamp: 1759811460.0
    ↓
ALP Sonos Integration (integrations/sonos.py)
  - Monitors sensor state changes
  - Parses timestamp from attributes (NEW)
  - Calls wake_sequence.set_next_alarm()
    ↓
Wake Sequence Calculator (features/wake_sequence.py)
  - Calculates wake_start_time (alarm - 15 min)
  - Calculates offset ramp (0% → 20%)
  - Updates coordinator data
    ↓
ALP Sensors (sensor.py)
  - sensor.adaptive_lighting_pro_alp_next_alarm
  - sensor.adaptive_lighting_pro_alp_wake_start_time
  - sensor.adaptive_lighting_pro_alp_wake_sequence_offset
    ↓
Coordinator Update Cycle
  - Checks if current time in wake window
  - Applies wake offset to bedroom_primary zone
  - Gradually increases brightness
    ↓
Zone Lights Brighten
  - light.master_bedroom_table_lamps
  - light.master_bedroom_corner_accent
```

---

## Success Criteria

✅ ALP integration reload successful
✅ Sonos sensor configured: `sensor.sonos_upcoming_alarms`
✅ `sensor.adaptive_lighting_pro_alp_next_alarm` shows timestamp (not "unknown")
✅ `sensor.adaptive_lighting_pro_alp_wake_start_time` calculated correctly
✅ Logs show "Parsed alarm time from attributes.earliest_alarm_time"
✅ Wake sequence status shows "Scheduled for..." with correct time
✅ Wake sequence triggers 15 minutes before alarm
✅ Bedroom lights gradually brighten during wake window

---

## Files Modified

1. **custom_components/adaptive_lighting_pro/integrations/sonos.py** (lines 189-224)
   - Multi-format alarm parsing (attributes + state)

2. **adaptive_lighting_pro_zones.yaml** (lines 32-34)
   - Sonos sensor configuration

---

## Next Actions

1. **Reload ALP integration** or restart HA
2. **Verify alarm detection** via ALP sensors
3. **Check logs** for successful parsing
4. **Wait for wake window** to test automatic triggering
5. **Optional**: Manual test with `set_wake_alarm` service

**Expected outcome**: Wake sequence will automatically trigger 15 minutes before your 04:31 Sonos alarm tomorrow morning, gradually brightening bedroom lights from 04:16 to 04:31.
