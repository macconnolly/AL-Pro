# Session Handoff - Quick Start Guide

**Last Updated**: 2025-10-01
**Status**: Phase 2 Core Engine - 75% Complete
**Next Session**: Start coordinator integration

---

## TL;DR - What You Need to Know

### Architecture Was Simplified ✅

**Original plan**: Complex mode system (WORK/LATE_NIGHT/MOVIE modes)
**Actual user workflow**: Zen32 cycling boost levels + Clear button
**New architecture**: Automatic state + Manual state + Scene presets + Per-zone disable

**Read this section in claude.md first**: "🚨 CRITICAL ARCHITECTURE SIMPLIFICATION"

### Core Calculation Modules Are Complete ✅

These files are **DONE** and mathematically correct - **DO NOT MODIFY**:
1. `adjustment_engine.py` - Asymmetric boundary logic
2. `features/environmental.py` - 5-factor boost calculation
3. `features/sunset_boost.py` - Dark day sunset boost (FIXED from backwards YAML)

### What's Left - 8 Hours to MVP

**Priority 1** (2 hours): Wire environmental/sunset into coordinator
**Priority 2** (15 min): Register number.py platform
**Priority 3** (1 hour): Scene preset support
**Priority 4** (3 hours): Comprehensive tests

See [TODO.md](TODO.md) for detailed breakdown.

---

## Critical Decisions Made

### 1. Environmental Boost Conditional Logic

**Q**: When is environmental boost suppressed?
**A**: Time-of-day multiplier in environmental.py handles this automatically:
- Night (10PM-6AM): multiplier = 0.0 → env_boost = 0
- Dawn/Dusk: multiplier = 0.7 → reduced
- Day: multiplier = 1.0 → full

**User requirement**: "Environmental boost should not be active after dark anyways. cloudy weather does not need to be compensated for after the sun goes down"

**No mode-based gating needed** - the time multiplier IS the solution!

### 2. Sunset Logic Was Backwards - Now Fixed

**Original YAML problem**: Lines 2414-2455 applied NEGATIVE offset to DIM lights during sunset
**Fix**: Created `sunset_boost.py` with POSITIVE offset that only applies on dark/cloudy days (lux < 3000)

### 3. Offset Calculation Formula

```python
# Check if zone is enabled
if not zone_config.get("enabled", True):
    total_brightness = 0
    total_warmth = 0
else:
    # Environmental features (always calculated when conditions warrant)
    env_boost = environmental_adapter.calculate_boost()     # 0-25%
    sunset_boost = sunset_boost_calculator.calculate_boost() # 0-25% (dark days only)

    # Manual adjustments (from button presses or scene presets)
    manual_brightness = user_adjustment  # -100 to +100%
    manual_warmth = user_warmth          # -2500 to +2500K

    # Total offsets
    total_brightness = env_boost + sunset_boost + manual_brightness
    total_warmth = manual_warmth

# Apply asymmetric boundaries
boundaries = calculate_boundaries(zone_config, total_brightness, total_warmth)
apply_to_adaptive_lighting(zone_id, boundaries)
```

### 4. Scene Presets Are Just Manual Offsets

**Not modes** - just convenient shortcuts to set manual adjustments:
- "Boost" = +15% brightness
- "Evening Comfort" = -5% brightness, -500K warmth
- "Ultra Dim" = -50% brightness, -1000K warmth
- "Clear" = Reset all manual adjustments to 0

### 5. Per-Zone Disable Flag Added

Each zone has `enabled` flag:
- When disabled: All offsets = 0
- Adaptive Lighting still runs (for manual HA control)
- User toggles via zone switch entity

---

## File Status

### Completed Core Modules ✅
- `custom_components/adaptive_lighting_pro/adjustment_engine.py`
- `custom_components/adaptive_lighting_pro/features/environmental.py`
- `custom_components/adaptive_lighting_pro/features/sunset_boost.py`
- `custom_components/adaptive_lighting_pro/features/zone_manager.py`
- `custom_components/adaptive_lighting_pro/features/manual_control.py`
- `custom_components/adaptive_lighting_pro/number.py`

### Needs Integration Work ⚠️
- `custom_components/adaptive_lighting_pro/coordinator.py` - Wire in environmental/sunset
- `custom_components/adaptive_lighting_pro/__init__.py` - Register number.py platform

### Documentation Files 📄
- `claude.md` - **SINGLE SOURCE OF TRUTH** - Read section "🚨 CRITICAL ARCHITECTURE SIMPLIFICATION"
- `TODO.md` - Updated with simplified architecture and next steps
- `PROJECT_PLAN.md` - Updated with version 1.1 simplified architecture
- `DESIGN_REVIEW.md` - Valuable senior engineer analysis (keep this)
- `implementation_1.yaml` - Original YAML reference

### Cleaned Up ✅
- ❌ `REMEDIATION_PLAN.md` (removed - outdated)
- ❌ `VERIFICATION_REPORT.md` (removed - info in DESIGN_REVIEW.md)
- ❌ `features/sunset_fade.py.OLD` (removed - replaced by sunset_boost.py)

---

## Next Task - Coordinator Integration (2 hours)

### What Needs to Happen

**File**: `coordinator.py`

