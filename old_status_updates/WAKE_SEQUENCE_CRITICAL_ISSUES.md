# Wake Sequence Implementation - Critical Issues Found

**Reviewed by**: Claude (as user/developer)
**Date**: 2025-10-01
**Standard**: claude.md - "Would I be proud to show this to the Anthropic team?"

## 🚨 VERDICT: NOT PRODUCTION READY - MULTIPLE CRITICAL BUGS

The wake sequence implementation has excellent code quality for what exists, but **it will never work in production** due to missing integration points.

---

## CRITICAL ISSUES (Showstoppers)

### ❌ Issue #1: SonosIntegration Never Initialized
**Severity**: CRITICAL - Feature completely non-functional
**File**: `coordinator.py`

**Problem**:
```python
# coordinator.py imports WakeSequenceCalculator
from .features.wake_sequence import WakeSequenceCalculator

# But NEVER imports or initializes SonosIntegration:
# from .integrations.sonos import SonosIntegration  ← MISSING
```

**Impact**:
- Wake sequence will NEVER trigger automatically from Sonos alarms
- The only way to set an alarm is manual (but no service exists for that)
- SonosIntegration class exists (282 lines of production-quality code) but is DEAD CODE
- All the sensor monitoring, alarm parsing, error handling = unused

**What's Missing in coordinator.__init__()**:
```python
# REQUIRED but MISSING:
from .integrations.sonos import SonosIntegration

# In __init__:
self._sonos_integration = SonosIntegration(hass, self._wake_sequence)

# In async_initialize() or similar:
await self._sonos_integration.async_setup()

# In async_shutdown():
await self._sonos_integration.async_shutdown()
```

**Test Result**: User sets Sonos alarm for 6:30 AM
- **Expected**: Wake sequence starts at 6:15 AM, gradual ramp 0% → 20%
- **Actual**: Nothing happens. Wake sequence never triggers. Alarm goes off at 6:30 AM with no preparation.

---

### ❌ Issue #2: Config Flow Missing Wake Sequence Settings
**Severity**: CRITICAL - No way to configure the feature
**File**: `config_flow.py`

**Problem**:
Config flow exposes OLD implementation_1.yaml Sonos settings:
```python
# config_flow.py has OLD approach:
CONF_SONOS_BEDROOM_OFFSET = -1800  # Sunrise time offset
CONF_SONOS_KITCHEN_OFFSET = -2700  # Sunrise time offset
```

But wake_sequence uses NEW constants that are NEVER exposed in UI:
```python
# const.py defines these but config_flow NEVER uses them:
CONF_WAKE_SEQUENCE_ENABLED = "wake_sequence_enabled"
CONF_WAKE_SEQUENCE_TARGET_ZONE = "wake_sequence_target_zone"
CONF_WAKE_SEQUENCE_DURATION = "wake_sequence_duration"
CONF_WAKE_SEQUENCE_MAX_BOOST = "wake_sequence_max_boost"
```

**Impact**:
- User cannot enable/disable wake sequence via UI
- User cannot configure target zone (stuck with default "bedroom")
- User cannot customize wake duration (stuck with 900 seconds)
- User cannot customize max boost (stuck with 20%)

**What's Missing in config_flow.py**:
```python
# In async_step_integrations schema:
vol.Optional(CONF_WAKE_SEQUENCE_ENABLED, default=False): selector.BooleanSelector(),
vol.Optional(CONF_WAKE_SEQUENCE_TARGET_ZONE, default="bedroom"): selector.TextSelector(),
vol.Optional(CONF_WAKE_SEQUENCE_DURATION, default=900): selector.NumberSelector(
    selector.NumberSelectorConfig(min=300, max=1800, step=60, mode="slider")
),
vol.Optional(CONF_WAKE_SEQUENCE_MAX_BOOST, default=20): selector.NumberSelector(
    selector.NumberSelectorConfig(min=5, max=50, step=5, mode="slider")
),
```

---

### ❌ Issue #3: No Service to Manually Set Wake Alarm
**Severity**: HIGH - No workaround if Sonos unavailable
**File**: `services.py` (missing implementation)

**Problem**:
User has no way to manually set wake alarm as a workaround when:
- Sonos integration is disabled
- Sonos sensor is unavailable
- User wants to test wake sequence
- User doesn't use Sonos but wants wake sequence from other automation

**What's Missing in services.py**:
```python
# Service: adaptive_lighting_pro.set_wake_alarm
async def async_set_wake_alarm(call):
    alarm_time = call.data.get("alarm_time")  # ISO datetime string
    coordinator = hass.data[DOMAIN][call.data.get("entry_id")]
    await coordinator.set_wake_alarm(alarm_time)

# Service: adaptive_lighting_pro.clear_wake_alarm
async def async_clear_wake_alarm(call):
    coordinator = hass.data[DOMAIN][call.data.get("entry_id")]
    coordinator.clear_wake_alarm()
```

