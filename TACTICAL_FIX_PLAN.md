# TACTICAL FIX PLAN - Adaptive Lighting Pro Critical Issues

**Created**: 2025-10-05
**Status**: Research Phase - Deep Analysis Complete
**Principle**: API Layer FIRST, Consumer Layer SECOND (claude.md)

---

## UNDERSTANDING: How Adaptive Lighting `manual_control` Works

### Research from AL Integration Source Code

**Key Finding**: When a light has `manual_control=True`:
- AL integration **STOPS ADAPTING** that light completely
- `change_switch_settings` (what we call to update boundaries) **STILL WORKS** but AL won't use those boundaries to adapt lights
- The light stays at its current state until manual_control is cleared

**What This Means For Us**:
- When we call `change_switch_settings` to update min/max brightness, we're setting AL's boundaries
- But if `manual_control=True`, AL won't actually adapt the lights to those boundaries
- We need `manual_control=False` for AL to actively adapt lights within our new boundaries

**Critical Insight**:
- Our internal timers (`zone_manager.is_manual_control_active()`) track when USER made manual adjustment
- AL's `manual_control` flag tracks whether AL should adapt lights or leave them alone
- These are TWO DIFFERENT THINGS that must work together!

---

## ISSUE #1: Wake Sequence vs Manual Control

### Current Behavior (coordinator.py:349-367)

```python
wake_in_progress = (
    zone_config.get("wake_sequence_enabled", True)
    and self._wake_sequence.calculate_boost(zone_id) > 0
)

if wake_in_progress or not self.zone_manager.is_manual_control_active(zone_id):
    await self._apply_adjustments_to_zone(zone_id, zone_config)
```

### The Problem

**Scenario**: User touches bedroom lights at 5:55 AM (bathroom trip)
1. Our timer system marks zone as `manual_control_active=True`
2. At 6:15 AM, wake sequence starts (boost > 0)
3. Condition evaluates: `True (wake) or not True (manual)` = `True or False` = `True`
4. `_apply_adjustments_to_zone()` is called ✅
5. We calculate wake_boost = 20%, call `change_switch_settings(min_brightness=40)` ✅
6. **BUT**: AL integration still has `manual_control=True` from 5:55 AM adjustment!
7. **RESULT**: AL boundaries changed but AL won't adapt because manual_control blocks it ❌

### Root Cause

We call `_apply_adjustments_to_zone()` which updates AL boundaries, but we **never clear AL's manual_control flag** during wake sequence.

### The Fix

**Location**: coordinator.py:356-367

**What We Need**:
When wake sequence is active, we must tell AL "please adapt these lights again" by setting `manual_control=False`

```python
if wake_in_progress:
    # CRITICAL: Wake sequence must CLEAR manual control on AL switch
    # so AL will actively adapt lights to our wake boundaries
    al_switch = zone_config.get("adaptive_lighting_switch")
    if al_switch:
        await self.hass.services.async_call(
            ADAPTIVE_LIGHTING_DOMAIN,
            "set_manual_control",
            {
                "entity_id": al_switch,
                "manual_control": False,  # Clear manual - let AL adapt again
            },
            blocking=False,
        )

    await self._apply_adjustments_to_zone(zone_id, zone_config)
    _LOGGER.info(
        "Wake sequence active for zone %s - cleared manual control, applied wake boundaries",
        zone_id,
    )
elif not self.zone_manager.is_manual_control_active(zone_id):
    await self._apply_adjustments_to_zone(zone_id, zone_config)
else:
    _LOGGER.debug(
        "Skipping adjustment for zone %s (manual control active, no wake override)",
        zone_id,
    )
```

**Why This Is Correct**:
- Wake sequence is INTENTIONAL automation (not user manual control)
- We WANT AL to actively adapt lights during wake ramp
- Setting `manual_control=False` tells AL "resume adaptation" within our new boundaries
- This is the same as timer expiry - we restore AL control

---

## ISSUE #2: Button Press Manual Control Integration

### Current Behavior Flow

**Button Press** (platforms/button.py:136-171):
```python
await self.coordinator.set_brightness_adjustment(new_value, start_timers=True)
```

**Coordinator** (coordinator.py:1012-1022):
```python
if start_timers and old_value != value:
    for zone_id in self.zones:
        await self.start_manual_timer(zone_id, skip_refresh=True)
await self.async_request_refresh()
```

