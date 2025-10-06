# TACTICAL FIX PLAN - FINAL CORRECTED VERSION
**Complete Understanding with User Confirmation**

**Created**: 2025-10-05
**Status**: Ready for Implementation
**Principle**: API Layer FIRST, Consumer Layer SECOND (@claude.md)

---

## ✅ CONFIRMED UNDERSTANDING

### 1. Environmental Time Multiplier
**User Confirmation**: "Suppress boost during dark periods is fine"
- **KEEP CURRENT LOGIC** with sun elevation suppression
- implementation_1.yaml does suppress at night (22:00-06:00) AND during dawn/dusk (0.7x)
- Current implementation is CORRECT per user requirements
- **NO CHANGES NEEDED**

### 2. Wake Sequence Environmental Boost
**User Confirmation**: "We don't want boost during wake either"
- Wake sequence should disable environmental boost
- **ACTION REQUIRED**: When wake active, set environmental boost to 0 for that zone

### 3. Wake Sequence Manual Control
**User Confirmation**: "Set manual_control=True when wake starts, clear when it ends"
- **ACTION REQUIRED**: Implement manual_control lifecycle for wake

### 4. Scene Zone Targeting
**User Confirmation**: "Only the lights or zones specified should be affected. Each zone will be different"
- Scenes should only affect zones with lights in scene actions
- **ACTION REQUIRED**: Per-zone scene offset tracking

---

## 🔴 CRITICAL ISSUE #1: Wake Sequence Missing manual_control Lifecycle

### Current Problem

**File**: coordinator.py:349-367

Wake sequence:
1. ✅ Calculates boost correctly
2. ✅ Applies adjustments to zone
3. ❌ Never sets `manual_control=True`
4. ❌ Never clears `manual_control=False` when done

**Result**: AL fights the gradual wake ramp, lights jump to sunrise brightness

### The Fix

**Phase 1: Track Wake State**

**Location**: coordinator.py (class variables)

```python
class ALPDataUpdateCoordinator:
    def __init__(...):
        # Existing init
        self._wake_active_zones: set[str] = set()  # Track which zones have active wake
```

**Phase 2: Set manual_control When Wake Starts**

**Location**: coordinator.py:356 (inside wake_in_progress block)

```python
if wake_in_progress:
    # Check if this is FIRST cycle of wake (just started)
    if zone_id not in self._wake_active_zones:
        # Wake just started - set manual control
        al_switch = zone_config.get("adaptive_lighting_switch")
        lights = zone_config.get("lights", [])

        if al_switch and lights:
            await self.hass.services.async_call(
                ADAPTIVE_LIGHTING_DOMAIN,
                "set_manual_control",
                {
                    "entity_id": al_switch,
                    "lights": lights,
                    "manual_control": True,  # Lock lights during wake
                },
                blocking=False,
            )
            _LOGGER.info(
                "Wake sequence started for zone %s - set manual control",
                zone_id,
            )

        # Mark zone as having active wake
        self._wake_active_zones.add(zone_id)

    # Apply wake adjustments
    await self._apply_adjustments_to_zone(zone_id, zone_config)

elif zone_id in self._wake_active_zones:
    # Wake just ended for this zone
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
            "Wake sequence completed for zone %s - cleared manual control",
            zone_id,
        )

    # Remove from active wake zones
    self._wake_active_zones.discard(zone_id)

    # Now apply normal adjustments
    if not self.zone_manager.is_manual_control_active(zone_id):
        await self._apply_adjustments_to_zone(zone_id, zone_config)
```

---

## 🔴 CRITICAL ISSUE #2: Wake Sequence Should Disable Environmental Boost

### Current Problem

**File**: coordinator.py:437-439

```python
if zone_config.get("environmental_enabled", True):
    env_boost = self._env_adapter.calculate_boost()
```

During wake sequence, environmental boost is STILL calculated and applied!

**Result**: Wake sequence tries to do 20% boost, but environmental adds another 15%, total 35% → breaks wake progression

### The Fix

**Location**: coordinator.py:437-439

```python
# Phase 2.5: Calculate environmental boost
# CRITICAL: Disable during wake sequence (user confirmed)
if zone_config.get("environmental_enabled", True) and zone_id not in self._wake_active_zones:
    env_boost = self._env_adapter.calculate_boost()
```

---

## 🔴 CRITICAL ISSUE #3: Scene Application Missing manual_control

