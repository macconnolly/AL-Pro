# Adaptive Lighting Pro - Senior Engineer Design Review

**Date**: 2025-10-01
**Reviewer**: Senior HA Engineer (User Experience Focus)
**Status**: Critical Design Issues Identified

---

## Executive Summary

After deep review from first principles with a relentless UX focus, I've identified **critical design issues** that will make or break the user experience. The core calculation modules are solid, but **mode interactions** are fundamentally underspecified and will cause frustration.

**Key Insight**: "Lights always exactly where they should be" means respecting **user intent hierarchy**:
1. **Manual control** (highest priority) - user explicitly adjusted
2. **Mode selection** (high priority) - user chose operational state
3. **Environmental adaptation** (medium priority) - system reacts to conditions
4. **Adaptive Lighting baseline** (lowest priority) - time-based defaults

Currently, these don't have proper hierarchy enforcement.

---

## Critical Design Issues Found

### 1. ❌ Environmental/Sunset Boost vs Mode Conflict

**Problem**: Environmental boost will fight against user's explicit mode choice.

**Example Scenario**:
- User sets LATE_NIGHT mode (wants max 25% brightness for sleep)
- Outside is dark/stormy, environmental boost calculates +15%
- System tries to apply: min=20%+15%=35%, max=25%
- Result: Boundary clamps to 25-25% (no adaptation range)
- Environmental boost wasted, mode intent partially violated

**Root Cause**: No checking of current mode before applying environmental features.

**Solution**:
```python
# Environmental/sunset boost ONLY in ADAPTIVE mode
if self._current_mode == Mode.ADAPTIVE:
    env_boost = self._env_adapter.calculate_boost()
    sunset_boost = self._sunset_boost.calculate_boost(lux)
else:
    env_boost = 0
    sunset_boost = 0
    _LOGGER.info(
        "Environmental boost skipped in %s mode. Only active in ADAPTIVE mode.",
        self._current_mode
    )
```

**Impact**: HIGH - This prevents system from fighting user intent

---

### 2. ❌ Manual Adjustments Ignored in Constrained Modes

**Problem**: User presses "brighter" button in LATE_NIGHT mode, nothing happens.

**Example Scenario**:
- LATE_NIGHT mode: max=25%
- Lights currently at 25%
- User presses "brighter" (+10%)
- System tries: min=25%+10%=35%, but max=25%
- Result: Clamped back to 25%, no visible change
- User frustration: "Button doesn't work!"

**Root Cause**: Manual adjustments don't override mode constraints.

**Solution**: Auto-switch to ADAPTIVE mode on manual control
```python
async def handle_manual_adjustment(self, adjustment: int):
    # Save previous mode for restoration
    if self._current_mode != Mode.ADAPTIVE:
        self._previous_mode = self._current_mode
        await self.async_set_mode(Mode.ADAPTIVE)
        _LOGGER.info(
            "Manual adjustment detected. Auto-switching from %s to ADAPTIVE mode. "
            "Will restore %s mode after timer expires.",
            self._previous_mode, self._previous_mode
        )

    # Apply adjustment
    self._brightness_adjustment += adjustment
    await self.start_manual_timer(zone_id)
```

**Timer Expiry Behavior**:
```python
async def _restore_adaptive_control(self, zone_id: str):
    # Clear manual adjustment
    self._brightness_adjustment = 0

    # Restore previous mode if we auto-switched
    if self._previous_mode is not None:
        await self.async_set_mode(self._previous_mode)
        _LOGGER.info("Manual timer expired. Restoring %s mode.", self._previous_mode)
        self._previous_mode = None
```

**Impact**: CRITICAL - This is core UX for manual control

---

### 3. ❌ Scenes Applied in Non-Adaptive Modes

**Problem**: Scene actions (turn on/off specific lights) don't make sense in WORK/MOVIE modes.

**Example Scenario**:
- User sets MOVIE mode (accent lights only, specific setup)
- Scene is set to EVENING_COMFORT (different light setup)
- Conflicting instructions!

**Solution**: Scenes only apply in ADAPTIVE mode
```python
async def async_set_scene(self, scene: Scene):
    if self._current_mode != Mode.ADAPTIVE:
        _LOGGER.warning(
            "Cannot apply scene %s in %s mode. Scenes only work in ADAPTIVE mode.",
            scene, self._current_mode
        )
        return

    # Apply scene
    await self._apply_scene_config(scene)
```

**Impact**: MEDIUM - Prevents confusing behavior

---

