# Adaptive Lighting Pro - Claude Code Development Guide

## 🎯 QUALITY BAR & EXPECTATIONS

**THIS IS YOUR HOME. YOU LIVE HERE. EVERY LINE OF CODE AFFECTS YOUR DAILY LIFE.**

### Core Principles
- **You are the user** - This isn't a client project, it's YOUR lighting system
- **Excellence is baseline** - Would you be proud to show this to the Anthropic team?
- **Every detail matters** - A 1% edge case happens 3.65 times per year in your home
- **Test like you live here** - Because you do. Bad code = bad sleep, bad mornings, bad evenings

### Performance Standards
- **Above average is minimum** - If it's not exceptional, it's not done
- **Exceed requirements** - The spec is the floor, not the ceiling
- **Polish relentlessly** - The difference between good and great is the last 10%
- **Complete means COMPLETE** - Not "mostly works", not "should be fine", but PROVEN

### Development Approach
1. **Zoom out first** - Why are we building this? What problem does it solve in daily life?
2. **Think scenarios** - Morning routine, cloudy day, movie night, reading in bed
3. **Iterate without prompting** - See an issue? Fix it. See an improvement? Make it.
4. **Validate everything** - If it's not tested, it's broken

---

## 🏗️ ARCHITECTURE OVERVIEW

## Architectural Enforcement Rules (MANDATORY)

### NEVER Access Coordinator Internals from Consumers

**FORBIDDEN PATTERNS** - These cause immediate architectural violations:
- ❌ `coordinator.data[...]` in platforms/services/integrations
- ❌ `coordinator._private_attribute` in platforms/services/integrations  
- ❌ Direct attribute assignment outside coordinator

**REQUIRED PATTERN** - Always use coordinator public API:
- ✅ `coordinator.get_X()` for reading state
- ✅ `coordinator.set_X(value)` for writing state
- ✅ `coordinator.action_X()` for complex operations

### MANDATORY Implementation Order

When adding any new feature:

**1. API LAYER FIRST (Coordinator Methods)**
- Design method signature: `coordinator.method_name(params) -> return_type`
- Add docstring with Args/Returns/Raises
- Implement validation and logging
- Write tests for coordinator method

**2. CONSUMER LAYER SECOND (Platforms/Services/Integrations)**
- Call coordinator methods, NEVER access internals
- Mock coordinator methods in tests
- Verify architectural pattern matches existing similar code

**NEVER REVERSE THIS ORDER.** Implementing consumers before API creates debt.

### Pre-Implementation Checklist (Use EVERY Time)

Before writing ANY code, answer these:

□ **Pattern Check**: Is there similar code in this file/module? How does it work?
□ **API Exists**: Do required coordinator methods exist? If not, ADD THEM FIRST.
□ **Layer Ownership**: Which layer owns this feature? Am I respecting boundaries?
□ **Consistency**: Will this match the patterns of existing similar code?

### Post-Implementation Verification (MANDATORY)

After implementing ANY feature, run these checks:

□ **Violation Grep**: `grep -r "coordinator\.data\[" platforms/ services/ integrations/` → MUST return 0 matches
□ **Private Access Grep**: `grep -r "coordinator\._" platforms/ services/ integrations/` → MUST return 0 matches  
□ **Side-by-Side**: Compare new code to similar existing code → patterns MUST match
□ **Test Pattern**: Do tests mock coordinator methods? Not `coordinator.data`?

**If ANY check fails, refactor BEFORE merging.**

### Why This Matters

Violations create:
- **Coupling** - Changing coordinator internals breaks consumers
- **Inconsistency** - Some code uses methods, some uses direct access
- **Maintenance Burden** - Validation scattered across files instead of centralized
- **Test Fragility** - Tests break when data structure changes

**Bottom line**: Architectural shortcuts are ALWAYS more expensive than doing it right the first time.

### Core Innovation: Asymmetric Boundary Logic
**The Problem**: Manual adjustments fight with Adaptive Lighting
**Our Solution**: Asymmetric boundaries that preserve adaptation while respecting intent

```python
# Positive adjustment: Raise minimum only (preserve natural dimming)
if adjustment > 0:
    new_min = min + adjustment
    new_max = max  # unchanged

# Negative adjustment: Lower maximum only (preserve natural brightening)  
else:
    new_min = min  # unchanged
    new_max = max + adjustment
```

