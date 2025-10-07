# CRITICAL FIX: AL Manual Control → ALP Timer Bridge

## Issue Discovered

**User reported**: AL switch shows `manual_control: ["light.kitchen_island_pendants"]` but ALP timer is NOT running.

**Root Cause**: Missing automation to bridge AL's manual detection with ALP's timer system.

## How Implementation 1 Worked

Implementation 1 had an automation that:
1. **Triggered** when AL switch's `manual_control` attribute changed
2. **Checked** if the list was not empty (manual control active)
3. **Started** the corresponding zone timer
4. **Used** the timeout value from user config

## The Missing Piece

Our implementation 2 had:
- ✅ Timer entities defined
- ✅ Integration code to start timers when **buttons** pressed
- ✅ Event listener for `timer.finished` to restore control
- ❌ **NO automation to start timers when AL detects manual control**

This meant:
- **Button presses** → Timer starts ✅
- **Physical light changes** → AL detects it, but timer NEVER starts ❌

## Fix Applied

**File**: `implementation_2.yaml`
**Lines**: 1017-1064

**Added automation**:

```yaml
automation:
  - id: alp_manual_override_triggered
    alias: "ALP - Per-Zone Manual Override Handler"
    description: "Start zone-specific timer when AL detects manual control"
    mode: queued
    max: 10
    trigger:
      # Monitor when manual_control attribute changes on any AL switch
      - platform: state
        entity_id:
          - switch.adaptive_lighting_main_living
          - switch.adaptive_lighting_kitchen_island
          - switch.adaptive_lighting_bedroom_primary
          - switch.adaptive_lighting_accent_spots
          - switch.adaptive_lighting_recessed_ceiling
        attribute: manual_control
    condition:
      # Only proceed if manual control list is not empty
      - condition: template
        value_template: >
          {% set manual = trigger.to_state.attributes.manual_control | default([]) %}
          {{ manual is iterable and manual is not string and manual | length > 0 }}
    variables:
      # Map AL switch to its ALP timer
      timer_map:
        switch.adaptive_lighting_main_living: timer.alp_manual_main_living
        switch.adaptive_lighting_kitchen_island: timer.alp_manual_kitchen_island
        switch.adaptive_lighting_bedroom_primary: timer.alp_manual_bedroom_primary
        switch.adaptive_lighting_accent_spots: timer.alp_manual_accent_spots
        switch.adaptive_lighting_recessed_ceiling: timer.alp_manual_recessed_ceiling
      zone_timer: "{{ timer_map.get(trigger.entity_id, 'timer.alp_manual_main_living') }}"
      # Get timeout from ALP integration config (default 2 hours = 7200 seconds)
      timeout_seconds: "{{ states('number.adaptive_lighting_pro_manual_control_timeout') | int(7200) }}"
    action:
      # Start the zone-specific timer
      - service: timer.start
        target:
          entity_id: "{{ zone_timer }}"
        data:
          duration: "{{ timeout_seconds }}"

      # Log for debugging
      - service: system_log.write
        data:
          message: >
            ALP: Manual control detected on {{ trigger.entity_id }}
            Lights: {{ trigger.to_state.attributes.manual_control | default([]) | join(', ') }}
            Starting timer: {{ zone_timer }} for {{ timeout_seconds }}s
          level: info
```

## How It Works

### Trigger Flow:

1. **Physical Change**: User manually adjusts kitchen island light
2. **AL Detects**: Base AL integration marks it as manually controlled
3. **Attribute Update**: `switch.adaptive_lighting_kitchen_island.manual_control` changes to `["light.kitchen_island_pendants"]`
4. **Automation Triggers**: Our new automation detects the attribute change
5. **Condition Check**: Verifies the manual_control list is not empty
6. **Timer Start**: Calls `timer.start` on `timer.alp_manual_kitchen_island`
7. **Timer Runs**: Timer counts down for configured duration (default 2 hours)
8. **Timer Expires**: `timer.finished` event fires
9. **Control Restored**: Integration's event listener calls `_restore_adaptive_control()`
10. **AL Cleared**: Calls `adaptive_lighting.set_manual_control` with `manual_control: false`

