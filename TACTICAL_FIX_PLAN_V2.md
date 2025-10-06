# TACTICAL FIX PLAN V2 - Adaptive Lighting Pro Critical Issues
**COMPLETE REWRITE WITH CORRECT UNDERSTANDING**

**Created**: 2025-10-05
**Status**: Deep Research Complete - Ready for Implementation
**Principle**: API Layer FIRST, Consumer Layer SECOND (@claude.md)

---

## FUNDAMENTAL UNDERSTANDING: `manual_control` in Adaptive Lighting

### How AL Integration Actually Works

**When `manual_control=True` for lights**:
- AL integration **STOPS actively adapting** those lights
- Lights **stay at their current brightness/color**
- AL won't change them even if boundaries change
- This is HOW we lock lights at specific levels!

**When `manual_control=False` for lights**:
- AL integration **actively adapts** lights to current boundaries
- AL will adjust brightness/color to match its calculations
- Lights follow AL's natural sunrise/sunset curve

### Critical Insight for Our Integration

**We use `manual_control=True` in TWO scenarios**:

1. **User makes manual adjustment** (button press, slider drag)
   - Set `manual_control=True` to lock lights at user's chosen level
   - Start timer (30min-2hr)
   - When timer expires, set `manual_control=False` to restore AL control

2. **System creates choreographed state** (wake sequence, scenes)
   - Set lights to specific levels (wake ramp, ultra dim scene, etc.)
   - Set `manual_control=True` to LOCK those lights at that level
   - Prevents AL from fighting our intentional choreography!

**Example - Wake Sequence**:
- 6:15 AM: Wake starts, set brightness to 20% (Phase 1)
- Set `manual_control=True` → locks lights at 20%
- 6:20 AM: Progress to 50% (Phase 2)
- Still `manual_control=True` → locks at 50%
- Without manual_control=True, AL sees sunrise at 6:30 and would JUMP lights to 80%, destroying gradual wake!

**Example - Ultra Dim Scene**:
- User applies Ultra Dim scene
- Lights turn on at 5% brightness
- Set `manual_control=True` → locks lights at 5%
- Without manual_control=True, AL would immediately raise lights to its calculated value (like 40%), defeating the scene!

---

## 🔴 CRITICAL ISSUE #1: Wake Sequence Doesn't Set manual_control=True

### The Problem

**File**: coordinator.py:349-367

**Current Code**:
```python
wake_in_progress = (
    zone_config.get("wake_sequence_enabled", True)
    and self._wake_sequence.calculate_boost(zone_id) > 0
)

if wake_in_progress or not self.zone_manager.is_manual_control_active(zone_id):
    await self._apply_adjustments_to_zone(zone_id, zone_config)
```

**What Happens**:
1. Wake sequence calculates boost (20% → 50% → 90%)
2. `_apply_adjustments_to_zone()` changes AL boundaries
3. AL sees new boundaries
4. **AL immediately adapts lights to match boundaries** ❌
5. Result: Lights JUMP to AL's calculated value, destroying gradual wake ramp!

**What SHOULD Happen** (from implementation_1.yaml analysis):
1. Wake sequence starts
2. **Set `manual_control=True` for bedroom lights** ✅
3. Progressively update boundaries (creates the "target")
4. Wake sequence code manually changes light brightness over 15 minutes
5. Lights stay locked at wake sequence's set values
6. At wake end (6:30 AM), set `manual_control=False` to restore AL

### Root Cause

Wake sequence never calls `adaptive_lighting.set_manual_control` at all!

### The Fix

**Location**: coordinator.py:356 (inside wake_in_progress block)

**Required Changes**:

1. **When wake sequence STARTS** (first time boost > 0):
   ```python
   if wake_in_progress:
       # NEW: Set manual control to lock lights during wake progression
       al_switch = zone_config.get("adaptive_lighting_switch")
       lights = zone_config.get("lights", [])

       if al_switch and lights:
           await self.hass.services.async_call(
               ADAPTIVE_LIGHTING_DOMAIN,
               "set_manual_control",
               {
                   "entity_id": al_switch,
                   "lights": lights,
                   "manual_control": True,  # LOCK lights during wake
               },
               blocking=False,
           )

       await self._apply_adjustments_to_zone(zone_id, zone_config)
       _LOGGER.info(
           "Wake sequence active for zone %s - locked lights in manual mode",
           zone_id,
       )
   ```