### Current Problem

**File**: coordinator.py:1368-1458

Scene application:
1. ✅ Executes scene actions (turn lights on at specific levels)
2. ✅ Sets scene offsets
3. ❌ Never sets `manual_control=True`
4. ❌ Applies offsets to ALL zones (not just choreographed ones)

**Result**:
- Ultra Dim scene sets lights to 5%
- AL immediately raises them back to 40%
- Scene lasts 0.1 seconds

### The Fix - Part A: Set manual_control for Choreographed Lights

**Location**: coordinator.py:1390 (after scene actions execute)

```python
# Execute scene actions
for action in config.get("actions", []):
    await self.hass.services.async_call(domain, service, action_copy, blocking=False)

# NEW: Lock lights that were choreographed
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
                "manual_control": True,  # Lock scene lights
            },
            blocking=False,
        )
        _LOGGER.info(
            "Scene %s locked %d lights in zone %s with manual control",
            scene.value,
            len(lights),
            zone_id,
        )
```

**Helper Method**:

```python
def _extract_lights_from_scene_actions(
    self, actions: list[dict[str, Any]]
) -> dict[str, list[str]]:
    """Extract light entity_ids from scene actions and map to zones.

    Args:
        actions: Scene action list from SCENE_CONFIGS

    Returns:
        Dict mapping zone_id -> list of light entity_ids in that zone
    """
    affected_lights_by_zone: dict[str, list[str]] = {}

    for action in actions:
        # Extract entity_id(s) from action
        entity_ids = action.get("entity_id", [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        # Map each light to its zone
        for light_id in entity_ids:
            for zone_id, zone_config in self.zones.items():
                zone_lights = zone_config.get("lights", [])
                if light_id in zone_lights:
                    if zone_id not in affected_lights_by_zone:
                        affected_lights_by_zone[zone_id] = []
                    if light_id not in affected_lights_by_zone[zone_id]:
                        affected_lights_by_zone[zone_id].append(light_id)

    return affected_lights_by_zone
```

### The Fix - Part B: Per-Zone Scene Offset Tracking

**Current**: `_scene_brightness_offset` and `_scene_warmth_offset` are GLOBAL

**Required**: Per-zone tracking so only choreographed zones get offsets

**Location**: coordinator.py (class variables)

```python
class ALPDataUpdateCoordinator:
    def __init__(...):
        # OLD: Global scene offsets
        # self._scene_brightness_offset: int = 0
        # self._scene_warmth_offset: int = 0

        # NEW: Per-zone scene offsets
        self._scene_offsets_by_zone: dict[str, tuple[int, int]] = {}
        # Maps zone_id -> (brightness_offset, warmth_offset)
```

**Location**: coordinator.py:1391-1395 (setting scene offsets)

```python
# Apply scene offsets to affected zones only
brightness_offset = config.get("brightness_offset", 0)
warmth_offset = config.get("warmth_offset", 0)

for zone_id in affected_lights_by_zone.keys():
    self._scene_offsets_by_zone[zone_id] = (brightness_offset, warmth_offset)
    _LOGGER.debug(
        "Scene %s applied offsets to zone %s: brightness %+d%%, warmth %+dK",
        scene.value,
        zone_id,
        brightness_offset,
        warmth_offset,
    )
```

**Location**: coordinator.py:456-458 (using scene offsets in adjustment calculation)

```python
# OLD:
# raw_brightness_boost = (env_boost + sunset_brightness_boost + wake_boost +
#                         self._brightness_adjustment + self._scene_brightness_offset)

# NEW: Get per-zone scene offset
scene_brightness, scene_warmth = self._scene_offsets_by_zone.get(zone_id, (0, 0))

raw_brightness_boost = (env_boost + sunset_brightness_boost + wake_boost +
                        self._brightness_adjustment + scene_brightness)

# OLD:
# total_warmth = self._warmth_adjustment + self._scene_warmth_offset + sunset_warmth_offset

# NEW:
total_warmth = self._warmth_adjustment + scene_warmth + sunset_warmth_offset
```

**Location**: coordinator.py:1410-1415 (ALL_LIGHTS scene clearing)