**start_manual_timer()** (coordinator.py:1304-1305):
```python
await self._mark_zone_lights_as_manual(zone_id)
```

**_mark_zone_lights_as_manual()** (coordinator.py:609-618):
```python
await self.hass.services.async_call(
    ADAPTIVE_LIGHTING_DOMAIN,
    "set_manual_control",
    {
        "entity_id": al_switch,
        "lights": lights,
        "manual_control": True,  # ✅ This IS correct!
    },
    blocking=False,
)
```

### The Problem (IF IT EXISTS)

**User's Claim**: "Buttons don't set manual control on AL switches"

**My Analysis**: The code DOES call `set_manual_control` with `manual_control=True`!

**Possible Issues**:
1. **Race Condition**: `blocking=False` means service returns immediately
   - `async_request_refresh()` might execute before `set_manual_control` completes
   - AL boundaries change but manual_control not yet set
   - AL sees new boundaries + no manual flag = adapts lights immediately
   - Then manual_control sets 0.1s later but damage done

2. **Service Call Order**: We set manual_control BEFORE changing boundaries
   - Line 1305: Call `_mark_zone_lights_as_manual()` (sets manual_control=True)
   - Line 1308: Call `zone_manager.async_start_manual_timer()` (internal timer)
   - Line 1022: Call `async_request_refresh()` (changes AL boundaries)

   This should be correct order - manual control first, then boundary change.

### Research Needed

**Questions**:
1. Does `blocking=False` actually cause a race condition in practice?
2. Is there a timing issue where AL sees boundary change before manual_control is set?
3. Do we need to use `await` without `blocking=False` (just remove the parameter)?

**Note**: In Home Assistant, `async_call(blocking=False)` returns immediately (fire-and-forget).
Without `blocking=False`, it's `blocking=True` by default and waits for service to complete.

### Potential Fix

**Location**: coordinator.py:609-618

**Change**: Remove `blocking=False` to ensure service completes before continuing

```python
await self.hass.services.async_call(
    ADAPTIVE_LIGHTING_DOMAIN,
    "set_manual_control",
    {
        "entity_id": al_switch,
        "lights": lights,
        "manual_control": True,
    },
    # NO blocking parameter = waits for completion
)
```

**Justification**:
- We MUST ensure manual_control is set before boundaries change
- 10-50ms delay to wait for service is acceptable (happens during timer start)
- Prevents race condition where AL sees new boundaries before manual flag

---

## ISSUE #3: Environmental Time Multiplier Logic

### Current Behavior (environmental.py:318-360)

```python
def _calculate_time_multiplier(self) -> float:
    # Try sun elevation first
    sun_state = self.hass.states.get("sun.sun")
    if sun_state:
        elevation = sun_state.attributes.get("elevation")
        if elevation is not None:
            elevation = float(elevation)
            if elevation < -6:
                return 0.0  # Night (civil twilight)
            elif -6 <= elevation < 0:
                return 0.7  # Dawn/dusk
            else:
                return 1.0  # Day

    # Fallback to clock time
    hour = datetime.now().hour
    if 22 <= hour or hour <= 6:
        return 0.0
    elif (6 < hour <= 8) or (18 <= hour < 22):
        return 0.7
    else:
        return 1.0
```

### The Problem

**Scenario**: December 21, 6:30 AM (winter solstice)
- Sun rises: 7:15 AM
- Current sun elevation: -8° (below horizon)
- Outdoor lux: 150 (very dark)
- Weather: Overcast
- Environmental boost calculation:
  - Lux factor: 20% (very low light)
  - Weather factor: 10% (overcast)
  - Season factor: 8% (winter)
  - **Time multiplier: 0.0** (sun below -6°)
  - **FINAL BOOST: 38% × 0.0 = 0%** ❌

**The User Is Absolutely Right**: This suppresses boost when user needs it MOST!

### Conceptual Confusion