2. **When wake sequence ENDS** (boost drops to 0):
   ```python
   # In WakeSequenceCalculator, need to detect when sequence completes
   # Then call coordinator method to clear manual_control

   # coordinator.py - new method:
   async def _clear_wake_manual_control(self, zone_id: str) -> None:
       """Clear manual control after wake sequence completes."""
       zone_config = self.zones.get(zone_id)
       if not zone_config:
           return

       al_switch = zone_config.get("adaptive_lighting_switch")
       lights = zone_config.get("lights", [])

       if al_switch and lights:
           await self.hass.services.async_call(
               ADAPTIVE_LIGHTING_DOMAIN,
               "set_manual_control",
               {
                   "entity_id": al_switch,
                   "lights": lights,
                   "manual_control": False,  # Restore AL control
               },
               blocking=False,
           )
           _LOGGER.info(
               "Wake sequence complete for zone %s - restored AL control",
               zone_id,
           )
   ```

**API Layer Changes Needed**:
- Add `_wake_in_progress: dict[str, bool]` to track which zones have active wake
- Add `_clear_wake_manual_control(zone_id)` method
- Detect transition from wake active → wake complete

---

## 🔴 CRITICAL ISSUE #2: Scene Application Doesn't Set manual_control=True

### The Problem

**File**: coordinator.py:1368-1458 (apply_scene method)

**Current Code**:
```python
async def apply_scene(self, scene: Scene) -> bool:
    config = SCENE_CONFIGS[scene]

    # Execute scene actions (turn lights on at specific brightness)
    for action in config.get("actions", []):
        await self.hass.services.async_call(domain, service, action_copy, blocking=False)

    # Apply scene offsets
    self._scene_brightness_offset = config.get("brightness_offset", 0)
    self._scene_warmth_offset = config.get("warmth_offset", 0)

    # Update zones
    for zone_id, zone_config in self.zones.items():
        await self._apply_adjustments_to_zone(zone_id, zone_config)
```

**What Happens**:
1. Scene actions turn lights on (e.g., Ultra Dim = 5% brightness)
2. Scene offsets applied (-70% offset)
3. AL boundaries updated
4. **AL immediately adapts lights back to its calculated value** ❌
5. Result: Ultra Dim scene lasts 0.1 seconds, then AL raises lights to 30%!

**What SHOULD Happen** (from implementation_1.yaml lines 3100-3200):
1. Scene actions turn lights on at specific levels
2. **Immediately set `manual_control=True` for those lights** ✅
3. Apply scene offsets
4. Lights STAY at scene's set levels because manual_control locks them
5. When scene cleared or timer expires, set `manual_control=False`

### Root Cause

Scene application never calls `adaptive_lighting.set_manual_control`!

### The Fix

**Location**: coordinator.py:1390-1395 (after scene actions, before offset application)

**Required Changes**:

1. **After executing scene actions, set manual_control=True**:
   ```python
   # Execute scene actions
   for action in config.get("actions", []):
       await self.hass.services.async_call(domain, service, action_copy, blocking=False)

   # NEW: Lock lights that were choreographed
   # Parse actions to find which lights were affected
   affected_lights_by_zone = self._extract_lights_from_scene_actions(config.get("actions", []))

   for zone_id, lights in affected_lights_by_zone.items():
       zone_config = self.zones.get(zone_id)
       if not zone_config:
           continue

       al_switch = zone_config.get("adaptive_lighting_switch")
       if al_switch and lights:
           await self.hass.services.async_call(
               ADAPTIVE_LIGHTING_DOMAIN,
               "set_manual_control",
               {
                   "entity_id": al_switch,
                   "lights": lights,
                   "manual_control": True,  # LOCK scene lights
               },
               blocking=False,
           )
           _LOGGER.debug(
               "Scene %s locked %d lights in zone %s",
               scene.value,
               len(lights),
               zone_id,
           )
   ```

2. **When clearing scene (ALL_LIGHTS), clear manual_control**:
   ```python
   if scene == Scene.ALL_LIGHTS:
       # Clear offsets
       self._scene_brightness_offset = 0
       self._scene_warmth_offset = 0

       # NEW: Restore AL control for all zones
       for zone_id, zone_config in self.zones.items():
           al_switch = zone_config.get("adaptive_lighting_switch")
           lights = zone_config.get("lights", [])

           if al_switch and lights:
               await self.hass.services.async_call(
                   ADAPTIVE_LIGHTING_DOMAIN,
                   "set_manual_control",
                   {
                       "entity_id": al_switch,
                       "lights": lights,
                       "manual_control": False,  # Restore AL
                   },
                   blocking=False,
               )
   ```

**API Layer Changes Needed**:
- Add `_extract_lights_from_scene_actions(actions)` helper method
- Track which zones/lights are under scene control
- Handle scene clearing properly

---

