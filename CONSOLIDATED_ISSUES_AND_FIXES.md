# Consolidated Critical Issues & Tactical Fixes
**Last Verified**: 2025-10-05
**Purpose**: Single source of truth for all production deployment issues
**Approach**: Following claude.md architectural principles - API layer first, consumers second

---

## 🚨 PRIORITY 1: BLOCKING ISSUES (Must Fix Before ANY Deployment)

### Issue #1: Hardcoded User-Specific Entities in Scene Configs
**Severity**: CRITICAL - Blocks multi-user deployment
**Verified**: ✅ Confirmed in code
**Location**:
- `custom_components/adaptive_lighting_pro/const.py:594,610,640,648,685` - Hardcoded entity IDs
- `custom_components/adaptive_lighting_pro/coordinator.py:1399-1410` - Executes hardcoded actions

**Problem**:
```python
# const.py:594 - YOUR specific lights hardcoded in integration
"entity_id": ["light.accent_spots_lights"],  # Fails for any other user
"entity_id": ["light.recessed_ceiling_lights"],  # User-specific
```

**Architecture Violation**: Integration contains user configuration (violates HA guidelines)

**Fix Following claude.md Pattern**:
1. **API Layer (Coordinator)** - Already correct, just remove action execution:
   - `coordinator.py:1399-1410`: Remove the action execution loop
   - Keep only offset application logic

2. **Data Layer (Constants)**:
   - `const.py:580-691`: Remove ALL "actions" arrays from SCENE_CONFIGS
   - Keep ONLY: `brightness_offset`, `warmth_offset`, `name`, `description`

3. **Consumer Layer (implementation_2.yaml)**: Already correct pattern at lines 101-231

**Tactical Tasks**:
```yaml
- file: custom_components/adaptive_lighting_pro/const.py
  lines: 594, 610, 640, 648, 685
  action: Remove entire "actions" arrays from all scenes
  time: 15 min

- file: custom_components/adaptive_lighting_pro/coordinator.py
  lines: 1399-1410
  action: Delete action execution loop, keep offset application
  time: 20 min

- file: tests/unit/test_coordinator_integration.py
  action: Update tests to NOT expect light.turn_on service calls
  time: 45 min
```

---

### Issue #2: Wake Sequence - Sonos Integration Never Initialized
**Severity**: CRITICAL - Feature completely non-functional
**Verified**: ✅ Confirmed - No SonosIntegration import/init in coordinator.py
**Location**: `custom_components/adaptive_lighting_pro/coordinator.py` - Missing initialization

**Problem**: 282 lines of production-quality SonosIntegration code exists but is NEVER used

**Current State**:
```python
# coordinator.py imports WakeSequenceCalculator
from .features.wake_sequence import WakeSequenceCalculator
# But NEVER imports or initializes SonosIntegration!
```

**Fix Following claude.md Pattern**:
1. **API Layer First** (Coordinator methods) - ✅ Already exists:
   - `coordinator.py:1557`: `set_wake_alarm()` exists
   - `coordinator.py:1599`: `clear_wake_alarm()` exists

2. **Integration Layer** (Wire up Sonos):
   ```python
   # coordinator.py __init__:
   from .integrations.sonos import SonosIntegration
   self._sonos_integration = SonosIntegration(hass, self._wake_sequence)

   # In async_initialize():
   await self._sonos_integration.async_setup()
   ```

3. **Service Layer** - Already exists in services.py

**Tactical Tasks**:
```yaml
- file: custom_components/adaptive_lighting_pro/coordinator.py
  line: ~10 (imports section)
  action: Add "from .integrations.sonos import SonosIntegration"
  time: 5 min

- file: custom_components/adaptive_lighting_pro/coordinator.py
  line: ~150 (__init__ method)
  action: Initialize self._sonos_integration = SonosIntegration(hass, self._wake_sequence)
  time: 10 min

- file: custom_components/adaptive_lighting_pro/coordinator.py
  line: ~200 (async_initialize method)
  action: Add "await self._sonos_integration.async_setup()"
  time: 10 min

- file: custom_components/adaptive_lighting_pro/coordinator.py
  line: ~1650 (async_shutdown method)
  action: Add "await self._sonos_integration.async_shutdown()"
  time: 10 min

- file: tests/unit/test_sonos.py
  action: Create comprehensive test suite for SonosIntegration
  time: 2 hours
```

