# CRITICAL: Missing Timer Entities

## Problem

The integration uses internal datetime-based state tracking in ZoneManager, but the **original YAML implementation used actual HA timer entities**. This is why buttons aren't creating visible timers.

## Evidence from implementation_1.yaml

```yaml
timer:
  adaptive_lighting_manual_timer_main_living:
    name: "AL Manual Timer - Main Living"
    icon: mdi:timer
  adaptive_lighting_manual_timer_kitchen_island:
    name: "AL Manual Timer - Kitchen Island"
    icon: mdi:timer
  # ... etc for all 5 zones
```

These were referenced throughout automations:
- `service: timer.start` to start timers
- `service: timer.cancel` to cancel timers
- `event: timer.finished` triggers to restore adaptive control
- Template sensors to show remaining time

## Current Integration Approach (Wrong)

**ZoneManager** tracks timers internally:
- `state.manual_control_active = True`
- `state.timer_expiry = now + timedelta(seconds=7200)`
- Polls in coordinator update cycle to check if expired

**Problems**:
1. No visible timer entities in UI
2. No timer.finished events
3. Can't use timer services (timer.start, timer.cancel, timer.pause)
4. Polling-based expiry check (not event-driven)
5. User can't see timer countdown in UI

## Solution Options

### Option 1: Require User to Add Timers to configuration.yaml (Quick Fix)

Add to adaptive_lighting_pro_zones.yaml or configuration.yaml:

```yaml
timer:
  alp_manual_recessed_ceiling:
    name: "ALP Manual Timer - Recessed Ceiling"
    icon: mdi:timer
    restore: true
  alp_manual_kitchen_island:
    name: "ALP Manual Timer - Kitchen Island"
    icon: mdi:timer
    restore: true
  alp_manual_bedroom_primary:
    name: "ALP Manual Timer - Bedroom Primary"
    icon: mdi:timer
    restore: true
  alp_manual_accent_spots:
    name: "ALP Manual Timer - Accent Spots"
    icon: mdi:timer
    restore: true
  alp_manual_main_living:
    name: "ALP Manual Timer - Main Living"
    icon: mdi:timer
    restore: true
```

Then update ZoneManager to:
1. Call `timer.start` service instead of setting internal state
2. Listen for `timer.finished` events to restore adaptive control
3. Remove polling-based expiry checking

**Pros**: Matches original implementation, visible timers, event-driven
**Cons**: Requires manual YAML config (not pure integration)

### Option 2: Create Custom Timer Entities in Integration (Better)

Home Assistant doesn't have a `Platform.TIMER`, but we can create timer-like entities using **sensors with countdown attributes**.

Create `ALPManualTimerSensor` entities that:
- Show remaining time as state (formatted: "1:45:23")
- Have attributes: `duration`, `finishes_at`, `active`
- Update every second via `async_track_time_interval`
- Fire custom event when timer expires

**Pros**: Pure integration, no YAML required, visible in UI
**Cons**: Not "real" HA timers, can't use timer.* services

### Option 3: Use Number Entities with Automation (Hybrid)

Create number entities for each zone representing seconds remaining:
- `number.alp_manual_timer_main_living` (0-14400 seconds)
- User or automation can see/modify remaining time
- Coordinator counts down every update cycle
- Fires event at zero

**Pros**: Configurable via UI, visible countdown
**Cons**: Still not real timers, manual countdown logic

## Recommended Approach: Option 1 (Use Real Timers)

**Why**: Matches original implementation exactly, uses HA's built-in timer functionality, event-driven, most robust.

### Implementation Steps

1. **Add timer definitions to adaptive_lighting_pro_zones.yaml**

2. **Update ZoneManager.async_start_manual_timer()**:
```python
async def async_start_manual_timer(self, zone_id, duration=None, ...):
    # Calculate duration (existing logic)

    # Start HA timer entity
    timer_entity = f"timer.alp_manual_{zone_id}"
    await self.hass.services.async_call(
        "timer",
        "start",
        {
            "entity_id": timer_entity,
            "duration": duration,
        },
    )

    # Update internal state for tracking
    state = self._zone_states[zone_id]
    state.manual_control_active = True
    state.timer_expiry = now + timedelta(seconds=duration)
    ...
```

3. **Add timer.finished event listener in __init__.py**:
```python
async def async_setup_entry(hass, entry):
    ...

    # Listen for timer.finished events
    async def handle_timer_finished(event):
        timer_id = event.data.get("entity_id")
        if not timer_id or not timer_id.startswith("timer.alp_manual_"):
            return

        zone_id = timer_id.replace("timer.alp_manual_", "")
        await coordinator._restore_adaptive_control(zone_id)

    entry.async_on_unload(
        hass.bus.async_listen("timer.finished", handle_timer_finished)
    )
```

4. **Update coordinator to call timer.cancel**:
```python
async def _restore_adaptive_control(self, zone_id):
    # Cancel HA timer
    timer_entity = f"timer.alp_manual_{zone_id}"
    try:
        await self.hass.services.async_call(
            "timer",
            "cancel",
            {"entity_id": timer_entity},
        )
    except Exception:
        pass  # Timer might already be finished

    # Rest of existing logic...
```

5. **Remove polling-based expiry check from coordinator update**

## User Action Required

Add this to configuration.yaml or adaptive_lighting_pro_zones.yaml:

```yaml
# ALP Manual Control Timers (Required)
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

Then code changes above will make buttons work correctly.