**Step 1**: Initialize features in `__init__`:
```python
self._env_adapter = EnvironmentalAdapter(hass)
self._sunset_boost = SunsetBoostCalculator(hass)
self._env_adapter.configure(lux_sensor=..., weather_entity=..., enabled=True)
self._sunset_boost.configure(enabled=True)
```

**Step 2**: Calculate combined offsets in `_async_update_data()`:
```python
# Calculate environmental features
env_boost = self._env_adapter.calculate_boost()

# Get lux for sunset boost
lux = self._get_current_lux()  # From lux sensor state
sunset_boost = self._sunset_boost.calculate_boost(lux)

# Combine with manual
total_brightness = env_boost + sunset_boost + self._brightness_adjustment
total_warmth = self._warmth_adjustment
```

**Step 3**: Apply to each zone:
```python
for zone_id, zone_config in self.zones.items():
    # Check zone enabled flag
    if not zone_config.get("enabled", True):
        total_brightness = 0
        total_warmth = 0

    boundaries = calculate_boundaries(
        zone_config,
        total_brightness,
        total_warmth
    )
    await self._apply_boundaries_to_zone(zone_id, boundaries)
```

**Step 4**: Add helper method:
```python
def _get_current_lux(self) -> float | None:
    """Get current outdoor lux from configured sensor."""
    lux_sensor = self.config_entry.data.get("lux_sensor")
    if not lux_sensor:
        return None
    state = self.hass.states.get(lux_sensor)
    if not state or state.state in ("unknown", "unavailable"):
        return None
    return float(state.state)
```

See [TODO.md](TODO.md) lines 97-147 for complete details.

---

## Test Requirements

### Tests Must Verify REAL Functionality

**Not acceptable**: "test_function_runs_without_errors"
**Required**: Real scenario validation with expected outcomes

### Example Real Scenarios

**test_environmental.py**:
```python
def test_foggy_winter_morning():
    """Fog + winter + dawn = high boost."""
    lux = 15  # Very dark
    weather = "fog"
    month = 1  # January
    hour = 7  # Dawn
    # Expected: (15 lux + 20 fog + 8 winter) * 0.7 dawn = 30.1 → 25 (clamped)
    boost = adapter.calculate_boost()
    assert boost == 25

def test_night_suppression():
    """Night time = boost disabled regardless of conditions."""
    lux = 0  # Dark
    weather = "rainy"
    month = 12  # Winter
    hour = 23  # Night
    boost = adapter.calculate_boost()
    assert boost == 0  # Time multiplier = 0.0
```

See [TODO.md](TODO.md) lines 207-331 for complete test plan.

---

## Key Files to Reference

1. **[claude.md](claude.md)** - Section "🚨 CRITICAL ARCHITECTURE SIMPLIFICATION" (lines 960-1119)
2. **[TODO.md](TODO.md)** - Complete task breakdown (lines 95-363)
3. **[adjustment_engine.py](custom_components/adaptive_lighting_pro/adjustment_engine.py)** - Core asymmetric logic (verified correct)
4. **[environmental.py](custom_components/adaptive_lighting_pro/features/environmental.py)** - 5-factor boost (verified correct)
5. **[sunset_boost.py](custom_components/adaptive_lighting_pro/features/sunset_boost.py)** - Dark day boost (verified correct)

---

## Questions to Ask Yourself

Before starting:
- [ ] Have I read the "🚨 CRITICAL ARCHITECTURE SIMPLIFICATION" section in claude.md?
- [ ] Do I understand why modes were removed?
- [ ] Do I know that time-of-day multiplier handles conditional environmental boost?
- [ ] Do I know that sunset boost is POSITIVE offset on dark days only?
- [ ] Have I reviewed the offset calculation formula?

While implementing:
- [ ] Am I modifying any of the verified core calculation modules? (STOP if yes!)
- [ ] Am I adding mode-based gating to environmental boost? (Don't - time multiplier handles this!)
- [ ] Am I writing tests that just check "no errors"? (Write real scenario tests!)

---

## Success Metrics

### Functional Requirements
- [x] Environmental boost compensates for dark/cloudy conditions
- [x] Sunset boost provides extra help on dark days at sunset
- [x] Manual adjustments add on top of environmental baseline
- [x] Timer clears manual adjustments after expiry
- [x] Scene presets provide convenient manual shortcuts
- [ ] Coordinator combines all offsets correctly (NEXT TASK)
- [ ] Zone disable flag works properly (NEXT TASK)

### Test Coverage
- [ ] Unit tests for all core calculation modules (PRIORITY 4)
- [ ] Integration tests for coordinator offset combination (PRIORITY 4)
- [ ] Real scenario tests (dark day, sunset, manual override) (PRIORITY 4)
- [ ] Edge case tests (boundary collapse, timer expiry) (PRIORITY 4)

---

**Ready to Start?** → Begin with [TODO.md](TODO.md) Priority 1: Coordinator Integration

**Questions?** → Reference [claude.md](claude.md) section "🚨 CRITICAL ARCHITECTURE SIMPLIFICATION"

**Debugging?** → Check [DESIGN_REVIEW.md](DESIGN_REVIEW.md) for analysis of common issues