**Service definition needed in services.yaml**:
```yaml
set_wake_alarm:
  name: Set wake alarm
  description: Manually set wake alarm time to trigger wake sequence
  fields:
    alarm_time:
      name: Alarm time
      description: Alarm time (ISO 8601 format)
      required: true
      example: "2025-10-02T06:30:00-07:00"
      selector:
        datetime:
```

---

### ❌ Issue #4: Coordinator Not Wired to Wake Sequence
**Severity**: MEDIUM - Partial integration
**File**: `coordinator.py`

**Current State** (coordinator.py lines 413-414):
```python
if zone_config.get("wake_sequence_enabled", True):
    wake_boost = self._wake_sequence.calculate_boost(zone_id)
```

**Problems**:
1. `wake_boost` is calculated but **never added to total_brightness**
2. Looking at line 385-404, the final brightness calculation is:
   ```python
   raw_brightness_boost = env_boost + sunset_boost + self._brightness_adjustment
   ```
   **MISSING: `+ wake_boost`**

3. Wake boost is calculated per-zone but never accumulated into the final adjustment

**Fix Required** (coordinator.py around line 385):
```python
# Before:
raw_brightness_boost = env_boost + sunset_boost + self._brightness_adjustment

# After:
wake_boost = self._wake_sequence.calculate_boost(zone_id)
raw_brightness_boost = env_boost + sunset_boost + self._brightness_adjustment + wake_boost
```

---

## MISSING TESTS (High Priority)

### ❌ Issue #5: No SonosIntegration Tests
**Severity**: HIGH - Critical component untested
**File**: `tests/unit/test_sonos.py` (DOES NOT EXIST)

**Missing Test Coverage**:
1. **Alarm Detection**:
   - `test_sonos_alarm_detected_triggers_wake_sequence()`
   - `test_alarm_time_unchanged_no_duplicate_trigger()`
   - `test_stale_alarm_in_past_ignored()`

2. **Sensor State Handling**:
   - `test_sensor_unavailable_clears_alarm()`
   - `test_sensor_unknown_state_clears_alarm()`
   - `test_sensor_comes_back_online_resumes()`

3. **Alarm Parsing**:
   - `test_parse_iso8601_timezone_aware()`
   - `test_parse_iso8601_utc_z_suffix()`
   - `test_parse_timezone_naive_assumes_utc()`
   - `test_parse_invalid_format_returns_none()`

4. **Integration Lifecycle**:
   - `test_setup_with_valid_sensor_succeeds()`
   - `test_setup_with_missing_sensor_fails_gracefully()`
   - `test_shutdown_removes_listener()`
   - `test_ha_restart_mid_sequence_resumes()`

5. **Real-World Scenarios**:
   - `test_alarm_cancelled_mid_sequence_stops_boost()`
   - `test_multiple_alarms_same_day_processes_earliest()`
   - `test_alarm_during_active_sequence_replaces()`
   - `test_network_blip_sensor_unavailable_recovers()`

**Total Missing Tests**: ~20 test cases covering 282 lines of untested code

---

### ❌ Issue #6: No Integration Tests
**Severity**: HIGH - End-to-end flow untested
**File**: `tests/integration/test_wake_sequence_integration.py` (DOES NOT EXIST)

**Missing Integration Tests**:
1. **End-to-End Wake Sequence**:
   - `test_full_wake_sequence_sonos_to_lights()`
   - Test: Set Sonos alarm → sensor updates → wake sequence starts → bedroom lights gradually brighten → alarm fires → sequence ends

2. **Combined Boosts**:
   - `test_dark_cloudy_morning_with_wake_sequence()`
   - Test: env_boost (25%) + wake_boost (20%) + intelligent capping for narrow bedroom zone

3. **Sensor Updates**:
   - `test_wake_sequence_sensors_update_during_ramp()`
   - Test: sensor.alp_wake_sequence_offset shows 0% → 10% → 20%
   - Test: sensor.alp_next_alarm shows correct time
   - Test: sensor.alp_wake_start_time shows alarm - 15 min

4. **Error Scenarios**:
   - `test_sonos_offline_during_sequence_graceful_degradation()`
   - `test_coordinator_restart_during_wake_sequence()`

**Total Missing Tests**: ~10-15 integration tests

---

## ARCHITECTURAL ISSUES (Medium Priority)