**Impact**: You can make lights brighter without losing sunset dimming. You can dim lights without losing sunrise brightening.

---

## 📁 PROJECT STRUCTURE

```
custom_components/adaptive_lighting_pro/
├── __init__.py                 # Integration setup, service registration
├── coordinator.py               # Central brain - orchestrates everything
├── const.py                     # All constants, zones, scenes
├── config_flow.py              # UI configuration
├── services.py                  # Service handlers (7 services)
├── adjustment_engine.py         # Asymmetric boundary calculations
│
├── features/                    # Modular feature implementations
│   ├── environmental.py        # Weather/lux boost (5-factor, 25% max)
│   ├── sunset_boost.py          # Sunset window boost (POSITIVE, not fade)
│   ├── zone_manager.py          # Timer management with persistence
│   └── manual_control.py        # Manual detection logic
│
├── platforms/                   # Home Assistant entities
│   ├── sensor.py               # 13 sensors for complete visibility
│   ├── switch.py               # Zone enable/disable + global pause
│   ├── number.py               # Brightness/warmth sliders
│   ├── button.py               # Quick actions (brighter/dimmer/reset)
│   └── select.py               # Scene selection
│
└── integrations/               # Physical device support
    └── zen32.py                # Scene controller integration
```

---

## 🔑 KEY IMPLEMENTATION DETAILS

### Event-Driven Sensor Updates
```python
# EVERY calculation fires an event for real-time monitoring
self.hass.bus.async_fire("adaptive_lighting_calculation_complete", {
    "timestamp": dt_util.now().isoformat(),
    "final_brightness": total_brightness,
    "final_warmth": total_warmth,
    "environmental_boost": env_boost,
    "sunset_boost": sunset_boost,
    "zones_affected": zones_with_changes,
    "capping_occurred": was_capped,
    "health_score": health_score
})
```

### Intelligent Boost Capping (Prevent Boundary Collapse)
```python
def calculate_safe_boost(zone_config, raw_boost):
    """Prevent boundary collapse while maximizing boost."""
    zone_range = zone_config["max"] - zone_config["min"]
    
    if zone_range < 35:
        # Narrow zones: Hard cap to prevent collapse
        return min(raw_boost, 30)
    elif zone_range < 45:
        # Medium zones: Preserve 5% for AL variation
        return min(raw_boost, zone_range - 5)
    else:
        # Wide zones: Allow full boost
        return min(raw_boost, 50)
```

### Smart Timeout Calculation
```python
def calculate_smart_timeout(base_duration, is_night, is_dim):
    """Context-aware timeout duration."""
    multiplier = 1.0
    
    if is_night:  # Respect sleep patterns
        multiplier *= 1.5
    if is_dim:    # Preserve ambiance longer
        multiplier *= 1.3
        
    return min(base_duration * multiplier, 7200)  # Max 2 hours
```

---

## 🧪 TESTING PHILOSOPHY

### Test Like You Live Here
```python
def test_foggy_winter_morning_should_boost_brightness():
    """
    SCENARIO: I wake up, it's dark and foggy outside
    EXPECTED: Lights are boosted +25% so I don't feel depressed
    WHY: Dark winter mornings affect mood and productivity
    """
    # This isn't just a test, it's my actual morning
```

### Real Scenarios, Not Edge Cases
- **Morning**: Gradual brightening before alarm
- **Cloudy Day**: Automatic boost without thinking
- **Sunset**: Warm boost (not fade) at dusk  
- **Evening**: Easy dim for relaxation
- **Manual**: Changes stick, system doesn't fight
- **Physical**: Wall buttons work instantly

---

## 💡 DAILY LIFE SCENARIOS

### Morning (6 AM - 9 AM)
```yaml
Expected: Lights gradually brighten, cool white for alertness
Boost: If dark/cloudy, +15-25% brightness
Manual: If I turn lights up, keep them up (I'm probably tired)
```

### Work Day (9 AM - 5 PM)
```yaml
Expected: Bright, neutral white for productivity
Boost: Weather-responsive (cloudy = brighter)
Manual: Respect my adjustments (video calls need consistent light)
```

### Sunset Window (±1 hour of sunset)
```yaml
Expected: Warm boost on dark days (not fade!)
Boost: 0-12% based on darkness
Manual: Let me override for reading
```