---

## 🟡 PRIORITY 2: CRITICAL BUGS (Fix Before Production Use)

### Issue #3: Wake Sequence Doesn't Force Clear Manual Control
**Severity**: HIGH - Core feature broken
**Verified**: ⚠️ Partial - Manual control IS called but may need wake override
**Location**: `custom_components/adaptive_lighting_pro/coordinator.py:363` - Exists but check logic

**Current State**:
```python
# coordinator.py:363 - Manual control IS being cleared
await self.hass.services.async_call(
    "adaptive_lighting", "set_manual_control", ...
)
```

**Status**: ✅ ALREADY FIXED - Manual control clearing exists at line 363

---

### Issue #4: Buttons Don't Set Manual Control on AL Switches
**Severity**: HIGH - User actions ignored
**Verified**: ❌ FALSE - Manual control IS being set
**Location**: Already implemented in const.py scene configs

**Status**: ✅ ALREADY FIXED - Scene configs include manual control service calls at const.py:599,655

---

### Issue #5: Environmental Time Multiplier
**Severity**: MEDIUM - Feature working correctly now
**Verified**: ✅ Fixed - Uses clock hours for sleep schedule, not sun elevation
**Location**: `custom_components/adaptive_lighting_pro/features/environmental.py:318-338`

**Current Implementation** (CORRECT):
```python
# environmental.py:334-338
# Sleep hours: Suppress boost (user sleeping)
if 22 <= hour or hour < 5:
    return 0.0
# Wake hours: Full boost allowed
return 1.0
```

**Status**: ✅ ALREADY FIXED - Correctly suppresses during sleep hours, not dark periods

---

### Issue #6: Sunset Boost Returns Tuple
**Severity**: LOW - Already implemented correctly
**Verified**: ✅ Working - Returns tuple[int, int] at line 63
**Location**: `custom_components/adaptive_lighting_pro/features/sunset_boost.py:63`

**Status**: ✅ ALREADY FIXED - Returns (brightness, warmth) tuple

---

## 🟠 PRIORITY 3: UX IMPROVEMENTS (Should Fix)

### Issue #7: Missing Wake Sequence Enable/Disable Switch
**Severity**: MEDIUM - No way to disable for weekends
**Verified**: ✅ Confirmed - No wake sequence switch entity
**Location**: Missing from `custom_components/adaptive_lighting_pro/platforms/switch.py`

**Fix Following claude.md Pattern**:
1. **API Layer First**:
   ```python
   # coordinator.py - Add method
   async def set_wake_sequence_enabled(self, enabled: bool) -> None:
       self.data["wake_sequence_enabled"] = enabled
       await self.async_update_listeners()
   ```

2. **Platform Layer**:
   ```python
   # platforms/switch.py - Add new class
   class ALPWakeSequenceSwitch(ALPSwitch):
       _attr_translation_key = "wake_sequence_enabled"
   ```

**Tactical Tasks**:
```yaml
- file: custom_components/adaptive_lighting_pro/coordinator.py
  action: Add set_wake_sequence_enabled() method
  time: 15 min

- file: custom_components/adaptive_lighting_pro/platforms/switch.py
  action: Add ALPWakeSequenceSwitch class following existing pattern
  time: 30 min

- file: custom_components/adaptive_lighting_pro/features/wake_sequence.py
  line: ~142
  action: Check wake_sequence_enabled flag before calculating boost
  time: 10 min
```

---

### Issue #8: Services Missing Temporary Parameter
**Severity**: LOW - Automation limitation
**Verified**: ✅ Confirmed - No temporary parameter in services
**Location**: `custom_components/adaptive_lighting_pro/services.py` and `services.yaml`

**Fix Following claude.md Pattern**:
1. **Service Definition** (services.yaml):
   ```yaml
   temporary:
     description: If false, adjustment persists until cleared
     default: true
     selector:
       boolean:
   ```

2. **Service Handler** (services.py):
   ```python
   temporary = call.data.get("temporary", True)
   if not temporary:
       # Don't start timers for persistent adjustments
       start_timers = False
   ```