### 4. ⚠️ No User Feedback for Constraint Violations

**Problem**: When adjustments are constrained, user has no idea why things aren't working.

**Example Scenarios**:

**Scenario A: Min exceeds max**
```
Zone bedroom: Adjustment +37% would raise min to 57%, but max is 40%.
Clamping to 40-40% range. Lights cannot adapt to time of day.
```

**Scenario B: Environmental boost disabled**
```
Environmental boost +15% skipped in LATE_NIGHT mode.
Switch to ADAPTIVE mode to enable automatic environmental adaptation.
```

**Scenario C: Manual adjustment has no effect**
```
Manual adjustment +10% has no effect - already at maximum (25%) in LATE_NIGHT mode.
Switch to ADAPTIVE mode or higher brightness mode for brighter lights.
```

**Solution**: Add comprehensive logging
```python
def _apply_boundaries(self, zone_id, boundaries):
    if boundaries.min_brightness >= boundaries.max_brightness:
        _LOGGER.warning(
            "Zone %s: Brightness range collapsed to %d-%d%%. "
            "Adaptive Lighting cannot vary brightness. "
            "Consider reducing adjustments or changing mode.",
            zone_id, boundaries.min_brightness, boundaries.max_brightness
        )

    if boundaries.min_brightness > original_max:
        _LOGGER.info(
            "Zone %s: Adjustments (+%d%%) clamped by configured max (%d%%). "
            "Lights at maximum brightness.",
            zone_id, total_offset, original_max
        )
```

**Impact**: HIGH - Users need to understand system behavior

---

### 5. ⚠️ Per-Zone Environmental Boost Not Configurable

**Problem**: Environmental boost applies globally, but some zones shouldn't boost (e.g., bedroom at night).

**Example Scenario**:
- Living room: Environmental boost helpful (compensate for dark weather)
- Bedroom at 11PM: Environmental boost unwanted (trying to sleep, want it dark)
- Both zones get same +15% boost!

**Solution**: Add per-zone environmental feature flags
```python
# In zone config
zone_config = {
    "zone_id": "bedroom_primary",
    "lights": [...],
    "environmental_boost_enabled": False,  # <-- NEW
    "sunset_boost_enabled": False,         # <-- NEW
    ...
}

# In coordinator
if zone_config.get("environmental_boost_enabled", True):
    env_boost = self._env_adapter.calculate_boost()
else:
    env_boost = 0
```

**Impact**: MEDIUM - Better per-zone control

---

## Bugs Fixed

### ✅ 1. Sunset Logic Backwards (CRITICAL FIX)

**Original YAML Implementation**:
- Applied negative offset (-25%) to dim lights during sunset
- Made lights DARKER as sun set
- Completely backwards from user needs!

**Correct Implementation** (sunset_boost.py):
- Applies positive offset (+25%) on dark/cloudy days during sunset
- Only active when lux < 3000 (dark days)
- Skipped on clear days (AL handles naturally)
- Compensates for "double darkness" of weather + sunset

**Impact**: CRITICAL - Fundamental logic correction

---

## Code Quality Assessment

### ✅ adjustment_engine.py - EXCELLENT

**Strengths**:
- Asymmetric boundary logic is mathematically perfect
- Boundary protection prevents min > max
- Clean separation of brightness and color temp logic
- Comprehensive validation

**Verified Correct**:
- Positive adjustments raise MIN only ✓
- Negative adjustments lower MAX only ✓
- Boundary clamping works ✓
- All edge cases handled ✓

**No changes needed** - this is production-ready code.

---

### ✅ environmental.py - EXCELLENT (after fixes)

**Strengths**:
- 5-factor calculation exactly matches YAML logic
- Stepped lux scaling (not linear) - correct
- Complete weather mapping (15 conditions)
- Time-of-day multiplier prevents false positives at night
- Seasonal adjustments accurate

**Verified Correct**:
- Lux: 0-15% stepped scaling ✓
- Weather: 0-20% comprehensive mapping ✓
- Seasonal: Winter +8%, Summer -3% ✓
- Time multiplier: 0.0/0.7/1.0 by time of day ✓
- Max clamp: 25% ✓

**Why time multiplier is correct**:
- At night, lux=0 is EXPECTED (no sun)
- Without multiplier, environmental boost would always trigger at night
- Multiplier prevents false "it's dark outside, boost!" at midnight
- This is proper design, not a bug

**No changes needed** - logic is sound.

---

### ✅ sunset_boost.py - EXCELLENT (completely rewritten)

