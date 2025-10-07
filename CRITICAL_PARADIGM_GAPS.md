# Critical Paradigm Gaps - Immediate Action Required

## Overview
After deep analysis of implementation_1.yaml, I've identified **12 core paradigms**. Most are already implemented in ALP, but 4 critical gaps need immediate attention.

---

## CRITICAL GAP #1: Manual Control Checking Before Application

### What Implementation_1 Does
```yaml
sequence:
  # ALWAYS check manual_control before applying
  - condition: template
    value_template: >
      {% set manual_list = state_attr(repeat.item.entity_id, 'manual_control') | default([]) %}
      {{ not (manual_list is iterable and manual_list is not string and manual_list | length > 0) }}

  # Only reached if manual_control is EMPTY
  - service: adaptive_lighting.change_switch_settings
```

### What ALP Needs to Verify
**File**: `coordinator.py` → `_apply_adjustments_to_zone()`

**Check**: Does it skip zones where AL has set manual_control?

**Why Critical**: Without this check, ALP fights with AL's own manual detection and scene stickiness breaks.

**Line to Check**: Around line 620-660 in coordinator.py

---

## CRITICAL GAP #2: Timer Expiry Apply Pattern

### What Implementation_1 Does
```yaml
# When timer expires, specify lights parameter for immediate restoration
- service: adaptive_lighting.set_manual_control
  data:
    entity_id: switch.adaptive_lighting_main_living
    manual_control: false

- service: adaptive_lighting.apply
  data:
    entity_id: switch.adaptive_lighting_main_living
    lights: light.main_living_lights  # ← FORCES immediate restoration
    transition: 2
    turn_on_lights: false
```

### What ALP Currently Does
```python
# coordinator.py line 886-895
await self.hass.services.async_call(
    ADAPTIVE_LIGHTING_DOMAIN,
    "apply",
    {
        "entity_id": al_switch,
        "turn_on_lights": False,
        # NO lights parameter! ← Different from implementation_1
    },
)
```

### The Question
Should ALP match implementation_1's pattern and specify the lights parameter on timer expiry?

**Rationale for YES**: Forces immediate restoration instead of waiting for AL's next cycle
**Rationale for NO**: Current pattern already works, lights param might override manual_control

**Needs**: Testing and decision

---

## CRITICAL GAP #3: Environmental Boost Sophistication

### What Implementation_1 Has
- **Logarithmic lux scaling**: 6 thresholds (10, 25, 50, 100, 200, 400)
- **Weather condition mapping**: 13 different conditions with specific boosts
- **Seasonal adjustments**: Winter +8%, Summer -3%
- **Time-of-day gating**: DISABLED 10 PM - 6 AM
- **Transition reduction**: 70% effectiveness during dawn/dusk
- **Maximum cap**: 25% total boost

### What ALP Currently Has
**File**: `features/environmental_adapter.py`

Simpler calculation that might miss edge cases.

### Action Required
**File to Review**: `features/environmental_adapter.py` → `calculate_boost()`

**Compare**: Current implementation vs IMPLEMENTATION_1_PARADIGMS.md § Paradigm 3

**Enhance**: Add missing sophistication (time gating, seasonal, transition reduction)

---

## CRITICAL GAP #4: Service Call Consistency

### Implementation_1 Service Call Rules

#### Rule 1: Always use `use_defaults: 'configuration'`
```yaml
- service: adaptive_lighting.change_switch_settings
  data:
    use_defaults: 'configuration'  # ← ALWAYS specified
    min_brightness: 55
    max_brightness: 100
```

#### Rule 2: Normal apply WITHOUT lights parameter
```yaml
- service: adaptive_lighting.apply
  data:
    entity_id: switch.adaptive_lighting_main_living
    turn_on_lights: false
    transition: 1
    # NO lights parameter - let AL use manual_control
```

#### Rule 3: Timer expiry apply WITH lights parameter
```yaml
- service: adaptive_lighting.apply
  data:
    entity_id: switch.adaptive_lighting_main_living
    lights: light.main_living_lights  # ← ONLY for timer expiry
    transition: 2
    turn_on_lights: false
```

### What ALP Needs
**Files to Review**:
1. `coordinator.py` → All `adaptive_lighting.change_switch_settings` calls
2. `coordinator.py` → All `adaptive_lighting.apply` calls
3. `services.py` → Service handlers that call AL

**Verify**:
- All change_switch_settings use `use_defaults: 'configuration'`
- All apply use `turn_on_lights: false`
- All apply use `transition: 1` or `transition: 2`
- Normal apply does NOT specify lights
- Only timer expiry specifies lights (if we decide to match implementation_1)

---

## Verification Checklist

### Immediate Checks (Do First)
- [ ] `coordinator.py:620-660` - Does `_apply_adjustments_to_zone()` check manual_control?
- [ ] `coordinator.py:636-653` - Does change_switch_settings use `use_defaults: 'configuration'`?
- [ ] `coordinator.py:646-653` - Does normal apply avoid specifying lights?
- [ ] `coordinator.py:886-895` - Should timer expiry apply specify lights?

### Enhancement Tasks (Do After SSH)
- [ ] `features/environmental_adapter.py` - Add time-of-day gating (disable 10 PM - 6 AM)
- [ ] `features/environmental_adapter.py` - Add seasonal adjustments (winter +8%, summer -3%)
- [ ] `features/environmental_adapter.py` - Add transition reduction (dawn/dusk 70%)
- [ ] `features/environmental_adapter.py` - Add logarithmic lux thresholds

### Testing Tasks (Do After Fixes)
- [ ] Test scene stickiness - apply "All Lights", verify lights stay at scene levels through AL refresh
- [ ] Test timer expiry - verify lights restore immediately (not after 30s)
- [ ] Test environmental boost - verify disabled at night (10 PM - 6 AM)
- [ ] Test manual control - verify system doesn't fight AL's own detection

---

## Summary

**Total Paradigms Identified**: 12
**Already Implemented Correctly**: 8
**Need Verification**: 2
**Need Enhancement**: 2

**Critical Files**:
1. `coordinator.py` - Manual control checking, service call patterns
2. `features/environmental_adapter.py` - Environmental boost sophistication

**Next Steps**:
1. Read `coordinator.py` lines 620-660 to verify manual_control checking
2. Read `features/environmental_adapter.py` to assess sophistication gap
3. Decide on timer expiry lights parameter question
4. Make fixes and test

See `IMPLEMENTATION_1_PARADIGMS.md` for complete analysis of all 12 paradigms.