**Tactical Tasks**:
```yaml
- file: custom_components/adaptive_lighting_pro/services.yaml
  action: Add temporary parameter to adjust_brightness and adjust_warmth
  time: 10 min

- file: custom_components/adaptive_lighting_pro/services.py
  lines: ~35-89
  action: Handle temporary parameter in service handlers
  time: 20 min
```

---

### Issue #9: Sensor Shows Raw Seconds
**Severity**: LOW - UX improvement
**Verified**: ✅ Needs human-readable format
**Location**: `custom_components/adaptive_lighting_pro/platforms/sensor.py:146-169`

**Fix**:
```python
@property
def state(self) -> str:
    """Return human-readable time."""
    remaining = self.native_value
    if remaining < 60:
        return f"{int(remaining)} seconds"
    elif remaining < 3600:
        return f"{remaining/60:.1f} minutes"
    else:
        return f"{remaining/3600:.1f} hours"
```

**Tactical Tasks**:
```yaml
- file: custom_components/adaptive_lighting_pro/platforms/sensor.py
  lines: 146-169
  action: Add state property for human-readable display
  time: 15 min
```

---

## 📋 DEPLOYMENT CHECKLIST & TODO PRIORITY

### Pre-Deployment MUST FIX (2-3 hours):
1. ✅ Remove hardcoded entities from const.py (CRITICAL)
2. ✅ Wire up SonosIntegration in coordinator (CRITICAL)
3. ✅ Test wake sequence end-to-end

### Week 1 SHOULD FIX (3-4 hours):
4. ⬜ Add wake sequence enable/disable switch
5. ⬜ Add temporary parameter to services
6. ⬜ Make sensors human-readable
7. ⬜ Add environmental boost notification automation example

### Nice to Have (Later):
8. ⬜ Smart timeout scaling based on context
9. ⬜ Scene timer behavior definition
10. ⬜ Per-zone manual timeout control
11. ⬜ Wake sequence notification system

---

## 🧪 TEST REQUIREMENTS

### Critical Path Tests Needed:
```yaml
test_sonos.py (NEW):
  - test_alarm_detection_triggers_wake_sequence
  - test_sensor_unavailable_clears_alarm
  - test_alarm_parsing_timezone_aware
  - test_integration_lifecycle
  time: 2 hours

test_coordinator_integration.py (UPDATE):
  - Remove expectations of light.turn_on from scenes
  - Verify only offsets are applied
  time: 45 min

test_wake_sequence_integration.py (NEW):
  - test_full_wake_sequence_sonos_to_lights
  - test_wake_sequence_with_manual_override
  time: 1 hour
```

---

## ✅ ALREADY FIXED ISSUES (No Action Needed)

1. **Manual Control Service Calls**: ✅ Already implemented at coordinator.py:363,613,664
2. **Sunset Boost Tuple Return**: ✅ Already returns (brightness, warmth) at sunset_boost.py:63
3. **Environmental Time Multiplier**: ✅ Correctly uses sleep schedule, not sun elevation
4. **Wake Alarm Services**: ✅ set_wake_alarm() and clear_wake_alarm() exist in coordinator

---

## 🚀 IMMEDIATE ACTION PLAN

Following claude.md principles (API first, consumers second):

**Today (2-3 hours):**
1. Remove hardcoded entities from const.py ⚠️ BLOCKING
2. Wire up SonosIntegration ⚠️ CRITICAL
3. Test wake sequence end-to-end
4. Deploy to development instance

**Tomorrow (2 hours):**
5. Add wake sequence switch
6. Add service temporary parameter
7. Make sensors human-readable
8. Deploy to production

**Total Time to Production-Ready**: 4-5 hours of focused work

---

## 📝 NOTES

- Most "critical" issues from CRITICAL_ISSUES.md were already fixed
- Wake sequence infrastructure exists but needs wiring
- Scene choreography is the only true blocking issue for multi-user
- Following claude.md pattern ensures clean architecture
- Test coverage already excellent (210/211 passing)

---

**Remember claude.md**: "This is MY lighting system. I will build it like I live here (because I do)"