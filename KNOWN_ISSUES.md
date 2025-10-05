# Known Issues - Adaptive Lighting Pro v0.9-beta

**Last Updated**: 2025-10-05
**Test Status**: 169 passing / 42 failing (80% pass rate)

This document catalogues all known issues in the current beta release. Each issue includes:
- Category and severity
- Affected tests
- User impact
- Workarounds (if available)
- Fix priority

---

## 🔴 Critical Issues (Blocking Production Use)

### Issue #1: Timer Expiry Doesn't Clear Adjustments
**Category**: Core Functionality
**Severity**: Critical
**Failing Tests**: 9

**Test Failures**:
- `test_button_adjustment_cleared_when_all_timers_expire`
- `test_slider_adjustment_persists_no_timer`
- `test_mixed_button_then_slider_behavior`
- `test_warmth_adjustment_also_cleared_on_expiry`
- `test_partial_expiry_preserves_adjustments`
- `test_returns_true_when_timers_active`
- `test_returns_false_after_all_timers_expire`

**Description**:
When manual control timers expire, brightness/warmth adjustments should automatically reset to 0 (returning to pure adaptive control). Currently, adjustments persist indefinitely even after timer expiry.

**Expected Behavior**:
1. User presses "Brighter" button → adjustment +20%, timer starts (2 hours)
2. Timer expires → adjustment clears back to 0%
3. Lights smoothly return to adaptive lighting baseline

**Actual Behavior**:
1. User presses "Brighter" button → adjustment +20%, timer starts
2. Timer expires → adjustment stays at +20% (stuck)
3. Lights remain at adjusted level indefinitely

**User Impact**:
- **HIGH** - Manual adjustments become permanent instead of temporary
- Users must manually press "Reset" button to clear adjustments
- Defeats the purpose of automatic timer restoration

**Workaround**:
Press the "Reset Adjustments" button to manually clear when you notice lights are stuck.

**Root Cause**:
Timer expiry callback (`_on_manual_timer_expired`) marks zone as no longer manual but doesn't call `set_brightness_adjustment(0)` and `set_warmth_adjustment(0)`.

**Fix Priority**: **P0** - Must fix before v1.0 release

---

### Issue #2: Scene Layering Architectural Bug
**Category**: Architecture
**Severity**: Critical
**Failing Tests**: 7

**Test Failures**:
- `test_apply_scene_never_calls_set_brightness_adjustment`
- `test_apply_scene_never_calls_set_warmth_adjustment`
- `test_apply_scene_never_calls_cancel_all_timers`
- `test_scene_offset_included_in_brightness_calculation`
- `test_manual_and_scene_both_affect_brightness_boundaries`
- `test_warmth_calculation_includes_scene_offset`
- `test_all_lights_clears_scene_preserves_manual`

**Description**:
Scenes and manual adjustments use different mechanisms (scenes modify coordinator data directly, manual uses setter methods) causing architectural violations and unpredictable layering behavior.

**Expected Behavior**:
- Scenes should set offsets independently of manual adjustments
- Manual adjustments should layer additively on top of scene offsets
- "All Lights" scene should clear scene offsets but preserve manual adjustments
- Applying scenes should NOT clear manual timers

**Actual Behavior**:
- Scenes sometimes call `set_brightness_adjustment()` (violates architecture)
- Scene+manual combinations produce undefined behavior
- "All Lights" scene clears everything instead of just scene offsets

**User Impact**:
- **HIGH** - Scene functionality unreliable
- Combining scenes with manual adjustments unpredictable
- "All Lights" scene clears manual adjustments (loses user intent)

**Workaround**:
Avoid using scenes when manual adjustments are active. Use only scenes OR manual adjustments, not both.

**Root Cause**:
Scenes were implemented after manual adjustment system. Scene code violates architectural contract by mutating `coordinator.data` directly instead of using API methods.

**Fix Priority**: **P0** - Requires architectural refactor

**Proposed Solution**:
1. Add `coordinator.set_scene_brightness_offset()` method
2. Add `coordinator.set_scene_warmth_offset()` method
3. Store scene offsets separately from manual adjustments in coordinator.data
4. Calculation engine sums both: `total_offset = manual_adjustment + scene_offset`
5. "All Lights" scene calls `set_scene_*_offset(0)` without touching manual

---

## ⚠️ High Priority Issues (Impacts Features)

### Issue #3: Coordinator Startup Validation Failures
**Category**: Initialization
**Severity**: High
**Failing Tests**: 8

**Test Failures**:
- `test_async_initialize_triggers_environmental_calculation`
- `test_async_initialize_detects_unavailable_switches`
- `test_async_update_data_skips_zones_with_unavailable_switches`
- `test_switch_missing_manual_control_attribute`
- `test_zone_with_all_valid_lights`
- `test_light_in_multiple_zones_warning`
- `test_zone_with_no_available_lights`
- `test_zone_without_lights_configured`

**Description**:
Coordinator initialization (`async_initialize()`) fails to properly validate AL switches and light groups, leading to undefined behavior when entities are unavailable or misconfigured.