**What time multiplier was SUPPOSED to do**:
- Suppress boost during SLEEP HOURS when user is in bed (don't need bright lights at 2 AM)

**What it ACTUALLY does**:
- Suppress boost when sun is low (dawn/dusk/night)
- But dark winter mornings (6-7 AM) are when environmental boost is MOST needed!

### The Fix

**Location**: environmental.py:318-360

**Concept**: Time multiplier should follow USER SCHEDULE (awake/asleep), not SUN POSITION (dark/light)

```python
def _calculate_time_multiplier(self) -> float:
    """Calculate time-of-day multiplier based on USER SCHEDULE.

    Purpose: Suppress boost during sleep hours when user doesn't need bright lights.
    NOT about sun position - dark mornings NEED boost!

    Sleep hours (22:00-05:00): 0.0 (user sleeping, suppress boost)
    Awake hours (05:00-22:00): 1.0 (full boost, INCLUDING dark mornings)

    Returns:
        Time multiplier (0.0 or 1.0)
    """
    hour = datetime.now().hour

    # Sleep hours: Suppress boost (user not awake)
    if 22 <= hour or hour < 5:
        return 0.0

    # Awake hours: Full boost (includes dark winter mornings!)
    else:
        return 1.0
```

**Justification**:
- At 2 AM: User sleeping, suppress boost (don't need 25% bright lights in bedroom)
- At 6:30 AM: User awake, allow full boost (dark winter morning needs compensation)
- Remove sun elevation logic entirely (conceptually wrong for time suppression)
- Remove 0.7x transition periods (simplify to binary: sleeping vs awake)

**Test Impact**:
- Test `test_dawn_should_reduce_but_not_eliminate_boost` will FAIL
- This test expects 0.7x multiplier at dawn
- Test is WRONG - must be updated to expect 1.0x at 6:30 AM

---

## ISSUE #4: Scene Application Zone Targeting

### User Request

"Fix scene application to only affect zones mentioned in actions"

### Current Behavior (coordinator.py:1368-1458)

```python
async def apply_scene(self, scene: Scene) -> bool:
    config = SCENE_CONFIGS[scene]

    # Execute scene actions (turn on/off specific lights)
    for action in config.get("actions", []):
        await self.hass.services.async_call(domain, service, action_copy, blocking=False)

    # Apply scene offsets
    self._scene_brightness_offset = config.get("brightness_offset", 0)
    self._scene_warmth_offset = config.get("warmth_offset", 0)

    # Update ALL zones immediately
    for zone_id, zone_config in self.zones.items():
        await self._apply_adjustments_to_zone(zone_id, zone_config)
```

### The Problem

**Scenario**: User applies "Evening Comfort" scene
- Scene actions turn on living room ceiling at 85%, turn off accent spots
- Scene offset: -15% brightness, -500K warmth
- **Current behavior**: Offset applied to ALL 5 zones!
  - Bedroom: Gets -15% offset (but no lights choreographed)
  - Kitchen: Gets -15% offset (but no lights choreographed)
  - Bathroom: Gets -15% offset (but no lights choreographed)

**User Expectation**: Scene should only affect zones whose lights are in the actions list

### Research Needed

**Questions**:
1. Should scene offsets be GLOBAL (all zones) or PER-ZONE (only choreographed zones)?
2. How do we determine which zones are "affected" by a scene?
   - Option A: Parse actions list, extract entity_ids, match to zones
   - Option B: Add explicit `zones: ["living_room", "bedroom"]` to SCENE_CONFIGS
   - Option C: Keep offsets global, let user control via zone-specific action lists

**Current Architecture**:
- `_scene_brightness_offset` and `_scene_warmth_offset` are GLOBAL coordinator state
- No per-zone scene offset tracking exists

### Potential Fix Approaches

**Option A: Per-Zone Scene Tracking** (COMPLEX)
- Change `_scene_brightness_offset` to dict: `_scene_offsets_by_zone: dict[str, tuple[int, int]]`
- Parse scene actions to determine affected zones
- Only apply offset to zones with lights in action entity_ids
- **Pros**: Precise zone targeting
- **Cons**: Complex parsing, fragile (relies on entity_id matching)

**Option B: Explicit Zone List in SCENE_CONFIGS** (MEDIUM)
- Add `zones: ["living_room", "bedroom"]` to each scene config
- Apply offset only to listed zones
- **Pros**: Explicit, clear, easy to understand
- **Cons**: User must manually specify zones (more config)

**Option C: Keep Global, Document Behavior** (SIMPLE)
- Scene offsets intentionally global (user can create zone-specific scenes if needed)
- Document: "Scene offsets affect all zones; use actions to choreograph specific lights"
- **Pros**: Simple, current behavior, no code change
- **Cons**: Might not match user expectation

### Recommended Approach

**Need User Clarification**: Which option matches user's mental model?

---

## ADDITIONAL ENHANCEMENTS (From User's List)

### 1. Quick Setup Config Flow

**User Request**: "Add optional Quick Setup flow that auto-detects AL switches"

**Implementation Plan**:
- **File**: config_flow.py
- **Location**: async_step_user() - before zone entry flow
- **Logic**:
  1. Detect all `switch.adaptive_lighting_*` entities in HA
  2. Offer choice: "Quick Setup (auto-configure from 5 detected switches)" vs "Manual Setup"
  3. If Quick Setup chosen:
     - Extract zone names from switch entity IDs (e.g., `switch.adaptive_lighting_bedroom` → `bedroom`)
     - Create default zone configs with sensible defaults
     - Show confirmation page: "Created 5 zones: bedroom, living_room, kitchen, office, bathroom. Continue to customize or finish?"
  4. User can still customize per-zone settings afterward (options flow)

**API Changes Needed**:
- None (pure config_flow enhancement)

**Estimated Effort**: 2-3 hours

---

### 2. Per-Zone Timeout Overrides

**User Request**: "Add number entities for per-zone timeout overrides"

**Current Behavior**: Global `manual_control_timeout` (5 min - 4 hours)

**Implementation Plan**:
- **API Layer** (coordinator.py):
  - Add `manual_timeout: int | None` to zone config schema
  - Add methods:
    - `get_zone_manual_timeout(zone_id: str) -> int`
    - `set_zone_manual_timeout(zone_id: str, timeout: int) -> None`
  - Update `start_manual_timer()` to check zone timeout first, fall back to global

- **Consumer Layer** (platforms/number.py):
  - Add `ALPZoneManualTimeoutNumber` class (5 entities, one per zone)
  - Use coordinator API methods

**Estimated Effort**: 2-3 hours

---

### 3. Sonos Convenience Features

**User Request**: "Add missing Sonos convenience features"

**Missing Features**:
- Wake sequence enable/disable switch
- Sunrise time sensor
- Wake start notification

**Implementation Plan**:
- **switch.alp_wake_sequence_enabled** (platforms/switch.py):
  - Coordinator method: `set_wake_sequence_enabled(bool)`
  - WakeSequenceCalculator checks enabled flag before calculating boost

- **sensor.alp_next_sunrise** (platforms/sensor.py):
  - Read from sun.sun entity, format as human-readable time

- **Notifications** (implementation_2.yaml Tier 2):
  - Automation: Trigger when wake sequence starts, send notification

**Estimated Effort**: 2-3 hours

---

### 4. implementation_2.yaml Notifications

**User Request**: "Add notifications and explore other notification opportunities"

**Opportunities**:
1. **Dark Day Alert**: Environmental boost > 20%
2. **Wake Sequence Started**: 15 min before alarm
3. **Manual Timer Expiring Soon**: 5 min warning
4. **Scene Changed**: User confirmation

**Implementation**: All in implementation_2.yaml Tier 2 (commented by default)

**Estimated Effort**: 1 hour

---

### 5. More Diagnostic Sensors

**User Request**: "Add more diagnostic sensors"

**Potential Additions**:
- `sensor.alp_last_action` - Last coordinator action with timestamp
- `sensor.alp_manual_timer_status` - Summary of all active timers
- `sensor.alp_zone_health_status` - Per-zone health check

**Estimated Effort**: 1-2 hours

---

## PRIORITY ORDER (Following claude.md)

### CRITICAL (Must Fix Before Deployment)
1. **Issue #1: Wake Sequence Manual Control** - Blocking core feature
2. **Issue #2: Button Press Race Condition** - Core UX broken if true
3. **Issue #3: Environmental Time Multiplier** - Logic backwards

### HIGH (Should Fix Soon)
4. **Issue #4: Scene Zone Targeting** - UX expectation mismatch
5. **Sonos Wake Disable Switch** - User explicitly requested from YAML parity

### MEDIUM (Nice to Have)
6. Quick Setup Config Flow
7. Per-Zone Timeout Overrides
8. Additional Diagnostic Sensors

### LOW (Enhancement)
9. implementation_2.yaml Notifications

---

## NEXT STEPS

1. **Get User Confirmation** on Issue #2 (is there really a race condition?)
2. **Get User Decision** on Issue #4 (which scene targeting approach?)
3. **Implement Fixes** in order:
   - API layer first (coordinator methods)
   - Consumer layer second (platforms)
   - Tests for each change
4. **Run Full Test Suite** after each fix
5. **Architectural Lint** (grep checks) before commit

**Ready to proceed with specific tactical implementation when user confirms analysis.**