### Key Features:

- **Uses ALP config**: Reads timeout from `number.adaptive_lighting_pro_manual_control_timeout`
- **Zone mapping**: Automatically maps AL switch to correct ALP timer
- **Logging**: Writes to system log for debugging
- **Queued mode**: Handles multiple rapid changes gracefully
- **Condition check**: Only triggers if manual_control list has items

## Deployment Steps

### Step 1: Reload Automation Configuration

**Option A - YAML Reload** (no restart needed):
```
Developer Tools → YAML → Automations → Reload
```

**Option B - Restart HA** (if reload doesn't work):
```
Settings → System → Restart
```

### Step 2: Verify Automation Loaded

```
Settings → Automations & Scenes
Search: "ALP - Per-Zone Manual Override Handler"
Expected: Automation exists and is enabled
```

### Step 3: Test the Flow

**Test Scenario**: Manually adjust kitchen island light

1. **Check initial state**:
   ```
   timer.alp_manual_kitchen_island → "idle"
   switch.adaptive_lighting_kitchen_island.manual_control → []
   ```

2. **Manually adjust light**:
   - Use physical switch, HomeKit, or HA UI
   - Change brightness or color temp
   - Wait 5-10 seconds for AL to detect

3. **Verify AL detection**:
   ```
   switch.adaptive_lighting_kitchen_island.manual_control → ["light.kitchen_island_pendants"]
   ```

4. **Verify timer started**:
   ```
   timer.alp_manual_kitchen_island → "active"
   timer attributes:
     duration: "2:00:00" (7200 seconds)
     remaining: ~7199
   ```

5. **Check logs**:
   ```
   Settings → System → Logs
   Filter: "ALP: Manual control detected"
   Expected: Log entry showing timer start
   ```

### Step 4: Verify Timer Expiry (Optional Long Test)

**Quick test** (cancel timer):
```
Developer Tools → Services
Service: timer.cancel
Entity: timer.alp_manual_kitchen_island
```

**Expected**:
- Timer state → "idle"
- AL manual_control → [] (cleared)
- Lights resume adaptive behavior

## Two-Way Integration Complete

### Before This Fix:

```
ALP Buttons → ALP Timer → Control Restored ✅
Physical Change → AL Detection → ❌ NOTHING
```

### After This Fix:

```
ALP Buttons → ALP Timer → Control Restored ✅
Physical Change → AL Detection → ALP Timer → Control Restored ✅
```

## Architecture

This completes the three-part timer system:

1. **Timer Entities** (implementation_2.yaml:45-69)
   - 5 timer entities, one per zone
   - Persistent across restarts

2. **Button-Triggered Timers** (zone_manager.py:303-320)
   - ZoneManager calls `timer.start` when buttons pressed
   - Uses configured timeout value

3. **AL-Triggered Timers** (implementation_2.yaml:1017-1064) ← **NEW**
   - Automation monitors AL switches
   - Starts timer when AL detects manual control

4. **Timer Expiry Handler** (__init__.py:256-286)
   - Listens for `timer.finished` events
   - Restores adaptive control via coordinator

## Why This Matters

**Without this automation**:
- User manually adjusts light with physical switch
- AL detects it and marks as manual_control
- **Timer never starts**
- Manual control stays active FOREVER
- User has to manually clear it or restart AL

**With this automation**:
- User manually adjusts light with physical switch
- AL detects it and marks as manual_control
- **Automation starts timer**
- Timer expires after 2 hours (configurable)
- Control automatically restored
- Lights resume adaptive behavior

## Current Status

| Component | Status |
|-----------|--------|
| Timer entities | ✅ Created |
| Button-triggered timers | ✅ Working |
| AL-triggered timers | ✅ **JUST ADDED** |
| Timer expiry handler | ✅ Working |
| Integration loaded | ✅ Active |

## Next Action

**User needs to**:
1. Reload automation configuration (or restart HA)
2. Test by manually adjusting kitchen island light
3. Verify timer starts automatically
4. Confirm timer expiry restores control

**Expected outcome**: Kitchen island light manual control will now trigger the ALP timer, which will expire after 2 hours and restore adaptive control automatically.