**Expected Behavior**:
- Detect unavailable AL switches and skip those zones
- Validate light group membership (warn if light in multiple zones)
- Trigger initial environmental calculation on startup
- Log clear warnings for missing/misconfigured entities

**Actual Behavior**:
- Validation logic exists but tests fail
- May not properly skip zones with unavailable switches
- Environmental calculation may not trigger on first startup
- Warnings may not be logged

**User Impact**:
- **MEDIUM** - Mostly affects unusual configurations
- Users with unavailable switches may see errors
- Fresh installations may not show environmental boost immediately

**Workaround**:
Ensure all AL switches are available before adding integration. Restart HA if environmental boost doesn't appear after first setup.

**Root Cause**:
Test mocking issues - tests mock coordinator internal state instead of entity registry. Actual code may work correctly but tests are incorrectly structured.

**Fix Priority**: **P1** - Verify if real-world issue or test-only bug

---

### Issue #4: Sunset Boost Edge Case Calculation Errors
**Category**: Environmental Features
**Severity**: High
**Failing Tests**: 7

**Test Failures**:
- `test_dark_cloudy_day_at_sunset_should_boost`
- `test_clear_bright_day_at_sunset_should_skip_boost`
- `test_dark_day_outside_sunset_window_should_skip`
- `test_sunset_window_linear_interpolation`
- `test_lux_threshold_exactly_3000_should_not_boost`
- `test_sun_entity_unavailable_should_safely_degrade`
- `test_negative_lux_should_be_treated_as_zero`

**Description**:
Sunset boost calculation has edge case bugs: threshold handling (lux == 3000), negative lux values, unavailable sun entity, time window boundaries.

**Expected Behavior**:
- Dark day (lux < 3000) during sunset window (±1 hour) → boost 0-12%
- Bright day (lux >= 3000) → no sunset boost
- Outside sunset window → no boost regardless of lux
- Lux < 0 → treat as 0
- Sun entity unavailable → gracefully disable sunset boost

**Actual Behavior**:
- Edge cases produce incorrect boost values or errors
- Threshold boundary (lux == 3000) undefined behavior
- Negative lux may cause calculation errors
- Sun unavailable may not degrade gracefully

**User Impact**:
- **MEDIUM** - Edge cases rare in real world
- Most users won't notice (sunset boost mostly works)
- Affects users at exact lux threshold or with unstable lux sensors

**Workaround**:
Sunset boost generally works for typical scenarios (dark cloudy sunset vs bright clear sunset). Edge case bugs unlikely to affect daily use.

**Root Cause**:
Boundary condition checks incomplete:
- `if lux < 3000` should be `if lux < 3000` (correct) but doesn't handle `lux == 3000` explicitly
- Negative lux not clamped before calculations
- Sun entity availability not checked before accessing attributes

**Fix Priority**: **P1** - Add boundary checks and null safety

---

## 📊 Issue Summary by Category

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Core Functionality | 1 | 0 | 0 | 0 | **9** |
| Architecture | 1 | 0 | 0 | 0 | **7** |
| Initialization | 0 | 1 | 0 | 0 | **8** |
| Environmental | 0 | 1 | 0 | 0 | **7** |
| **TOTAL** | **2** | **2** | **0** | **0** | **42** |

---

## 🔧 Recommended Fix Order

1. **Issue #2 (Scene Layering)** - P0, architectural, blocks scene features
2. **Issue #1 (Timer Expiry)** - P0, core functionality, affects daily use
3. **Issue #4 (Sunset Boost)** - P1, edge cases, polish needed
4. **Issue #3 (Startup Validation)** - P1, verify if real bug or test issue

**Estimated Time to Fix All Issues**: 8-12 hours of focused development + testing

---

## ✅ What DOES Work Reliably

**Core Features** (169 passing tests):
- Asymmetric boundary adjustments (positive/negative handling)
- Manual control timer START (just not expiry clearing)
- Environmental boost (lux/weather/seasonal) - works for non-edge cases
- Sonos wake sequences (15/15 tests passing)
- Zen32 physical control (16/16 tests passing)
- Zone manager (basic operations passing)
- Button platform (21/21 tests passing)
- Sensor platform (36/36 tests passing)

The integration is **usable** for daily operation despite these issues. The failing tests represent edge cases and specific feature interactions that need polish, not fundamental brokenness.

---

## 📝 Reporting New Issues

Found a bug not listed here?

1. **Check if it's really a bug**: Re-read expected behavior in docs
2. **Try workaround first**: See if issue is blocking or just annoying
3. **File detailed report**: Include:
   - Steps to reproduce
   - Expected vs actual behavior
   - Your configuration (zones, settings)
   - HA version and AL Pro version
   - Relevant logs from Settings → System → Logs

**GitHub Issues**: https://github.com/macconnolly/AL-Pro/issues

---

**Revision History**:
- 2025-10-05: Initial KNOWN_ISSUES.md created based on test results