**Strengths**:
- Correct positive offset (boost, not dim)
- Smart lux gating (only on dark days)
- Clear documentation of purpose
- Proper user experience

**Verified Correct**:
- Only active on dark days (lux < 3000) ✓
- Positive offset 0-25% ✓
- Sunset window -4° to 4° ✓
- Skipped on clear days ✓

**Critical fix applied** - was backwards in original YAML.

---

### ⚠️ coordinator.py - NEEDS MAJOR WORK

**Current State**: Basic scaffold, features not wired

**Missing Critical Features**:
1. No environmental/sunset boost integration
2. No mode checking before applying features
3. No auto-mode-switch on manual control
4. No previous mode tracking/restoration
5. No constraint violation logging
6. No health score calculation

**Required Changes**: See implementation plan below

---

## Implementation Plan

### Phase 1: Mode-Aware Environmental Features (CRITICAL)

**File**: `coordinator.py`

**Changes**:
```python
class ALPDataUpdateCoordinator:
    def __init__(self, ...):
        # Add mode tracking
        self._current_mode: Mode = Mode.ADAPTIVE
        self._previous_mode: Mode | None = None

        # Initialize environmental features
        self._env_adapter = EnvironmentalAdapter(hass)
        self._sunset_boost = SunsetBoostCalculator(hass)
        self._manual_detector = ManualControlDetector(hass)

    async def _async_update_data(self):
        # Calculate environmental features ONLY in ADAPTIVE mode
        if self._current_mode == Mode.ADAPTIVE:
            env_boost = self._env_adapter.calculate_boost()

            # Get lux for sunset boost
            lux = self._get_current_lux()
            sunset_boost = self._sunset_boost.calculate_boost(lux)
        else:
            env_boost = 0
            sunset_boost = 0

        # Calculate total offset
        total_brightness_offset = (
            self._brightness_adjustment +
            env_boost +
            sunset_boost
        )

        # Apply to each zone
        for zone_id, zone_config in self.zones.items():
            # Apply mode config first
            mode_config = self._get_mode_config_for_zone(zone_id)
            effective_config = {**zone_config, **mode_config}

            # Calculate boundaries
            boundaries = calculate_boundaries(
                effective_config,
                total_brightness_offset,
                self._warmth_adjustment
            )

            # Check for constraints
            if boundaries.min_brightness >= boundaries.max_brightness:
                _LOGGER.warning(
                    "Zone %s: Range collapsed to %d-%d%%. "
                    "Adaptive Lighting disabled.",
                    zone_id,
                    boundaries.min_brightness,
                    boundaries.max_brightness
                )

            # Apply
            await self._apply_boundaries_to_zone(zone_id, boundaries)
```

**Priority**: CRITICAL - This is core functionality

---

### Phase 2: Auto-Mode-Switch on Manual Control (CRITICAL)

**File**: `coordinator.py`

**Changes**:
```python
async def set_brightness_adjustment(self, value: int):
    # If not in ADAPTIVE mode, switch automatically
    if self._current_mode != Mode.ADAPTIVE:
        self._previous_mode = self._current_mode
        await self.async_set_mode(Mode.ADAPTIVE)
        _LOGGER.info(
            "Manual adjustment detected in %s mode. "
            "Auto-switching to ADAPTIVE. Will restore after timer.",
            self._previous_mode
        )

    self._brightness_adjustment = value
    await self.async_request_refresh()

async def _restore_adaptive_control(self, zone_id: str):
    # Clear manual adjustments
    await self.zone_manager.async_cancel_timer(zone_id)

    # If all zone timers are cleared, restore previous mode
    if not self.zone_manager.has_active_timers():
        if self._previous_mode is not None:
            await self.async_set_mode(self._previous_mode)
            _LOGGER.info(
                "All manual timers expired. Restoring %s mode.",
                self._previous_mode
            )
            self._previous_mode = None

        # Clear adjustments
        self._brightness_adjustment = 0
        self._warmth_adjustment = 0
```

**Priority**: CRITICAL - Core UX requirement

---

### Phase 3: Health Score and Constraint Warnings (HIGH)

**File**: `coordinator.py`