### ⚠️ Issue #7: Inconsistent Configuration Approach
**Severity**: MEDIUM - Confusing codebase
**Files**: `config_flow.py`, `const.py`, `coordinator.py`

**Problem**:
Two conflicting Sonos approaches exist in the codebase:

**Approach 1**: OLD implementation_1.yaml (sunrise time offsets)
```python
# config_flow.py exposes:
CONF_SONOS_BEDROOM_OFFSET = -1800  # Offset AL's sunrise time
CONF_SONOS_KITCHEN_OFFSET = -2700  # Per-zone sunrise offsets
```

**Approach 2**: NEW wake_sequence (brightness boost)
```python
# coordinator.py implements:
wake_boost = self._wake_sequence.calculate_boost(zone_id)
# Adds 0-20% brightness boost over 15 minutes
```

**Impact**:
- Developer confusion: Which approach is authoritative?
- Config flow exposes wrong settings
- User expects sunrise offset behavior but gets boost behavior
- Documentation inconsistency

**Resolution Required**:
1. **Remove** CONF_SONOS_BEDROOM_OFFSET and CONF_SONOS_KITCHEN_OFFSET from config_flow
2. **Add** CONF_WAKE_SEQUENCE_* settings to config_flow
3. **Update** documentation to clarify: wake sequence is brightness BOOST, not sunrise offset
4. **Deprecation notice** for users migrating from YAML implementation

---

### ⚠️ Issue #8: Missing Wake Sequence Service Methods
**Severity**: MEDIUM - Limited automation flexibility
**File**: `coordinator.py`

**Current State**:
Coordinator has NO public methods to control wake sequence from services/automations:
```python
# MISSING but needed:
async def set_wake_alarm(self, alarm_time: datetime) -> None
async def clear_wake_alarm(self) -> None
def get_wake_sequence_status(self) -> dict[str, Any]
```

**Impact**:
- Advanced users cannot create automations to trigger wake sequence from:
  - Google Calendar events
  - iOS/Android alarm apps via webhooks
  - Custom wake time calculations
- No way to test wake sequence without Sonos

**Fix Required** (coordinator.py):
```python
async def set_wake_alarm(self, alarm_time: datetime) -> None:
    \"\"\"Manually set wake alarm (for automations or testing).\"\"\"
    self._wake_sequence.set_next_alarm(alarm_time)
    await self.async_request_refresh()  # Trigger immediate update

async def clear_wake_alarm(self) -> None:
    \"\"\"Clear wake alarm (cancel wake sequence).\"\"\"
    self._wake_sequence.clear_alarm()
    await self.async_request_refresh()
```

---

## DOCUMENTATION ISSUES (Low Priority)

### ⚠️ Issue #9: No User-Facing Documentation
**Severity**: LOW - But required for release
**File**: `docs/wake_sequence.md` (DOES NOT EXIST)

**Missing Documentation**:
1. **Feature Overview**: What wake sequence does, why it's useful
2. **Setup Guide**: How to configure Sonos integration
3. **Troubleshooting**: Common issues (sensor unavailable, alarm not triggering)
4. **Advanced Usage**: Manual services, custom automations
5. **Examples**: Real YAML automation examples

---

## POSITIVE FINDINGS (What Works Well)

### ✅ Excellent Code Quality Where Implemented

**WakeSequenceCalculator** (features/wake_sequence.py):
- Clean, well-documented class (311 lines)
- Comprehensive docstrings with examples
- Proper error handling (past alarms ignored)
- Type hints throughout
- Configurable (duration, max_boost, target_zone)
- Stateless calculation (pure function behavior)

**SonosIntegration** (integrations/sonos.py):
- Robust error handling (sensor unavailable, parsing failures)
- Proper async lifecycle (setup, shutdown)
- State change listener correctly implemented
- ISO 8601 parsing with timezone handling
- Logging at appropriate levels (debug, info, warning, error)
- Real-world edge cases documented

**Test Coverage for WakeSequenceCalculator**:
- 10 test cases covering real-world morning scenarios
- Edge cases tested (disabled feature, wrong zone, cleared alarm)
- Descriptive test names and assertions
- Follows claude.md standards ("why it matters" comments)

### ✅ Architecture is Sound

The separation of concerns is excellent:
```
WakeSequenceCalculator  →  Pure logic, no HA dependencies
        ↑
SonosIntegration       →  Sensor monitoring, calls wake_sequence
        ↑
Coordinator            →  Orchestration, applies boosts to zones
        ↑
Sensors                →  Display state to user
```

**This architecture is correct** - just needs the wiring completed.

---

## IMPACT ANALYSIS: What Happens if User Tries to Use This?

