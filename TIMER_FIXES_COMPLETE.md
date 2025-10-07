# Timer Implementation - COMPLETE

## Problem Solved

The integration was using internal datetime-based state tracking instead of actual Home Assistant timer entities. This caused:
- No visible timers in UI
- Manual control sensors always showing "No manual control"
- Buttons appeared to work but nothing happened
- No automatic restoration of adaptive control after timeout

## Solution Applied

### 1. Timer Entity Definitions in implementation_2.yaml

Added actual HA timer entities that the integration will control:

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

### 2. ZoneManager Starts Real Timers

**File**: [features/zone_manager.py:303-320](custom_components/adaptive_lighting_pro/features/zone_manager.py#L303-320)

When buttons are pressed, ZoneManager now:
1. Sets internal state (for tracking)
2. **Calls timer.start service** on actual HA timer entity

```python
# CRITICAL FIX: Start actual HA timer entity
timer_entity = f"timer.alp_manual_{zone_id}"
try:
    await self.hass.services.async_call(
        "timer",
        "start",
        {
            "entity_id": timer_entity,
            "duration": duration,
        },
    )
    _LOGGER.info("Started HA timer entity: %s for %ds", timer_entity, duration)
except Exception as err:
    _LOGGER.error(
        "Failed to start HA timer %s: %s (timer entity may not exist in YAML)",
        timer_entity,
        err,
    )
```

### 3. ZoneManager Cancels Real Timers

**File**: [features/zone_manager.py:357-373](custom_components/adaptive_lighting_pro/features/zone_manager.py#L357-373)

When manual control is cancelled:
1. Clears internal state
2. **Calls timer.cancel service** on HA timer entity

```python
# CRITICAL FIX: Cancel actual HA timer entity
timer_entity = f"timer.alp_manual_{zone_id}"
try:
    await self.hass.services.async_call(
        "timer",
        "cancel",
        {
            "entity_id": timer_entity,
        },
    )
    _LOGGER.info("Cancelled HA timer entity: %s", timer_entity)
except Exception as err:
    _LOGGER.debug(
        "Could not cancel HA timer %s: %s (may already be finished)",
        timer_entity,
        err,
    )
```

### 4. Event-Driven Timer Expiry

**File**: [__init__.py:256-286](custom_components/adaptive_lighting_pro/__init__.py#L256-286)

Integration now listens for `timer.finished` events:

```python
async def handle_timer_finished(event):
    """Handle timer.finished event to restore adaptive control for a zone."""
    timer_id = event.data.get("entity_id", "")

    # Only handle our ALP manual control timers
    if not timer_id.startswith("timer.alp_manual_"):
        return

    # Extract zone_id from timer entity_id
    zone_id = timer_id.replace("timer.alp_manual_", "")

    _LOGGER.info("Timer finished for zone %s, restoring adaptive control", zone_id)

    # Restore adaptive control via coordinator
    await coordinator._restore_adaptive_control(zone_id)

# Register event listener
entry.async_on_unload(
    hass.bus.async_listen("timer.finished", handle_timer_finished)
)
```

## Expected Behavior After Restart

### When Button Pressed:

1. User presses **button.adaptive_lighting_pro_brighter**
2. Coordinator calls `set_brightness_adjustment(value, start_timers=True)`
3. For each zone, coordinator calls `zone_manager.async_start_manual_timer()`
4. **ZoneManager starts 5 timer entities**:
   - `timer.alp_manual_recessed_ceiling` → 2:00:00
   - `timer.alp_manual_kitchen_island` → 2:00:00
   - `timer.alp_manual_bedroom_primary` → 2:00:00
   - `timer.alp_manual_accent_spots` → 2:00:00
   - `timer.alp_manual_main_living` → 2:00:00

5. **Visible in UI**: All 5 timer entities start counting down
6. **Manual control sensors update**:
   - `sensor.adaptive_lighting_pro_main_living_manual_control`
   - Attributes show: `manual_control_active: true`, `timer_remaining: 7200`

### After 2 Hours (Timer Expires):

1. HA fires `timer.finished` event for `timer.alp_manual_main_living`
2. Integration's event handler catches it
3. Calls `coordinator._restore_adaptive_control("main_living")`
4. Coordinator:
   - Calls `adaptive_lighting.set_manual_control` with `manual_control: false`
   - Calls `adaptive_lighting.apply` to restore AL values
   - If all timers expired, clears manual adjustments to 0

## Testing Steps

### 1. Restart Home Assistant

```bash
Settings → System → Restart Home Assistant
```

This loads:
- Timer entity definitions from implementation_2.yaml
- Updated code that uses those timers

### 2. Verify Timers Exist

```bash
# Developer Tools → States
# Search for: timer.alp_manual

# Should see 5 entities:
timer.alp_manual_recessed_ceiling  → idle
timer.alp_manual_kitchen_island    → idle
timer.alp_manual_bedroom_primary   → idle
timer.alp_manual_accent_spots      → idle
timer.alp_manual_main_living       → idle
```

### 3. Press Brighter Button

```bash
# Developer Tools → Services
service: button.press
data:
  entity_id: button.adaptive_lighting_pro_brighter
```

### 4. Verify Timers Started

```bash
# Immediately check timer entities
timer.alp_manual_main_living

# Should show:
# - state: active
# - duration: 0:02:00:00 (2 hours)
# - finishes_at: timestamp 2 hours from now
# - remaining: counting down from 7200 seconds
```

### 5. Verify Manual Control Sensors Updated

```bash
sensor.adaptive_lighting_pro_main_living_manual_control

# Attributes should show:
# - manual_control_active: true
# - timer_remaining_seconds: ~7200 (counting down)
# - timer_finishes_at: timestamp
```

### 6. Verify AL Switches Marked Manual

```bash
switch.adaptive_lighting_main_living

# Check attributes.manual_control should include all zone lights:
# - light.entryway_lamp
# - light.living_room_floor_lamp
# - etc.
```

### 7. Test Automatic Restoration (Optional - Quick Test)

```bash
# Manually finish a timer early
service: timer.finish
data:
  entity_id: timer.alp_manual_main_living

# Within seconds, check:
# 1. Timer state changes to idle
# 2. Manual control sensor shows manual_control_active: false
# 3. AL switch manual_control list is empty
```

## Success Criteria

✅ 5 timer entities exist and are idle before button press
✅ Press Brighter button succeeds (no 500 error)
✅ All 5 timer entities transition to "active" state
✅ Timers show countdown from 2:00:00 (7200 seconds)
✅ Manual control sensors show manual_control_active: true
✅ Manual control sensors show timer_remaining > 0
✅ AL switches show lights in manual_control list
✅ After timeout (or manual finish), timers return to idle
✅ After timeout, manual control sensors show manual_control_active: false
✅ After timeout, AL resumes controlling lights

## Files Modified

1. [implementation_2.yaml:45-69](implementation_2.yaml#L45-69) - Added timer entity definitions
2. [features/zone_manager.py:303-320](custom_components/adaptive_lighting_pro/features/zone_manager.py#L303-320) - Timer start
3. [features/zone_manager.py:357-373](custom_components/adaptive_lighting_pro/features/zone_manager.py#L357-373) - Timer cancel
4. [__init__.py:256-286](custom_components/adaptive_lighting_pro/__init__.py#L256-286) - Timer finished event listener

## This Completes the Fix For

- ❌ Buttons throwing 500 error → ✅ Should work now
- ❌ No timers visible → ✅ 5 timer entities visible
- ❌ Manual control always false → ✅ Updates when buttons pressed
- ❌ No automatic restoration → ✅ Event-driven via timer.finished
- ❌ Can't see countdown → ✅ Timer entities show remaining time