**Changes**:
```python
def _calculate_health_score(self) -> tuple[int, str]:
    """Calculate system health score and status message.

    Returns:
        Tuple of (score 0-100, status message)
    """
    score = 100
    issues = []

    # Check for collapsed ranges
    for zone_id in self.zones:
        zone_data = self.data["zones"].get(zone_id, {})
        # Would need to track computed min/max in state
        if zone_data.get("min_brightness") >= zone_data.get("max_brightness"):
            score -= 20
            issues.append(f"{zone_id}: no adaptation range")

    # Check for unavailable switches
    unavailable = self._count_unavailable_switches()
    score -= (unavailable * 15)
    if unavailable > 0:
        issues.append(f"{unavailable} zones unavailable")

    # Check for mode conflicts
    if self._previous_mode is not None:
        issues.append("manual control active")

    # Generate status
    if score >= 90:
        status = "Healthy"
    elif score >= 70:
        status = "OK - " + ", ".join(issues)
    elif score >= 50:
        status = "Constrained - " + ", ".join(issues)
    else:
        status = "Degraded - " + ", ".join(issues)

    return (max(0, score), status)
```

**Priority**: HIGH - User needs visibility

---

### Phase 4: Per-Zone Feature Flags (MEDIUM)

**File**: `config_flow.py`, `coordinator.py`

**Changes**:
```python
# In config flow - add per-zone checkboxes
ZONE_SCHEMA = vol.Schema({
    vol.Required("zone_id"): str,
    vol.Required("lights"): selector.EntitySelector(...),
    vol.Optional("environmental_boost_enabled", default=True): bool,
    vol.Optional("sunset_boost_enabled", default=True): bool,
    ...
})

# In coordinator
if zone_config.get("environmental_boost_enabled", True):
    env_boost = self._env_adapter.calculate_boost()
else:
    env_boost = 0
```

**Priority**: MEDIUM - Nice to have, not critical

---

## Recommended Next Steps

1. **IMMEDIATE**: Implement Phase 1 (mode-aware features) - 2-3 hours
2. **CRITICAL**: Implement Phase 2 (auto-mode-switch) - 1-2 hours
3. **HIGH**: Implement Phase 3 (health score) - 1 hour
4. **MEDIUM**: Write unit tests - 2-3 hours
5. **MEDIUM**: Implement Phase 4 (per-zone flags) - 1 hour

**Total Estimated Time**: 7-11 hours to production-ready

---

## User Experience Validation

### Test Scenario 1: Dark Stormy Evening

**Setup**: 6PM, heavy rain, lux=400, user in living room

**Expected Behavior**:
1. Mode: ADAPTIVE (default)
2. Environmental boost: +10% (dark/rainy)
3. Sunset boost: +12% (dark day during sunset window)
4. Total: +22% brightness boost
5. Lights: Noticeably brighter than normal evening
6. **Result**: ✅ Comfortable despite storm

### Test Scenario 2: User Wants Sleep (Late Night)

**Setup**: 11PM, user sets LATE_NIGHT mode, outside is stormy (lux=0)

**Expected Behavior**:
1. Mode: LATE_NIGHT (max=25%)
2. Environmental boost: 0% (skipped due to mode)
3. Sunset boost: 0% (skipped due to mode)
4. Lights: Capped at 25%, very dim
5. **Result**: ✅ Dim for sleep, not fighting mode

### Test Scenario 3: Manual Override in Late Night

**Setup**: 11PM in LATE_NIGHT mode, user presses "brighter"

**Expected Behavior**:
1. Detect manual adjustment
2. Auto-switch to ADAPTIVE mode
3. Save previous mode (LATE_NIGHT)
4. Apply +10% adjustment
5. Start 30min timer (smart timeout for late night)
6. After timer: Restore LATE_NIGHT mode
7. **Result**: ✅ Responsive to manual input, returns to automation

### Test Scenario 4: Clear Sunny Day

**Setup**: 2PM, sunny, lux=15000, ADAPTIVE mode

**Expected Behavior**:
1. Environmental boost: 0% (lux too high)
2. Sunset boost: 0% (not sunset time)
3. Manual: 0% (no user adjustment)
4. Total: 0% offset
5. AL baseline: Follows normal daytime curve
6. **Result**: ✅ System stays out of the way

---

## Conclusion

The **core calculation modules are solid** and production-ready. The **critical issues are all in coordinator integration** - specifically:

1. Mode interaction logic not implemented
2. Features not wired together
3. User feedback missing

Once these are fixed, the system will deliver on the promise: **"Lights always exactly where they should be"** by properly respecting the hierarchy of user intent.

**Confidence**: HIGH - clear path to production quality
**Blockers**: None - just need implementation time
**Risk**: LOW - all issues identified and solvable

---

**Reviewer**: Senior HA Engineer
**Date**: 2025-10-01
**Status**: Ready for Implementation