## 🔴 CRITICAL ISSUE #3: Button Press May Have Race Condition

### Current Behavior Analysis

**File**: coordinator.py:1012-1022, :582-620

**Current Flow**:
1. Button pressed → `coordinator.set_brightness_adjustment(+20, start_timers=True)`
2. Coordinator sets `self._brightness_adjustment = 20`
3. Coordinator calls `start_manual_timer(zone_id)` for each zone
4. Inside `start_manual_timer()`:
   - Calls `_mark_zone_lights_as_manual(zone_id)` (line 1305)
5. Inside `_mark_zone_lights_as_manual()`:
   - Calls `adaptive_lighting.set_manual_control` with `manual_control=True` (line 609-618)
   - Uses `blocking=False` ❓
6. Coordinator calls `async_request_refresh()` (line 1022)

**Potential Race Condition**:
```python
# Line 609-618: _mark_zone_lights_as_manual
await self.hass.services.async_call(
    ADAPTIVE_LIGHTING_DOMAIN,
    "set_manual_control",
    {
        "entity_id": al_switch,
        "lights": lights,
        "manual_control": True,
    },
    blocking=False,  # ⚠️ Returns immediately!
)

# Line 1022: set_brightness_adjustment
await self.async_request_refresh()  # ⚠️ Might execute before manual_control is set!
```

**If Race Condition Occurs**:
1. `set_manual_control` service called with `blocking=False` (returns immediately)
2. `async_request_refresh()` executes before service completes
3. AL boundaries updated but `manual_control` not yet set
4. AL sees new boundaries + no manual flag = **adapts lights immediately** ❌
5. 10ms later, `manual_control` sets but lights already adapted

### The Problem (IF IT EXISTS)

User presses +20% button:
- Expects: Lights get 20% brighter and STAY there for 30 minutes
- Reality: Lights might flicker brighter then back to AL value, THEN lock

### Verification Needed

**Question**: Does `blocking=False` actually cause this in practice?

**HA Service Call Documentation**:
- `blocking=False` (default): Service returns immediately, doesn't wait
- `blocking=True`: Wait for service to complete before returning

### The Fix (If Needed)

**Location**: coordinator.py:609-620

**Change**: Remove `blocking=False` to ensure service completes:
```python
await self.hass.services.async_call(
    ADAPTIVE_LIGHTING_DOMAIN,
    "set_manual_control",
    {
        "entity_id": al_switch,
        "lights": lights,
        "manual_control": True,
    },
    # NO blocking parameter = defaults to True = waits for completion
)
```

**OR use explicit blocking=True**:
```python
await self.hass.services.async_call(
    ADAPTIVE_LIGHTING_DOMAIN,
    "set_manual_control",
    {
        "entity_id": al_switch,
        "lights": lights,
        "manual_control": True,
    },
    blocking=True,  # ✅ Wait for manual_control to be set
)
```

**Justification**:
- MUST ensure `manual_control=True` is set BEFORE boundaries change
- 10-50ms delay acceptable (happens during timer start, before user notices)
- Prevents any possibility of race condition

**Status**: ❓ NEEDS USER CONFIRMATION - Is this actually broken in production?

---

## 🔴 CRITICAL ISSUE #4: Environmental Time Multiplier Backwards Logic

### The Problem

**File**: features/environmental.py:318-360

**Current Logic**:
```python
def _calculate_time_multiplier(self) -> float:
    # Uses sun elevation
    sun_state = self.hass.states.get("sun.sun")
    if sun_state:
        elevation = float(sun_state.attributes.get("elevation"))
        if elevation < -6:
            return 0.0  # Night - suppress boost
        elif -6 <= elevation < 0:
            return 0.7  # Dawn/dusk - reduce boost
        else:
            return 1.0  # Day - full boost

    # Fallback to clock
    hour = datetime.now().hour
    if 22 <= hour or hour <= 6:
        return 0.0  # Night - suppress boost
```

**Scenario - December 21, 6:30 AM**:
- Sun rises: 7:15 AM
- Current sun elevation: -8° (below horizon, still dark)
- Outdoor lux: 150 (very dark, foggy)
- Environmental boost calculation:
  - Lux factor: 20% (very dark)
  - Weather: 10% (overcast)
  - Season: 8% (winter)
  - Raw boost: 38%
  - **Time multiplier: 0.0** (sun < -6°)
  - **FINAL: 38% × 0.0 = 0%** ❌

**User Expectation**: Dark foggy winter morning at 6:30 AM should get MAXIMUM boost (38%), not ZERO!

### Conceptual Error