### Scenario 1: User Sets Sonos Alarm for 6:30 AM

**Expected Behavior** (from claude.md):
```
6:15 AM: Wake sequence starts (0% boost)
6:22 AM: Halfway through (10% boost)
6:30 AM: Alarm fires (20% boost), sequence ends
```

**Actual Behavior**:
```
6:15 AM: Nothing (SonosIntegration never initialized)
6:22 AM: Nothing (wake_sequence.calculate_boost never called)
6:30 AM: Alarm goes off (user woken abruptly, no gentle ramp)
```

**User Experience**: "This doesn't work at all"

---

### Scenario 2: User Tries to Configure Wake Sequence

**User Actions**:
1. Opens HA configuration
2. Goes to Adaptive Lighting Pro integration
3. Clicks "Configure"
4. Looks for wake sequence settings

**Expected**:
- Enable/disable wake sequence toggle
- Target zone selector
- Wake duration slider (5-30 minutes)
- Max boost slider (5-50%)

**Actual**:
- Only sees OLD Sonos bedroom/kitchen offset settings
- No wake sequence controls anywhere
- Confused: "Where do I enable this feature?"

**User Experience**: "Feature exists in code but can't be enabled"

---

### Scenario 3: Dark Cloudy Morning at 6:22 AM

**Expected Behavior**:
```python
env_boost = 25%        # Very dark, cloudy
wake_boost = 10%       # Halfway through sequence
manual_adj = 0%        # No manual adjustment
total = 35%            # Combined boost

# Bedroom zone: 20-40% range (narrow)
# Intelligent capping: 35% > 30% max → capped to 30%
# Final brightness: 20% + 30% = 50% (comfortable wake)
```

**Actual Behavior**:
```python
env_boost = 25%        # Calculated correctly
wake_boost = 0%        # Never added (Issue #4)
manual_adj = 0%
total = 25%            # Missing wake boost!

# Final brightness: 20% + 25% = 45% (darker than expected)
```

**User Experience**: "Wake sequence doesn't seem to be doing anything"

---

## CRITICAL PATH TO PRODUCTION

To make this feature actually work, complete IN ORDER:

### Phase 1: Core Integration (2-3 hours)
1. ✅ Import SonosIntegration in coordinator.py
2. ✅ Initialize self._sonos_integration in coordinator.__init__()
3. ✅ Call await self._sonos_integration.async_setup()
4. ✅ Add wake_boost to total brightness calculation (line ~385)
5. ✅ Test end-to-end: Set alarm → wake sequence triggers

### Phase 2: Configuration (1-2 hours)
6. ✅ Add CONF_WAKE_SEQUENCE_* fields to config_flow.py integration step
7. ✅ Remove or deprecate old CONF_SONOS_*_OFFSET fields
8. ✅ Pass config to coordinator for wake_sequence.configure()
9. ✅ Test: Configure wake sequence via UI

### Phase 3: Services (1 hour)
10. ✅ Add set_wake_alarm and clear_wake_alarm to services.py
11. ✅ Add services.yaml definitions
12. ✅ Add coordinator.set_wake_alarm() and clear_wake_alarm() methods
13. ✅ Test: Call service from automation

### Phase 4: Testing (3-4 hours)
14. ✅ Write test_sonos.py with 20 test cases
15. ✅ Write test_wake_sequence_integration.py with 10 integration tests
16. ✅ Achieve >80% coverage on wake_sequence and sonos modules
17. ✅ Test all real-world scenarios from claude.md

### Phase 5: Documentation (1 hour)
18. ✅ Write docs/wake_sequence.md user guide
19. ✅ Add troubleshooting section
20. ✅ Add example automations

**Total Estimated Time**: 8-11 hours to production-ready

---

## FINAL VERDICT

**Code Quality**: ★★★★★ (5/5) - Excellent where implemented
**Completeness**: ★☆☆☆☆ (1/5) - Major gaps in integration
**Production Ready**: ❌ NO - Will not work in real use

**Recommendation**:
**DO NOT SHIP** until issues #1-#4 are resolved. The code that exists is excellent, but critical integration points are missing. User will enable Sonos integration, set alarm, and nothing will happen - creating a support nightmare.

**Timeline to Production**: 8-11 hours of focused work following critical path above.

---

**Question from claude.md**: *"Would I be proud to show this to the Anthropic team?"*

**Answer**:
- The WakeSequenceCalculator class? **Yes** - it's beautiful code
- The overall integration? **No** - it's incomplete and won't work
- After fixing Issues #1-#4? **Absolutely** - this will be exceptional

The bones are excellent. Just needs the muscles connected to make it move.