```python
if scene == Scene.ALL_LIGHTS:
    # Clear ALL per-zone scene offsets
    self._scene_offsets_by_zone = {}

    # Restore AL control for all zones
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

**Location**: coordinator.py (global state sensors need update)

```python
# In _async_update_data, update sensor data:
state["global"]["scene_brightness_offset"] = 0  # No longer used
state["global"]["scene_warmth_offset"] = 0      # No longer used
state["global"]["current_scene"] = self._current_scene.value if self._current_scene else "default"
state["global"]["scene_offsets_by_zone"] = self._scene_offsets_by_zone  # NEW
```

---

## 🟡 ISSUE #4: Button Press Possible Race Condition

### Analysis

**Current Code**: coordinator.py:609-618

```python
await self.hass.services.async_call(
    ADAPTIVE_LIGHTING_DOMAIN,
    "set_manual_control",
    {
        "entity_id": al_switch,
        "lights": lights,
        "manual_control": True,
    },
    blocking=False,  # ⚠️ Returns immediately
)
```

**Potential Problem**: Service returns before completing, `async_request_refresh()` might execute before manual_control is actually set

### The Fix

**Location**: coordinator.py:609-618

**Remove `blocking=False` parameter** (defaults to blocking):

```python
await self.hass.services.async_call(
    ADAPTIVE_LIGHTING_DOMAIN,
    "set_manual_control",
    {
        "entity_id": al_switch,
        "lights": lights,
        "manual_control": True,
    },
    # No blocking parameter = waits for service completion
)
```

**Apply Same Fix to All set_manual_control Calls**:
- Wake sequence start/end
- Scene application
- Button press (this one)
- Any other manual_control calls

---

## 📋 ADDITIONAL ENHANCEMENTS (From User List)

### 1. Quick Setup Config Flow

**Implementation**: config_flow.py - detect AL switches, offer auto-configuration

**Estimated Effort**: 2-3 hours

### 2. Per-Zone Timeout Overrides

**Implementation**:
- API: Add `manual_timeout` to zone config, coordinator methods
- Consumer: Add `ALPZoneManualTimeoutNumber` entities

**Estimated Effort**: 2-3 hours

### 3. Sonos Convenience Features

**Missing**:
- Wake sequence enable/disable switch
- Sunrise time sensor
- Wake start notifications

**Estimated Effort**: 2-3 hours

### 4. implementation_2.yaml Notifications

**Add to Tier 2** (commented):
- Dark day alerts
- Wake sequence notifications
- Timer expiry warnings

**Estimated Effort**: 1 hour

### 5. More Diagnostic Sensors

**Additions**:
- Last action sensor
- Manual timer status summary
- Per-zone health status

**Estimated Effort**: 1-2 hours

---

## 🎯 IMPLEMENTATION ORDER

### CRITICAL (Must Fix First)

1. **Wake Sequence manual_control Lifecycle** (Issue #1)
   - Track wake active zones
   - Set manual_control=True on start
   - Clear manual_control=False on end

2. **Wake Sequence Disable Environmental Boost** (Issue #2)
   - Add check: `zone_id not in self._wake_active_zones`

3. **Scene Per-Zone Tracking** (Issue #3)
   - Change to `_scene_offsets_by_zone: dict`
   - Update all references
   - Extract lights from scene actions
   - Set manual_control for choreographed lights
   - Clear manual_control on ALL_LIGHTS

4. **Remove blocking=False from All set_manual_control Calls** (Issue #4)
   - Prevent race conditions

### Implementation Steps (Following @claude.md)

For each issue:

1. **API Layer First**
   - Add coordinator state tracking (e.g., `_wake_active_zones`)
   - Add coordinator methods (e.g., `_extract_lights_from_scene_actions()`)
   - Update existing methods
   - Comprehensive docstrings
   - Logging at INFO/DEBUG levels

2. **Consumer Layer Second**
   - Update platforms if needed (scene tracking might need sensor updates)
   - Ensure no direct coordinator access

3. **Tests**
   - Test new coordinator methods
   - Test wake lifecycle
   - Test scene per-zone behavior
   - Update existing tests if needed

4. **Verification**
   - Run full test suite
   - Architectural grep checks
   - Manual testing of wake sequence + scenes

---

## ✅ READY FOR IMPLEMENTATION

All critical issues identified with correct understanding:
- ✅ Wake manual_control lifecycle
- ✅ Wake disables environmental boost
- ✅ Scene manual_control + per-zone tracking
- ✅ Remove blocking=False race condition

**Awaiting confirmation to proceed with implementation.**