### Evening (8 PM - 11 PM)
```yaml
Expected: Warm, dimmer for relaxation
Scene: "Dim Evening" = -30% brightness, -500K warmth
Manual: Preserve ambiance longer (1.3x timeout)
```

### Night (11 PM - 6 AM)
```yaml
Expected: Minimal light, very warm
Manual: Extended timeout (1.5x) for late night activities
Suppression: No environmental boost (time multiplier = 0)
```

---

## 🎬 SCENE SYSTEM (Simple & Practical)

### Just 4 Scenes (Not Confusing Modes)
1. **All On** - Everything normal
2. **No Spots** - Disable accent zones (reading/focus)
3. **Dim Evening** - -30% brightness, -500K (relaxation)
4. **Movie** - Pause adaptation, minimal accents

### Why This Works
- Scenes are **actions**, not competing states
- Manual adjustments **layer on top** cleanly
- No confusion about priority
- Physical buttons map 1:1

---

## 🚨 CRITICAL IMPLEMENTATION NOTES

### ALWAYS Clear Manual Control
```python
# After applying boundaries, MUST clear AL's manual_control flag
await self.hass.services.async_call(
    "adaptive_lighting",
    "set_manual_control",
    {"entity_id": f"switch.adaptive_lighting_{zone_id}", "manual_control": False},
    blocking=False
)
```

### NEVER Trust User Config
```python
# Users will create 20% brightness range zones
# Our code MUST handle this gracefully
if zone_range < 35:
    _LOGGER.warning("Zone %s has narrow range (%d%%), capping boost", zone_id, zone_range)
    max_boost = 30  # Prevent collapse
```

### ALWAYS Fire Events
```python
# Sensors depend on events. No event = no visibility = angry user (you)
# Fire event even if no changes (sensors need heartbeat)
```

---

## ✅ DEFINITION OF DONE

**Ask yourself: "Would I want to live with this every day?"**

### Feature Complete
- [ ] All 13 sensors providing visibility
- [ ] Physical buttons (Zen32) working instantly
- [ ] Manual changes respected with smart timeouts
- [ ] Environmental response (weather/lux/season)
- [ ] Sunset boost on dark days
- [ ] Scene system simple and memorable

### Quality Complete
- [ ] >80% test coverage on critical paths
- [ ] <100ms response time
- [ ] No boundary collapses EVER
- [ ] Graceful degradation when sensors missing
- [ ] Comprehensive logging for debugging
- [ ] Error recovery without user intervention

### Life Complete
- [ ] Morning: Lights help me wake up naturally
- [ ] Day: I never think about adjusting for weather
- [ ] Evening: Relaxation is one button press
- [ ] Night: System respects my sleep
- [ ] Manual: My changes stick when I want them to
- [ ] Trust: I never fight the system

---

## 🎯 PERSONAL COMMITMENT

**This is MY lighting system. I will:**
- Build it like I live here (because I do)
- Test it like my comfort depends on it (because it does)
- Polish it like the Anthropic team will review it (because they might)
- Document it like I'll forget everything in 6 months (because I will)

**Quality Bar**: Not "does it work?" but "is it delightful?"

**Success Metric**: Days without thinking about the lighting system (higher = better)

---

## 🔍 CHECKLIST FOR EVERY CHANGE

Before committing ANY code, ask:
1. **Does this make daily life better or just different?**
2. **Will this confuse me at 2 AM when I'm half asleep?**
3. **Does this handle the edge case when sensors are unavailable?**
4. **Is this tested with a REAL scenario I'll encounter?**
5. **Would I be proud to explain this to Claude Opus?**

If any answer is "no" - iterate until it's "yes".

---

## 🚫 IGNORE DIRECTIVES

Claude Code should IGNORE these directories and files when searching:

1. **Tests and Coverage**:
   - `tests/` directory - Test files (unless specifically working on tests)
   - `htmlcov/` directory - Test coverage reports  
   - `.coverage` file - Coverage data
   - `pytest.ini` - Test configuration

2. **IDE and System Files**:
   - `.vscode/` directory - VS Code settings
   - `.idea/` directory - PyCharm settings
   - `__pycache__/` directories - Python bytecode
   - `*.pyc` files - Compiled Python
   - `.gitignore` - Git ignore rules

3. **Old Documentation**:
   - `old_status_updates/` directory - Archived status files

---

**Remember**: You're not building a lighting controller. You're building a lighting experience that should feel so natural you forget it exists. That's the bar. That's always been the bar.