**What time multiplier was meant to do**: Suppress boost during SLEEP HOURS (2 AM when user is in bed, doesn't need lights)

**What it actually does**: Suppress boost when SUN IS LOW (dark mornings/evenings)

**Why this is backwards**: Dark mornings are EXACTLY when environmental boost is most needed!

### Root Cause

Confusion between:
- **Sun position** (dark/light) ← Environmental boost already handles this via lux
- **User schedule** (asleep/awake) ← What time multiplier should handle

### The Fix

**Location**: features/environmental.py:318-360

**Correct Logic**:
```python
def _calculate_time_multiplier(self) -> float:
    """Calculate time-of-day multiplier based on USER SCHEDULE (not sun position).

    Purpose: Suppress boost during SLEEP HOURS when user doesn't need bright lights.

    Dark mornings (6 AM, sun not yet risen) NEED full boost - that's what
    environmental boost is FOR! Time multiplier suppresses during sleep only.

    Sleep hours (22:00-05:00): 0.0 (user sleeping, no boost needed)
    Awake hours (05:00-22:00): 1.0 (full boost, INCLUDING dark mornings!)

    Returns:
        Time multiplier (0.0 or 1.0)
    """
    hour = datetime.now().hour

    # Sleep hours: Suppress boost (user not awake, doesn't benefit)
    if 22 <= hour or hour < 5:
        return 0.0

    # Awake hours: Full boost (includes dark winter mornings 5-8 AM!)
    else:
        return 1.0
```

**Key Changes**:
1. Remove ALL sun elevation logic (conceptually wrong)
2. Remove 0.7x transition periods (simplify to binary: sleep vs awake)
3. Change sleep window: `hour <= 6` → `hour < 5`
4. User wakes at 5 AM → gets full boost for dark mornings

**Test Impact**:
- `test_dawn_should_reduce_but_not_eliminate_boost` will FAIL
- Test expects 0.7x multiplier at dawn
- **Test is WRONG** - update to expect 1.0x at 6:30 AM

---

## 🟡 ISSUE #5: Scene Zone Targeting (User Expectation Mismatch)

### Current Behavior

**File**: coordinator.py:1421-1458

**Current Code**:
```python
# After setting scene offsets
for zone_id, zone_config in self.zones.items():
    await self._apply_adjustments_to_zone(zone_id, zone_config)
```

**What Happens**:
- Scene "Evening Comfort" applied
- Scene actions choreograph living room lights (turn on pendants, turn off ceiling)
- Scene offset: -15% brightness, -500K warmth
- **Offset applied to ALL 5 ZONES** (bedroom, kitchen, bathroom, office, living room)

**User Expectation**:
- Scene should only affect zones whose lights appear in scene actions
- Bedroom shouldn't get -15% offset if scene doesn't touch bedroom lights

### The Question

Should scene offsets be:
1. **GLOBAL** (current behavior) - All zones get offset
2. **ZONE-SPECIFIC** - Only zones with lights in actions get offset

### Implementation Options

**Option A: Keep Global (Simple)**
- Scene offsets affect all zones
- Document: "Use scene-specific action lists to control which lights choreograph"
- **Pros**: No code change, simple
- **Cons**: Might not match user expectation

**Option B: Parse Actions for Zone Targeting (Medium)**
- Extract entity_ids from scene actions
- Match entity_ids to zones
- Only apply offset to zones with choreographed lights
- **Pros**: Precise, matches user expectation
- **Cons**: Complex parsing, fragile

**Option C: Explicit Zone List in SCENE_CONFIGS (Best)**
- Add `zones: ["living_room", "bedroom"]` to each scene config
- Only apply offset to listed zones
- **Pros**: Explicit, clear, flexible
- **Cons**: More configuration

### Recommended Fix

**Use Option C** - Add explicit zone targeting to SCENE_CONFIGS:

**Location**: const.py:580-691 (SCENE_CONFIGS)

```python
SCENE_CONFIGS = {
    Scene.ALL_LIGHTS: {
        "name": "All Lights",
        "brightness_offset": 0,
        "warmth_offset": 0,
        "zones": ["living_room", "bedroom", "kitchen", "office", "bathroom"],  # All zones
        "actions": [...]
    },
    Scene.EVENING_COMFORT: {
        "name": "Evening Comfort",
        "brightness_offset": -15,
        "warmth_offset": -500,
        "zones": ["living_room", "kitchen"],  # Only these zones get offset
        "actions": [...]
    },
}
```

**Then in apply_scene()**:
```python
target_zones = config.get("zones", [])
for zone_id in target_zones:
    zone_config = self.zones.get(zone_id)
    if zone_config:
        await self._apply_adjustments_to_zone(zone_id, zone_config)
```

---

## 📋 ADDITIONAL ENHANCEMENTS

### 1. Quick Setup Config Flow

**User Request**: "Add optional Quick Setup that auto-detects AL switches"

**Implementation**:
- **File**: config_flow.py
- **Location**: async_step_user() - add choice step before manual zone entry

```python
async def async_step_user(self, user_input=None):
    # Detect existing AL switches
    al_switches = [
        entity_id for entity_id in self.hass.states.async_entity_ids("switch")
        if entity_id.startswith("switch.adaptive_lighting_")
    ]

    if al_switches and user_input is None:
        return self.async_show_form(
            step_id="setup_choice",
            data_schema=vol.Schema({
                vol.Required("setup_type"): vol.In({
                    "quick": f"Quick Setup ({len(al_switches)} AL switches detected)",
                    "manual": "Manual Setup (configure everything)",
                }),
            }),
        )

    if user_input.get("setup_type") == "quick":
        return await self.async_step_quick_setup()
```

**Estimated Effort**: 2-3 hours

---

### 2. Per-Zone Timeout Overrides

**User Request**: "Add number entities for per-zone timeout overrides"

**Implementation**:
- **API Layer** (coordinator.py):
  - Add `manual_timeout: int | None` to zone config schema
  - Add `get_zone_manual_timeout(zone_id) -> int`
  - Add `set_zone_manual_timeout(zone_id, timeout) -> None`

- **Consumer Layer** (platforms/number.py):
  - Add `ALPZoneManualTimeoutNumber` class (one per zone)

**Estimated Effort**: 2-3 hours

---

### 3. Sonos Convenience Features

**User Request**: "Add missing Sonos features from implementation_1"

**Missing**:
- Wake sequence enable/disable switch
- Sunrise time sensor
- Wake start notification

**Implementation**:
- `switch.alp_wake_sequence_enabled` (platforms/switch.py)
- `sensor.alp_next_sunrise` (platforms/sensor.py)
- Notifications in implementation_2.yaml Tier 2

**Estimated Effort**: 2-3 hours

---

### 4. implementation_2.yaml Notifications

**User Request**: "Explore notification opportunities"

**Opportunities**:
1. Dark day alert (env boost > 20%)
2. Wake sequence started (15 min before alarm)
3. Manual timer expiring soon (5 min warning)
4. Scene changed confirmation

**Location**: implementation_2.yaml Tier 2 (commented by default)

**Estimated Effort**: 1 hour

---

### 5. More Diagnostic Sensors

**User Request**: "Add more diagnostic sensors"

**Additions**:
- `sensor.alp_last_action` - Last coordinator action + timestamp
- `sensor.alp_manual_timer_status` - Summary of all active timers
- `sensor.alp_zone_health_status` - Per-zone health

**Estimated Effort**: 1-2 hours

---

## 🎯 IMPLEMENTATION PRIORITY

### CRITICAL (Must Fix)
1. **Wake Sequence Manual Control** - Core feature broken
2. **Scene Application Manual Control** - Core feature broken
3. **Environmental Time Multiplier** - Logic backwards

### HIGH (Should Fix)
4. **Button Press Race Condition** - IF user confirms it's broken
5. **Scene Zone Targeting** - UX expectation mismatch

### MEDIUM (Nice to Have)
6. Quick Setup Config Flow
7. Per-Zone Timeout Overrides
8. Sonos Wake Disable Switch

### LOW (Polish)
9. implementation_2.yaml Notifications
10. Additional Diagnostic Sensors

---

## 🛠️ IMPLEMENTATION APPROACH (Following @claude.md)

### For Each Critical Issue:

1. **API Layer FIRST**
   - Add coordinator methods (e.g., `_set_wake_manual_control()`)
   - Add state tracking (e.g., `_wake_in_progress: dict[str, bool]`)
   - Write comprehensive docstrings
   - Add logging

2. **Consumer Layer SECOND**
   - Update platforms to use new coordinator methods
   - Never access coordinator internals directly

3. **Tests for Each**
   - Test coordinator methods in isolation
   - Test consumer layer with mocked coordinator

4. **Architectural Verification**
   - Run grep checks for violations
   - Ensure no `coordinator.data[]` access
   - Ensure no `coordinator._private` access

---

## ✅ NEXT STEPS

**Awaiting User Confirmation**:

1. ❓ **Issue #2 (Button Race Condition)**: Is this actually broken in production, or theoretical?

2. ❓ **Issue #5 (Scene Zone Targeting)**: Which approach (A/B/C)?

3. ❓ **Any other critical issues** not yet identified?

**Ready to implement when confirmed.**
