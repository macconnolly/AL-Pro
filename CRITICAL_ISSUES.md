# Critical Issues - Adaptive Lighting Pro v0.9-beta

**Last Updated**: 2025-10-05
**Purpose**: Document all critical issues preventing production deployment with detailed fixes
**Scope**: Personal home deployment (not HACS release)

---

## 🚨 CRITICAL ISSUES (Must Fix Before Deployment)

### Issue #1: Wake Sequence Doesn't Override Manual Control
**Severity**: CRITICAL - Core feature broken
**Location**: `custom_components/adaptive_lighting_pro/coordinator.py` lines 349-367
**Test Impact**: Will break 21 tests when fixed (need tuple handling)

**Problem**:
The wake sequence only checks if boost > 0 but doesn't actually clear manual control on the AL switch. This means if a user manually adjusted lights at 5:30am, the 6:00am wake sequence won't activate because AL thinks the lights are still manually controlled.

**Current Code** (coordinator.py:349-367):
```python
# Check if wake sequence is active for this zone
wake_in_progress = (
    zone_config.get("wake_sequence_enabled", True)
    and self._wake_sequence.calculate_boost(zone_id) > 0
)

if wake_in_progress:
    wake_boost = self._wake_sequence.calculate_boost(zone_id)
    _LOGGER.debug(f"Wake sequence active for zone {zone_id}: {wake_boost}% boost")
```

**Required Fix**:
```python
# Check if wake sequence is active for this zone
wake_in_progress = (
    zone_config.get("wake_sequence_enabled", True)
    and self._wake_sequence.calculate_boost(zone_id) > 0
)

if wake_in_progress:
    wake_boost = self._wake_sequence.calculate_boost(zone_id)
    _LOGGER.debug(f"Wake sequence active for zone {zone_id}: {wake_boost}% boost")

    # CRITICAL: Force clear manual control during wake sequence
    # Wake sequence MUST override any previous manual adjustments
    zone_lights = zone_config.get("lights", [])
    if zone_lights:
        await self.hass.services.async_call(
            "adaptive_lighting",
            "set_manual_control",
            {
                "entity_id": f"switch.adaptive_lighting_{zone_id}",
                "lights": zone_lights,
                "manual_control": False
            },
            blocking=False
        )
        _LOGGER.info(f"Cleared manual control for wake sequence in zone {zone_id}")
```

**User Impact**: Wake alarms won't work if any manual adjustment was made during the night.

---

### Issue #2: Button Platform Doesn't Set Manual Control on AL Switches
**Severity**: CRITICAL - User actions ignored
**Location**: `custom_components/adaptive_lighting_pro/platforms/button.py` lines 50-85

**Problem**:
When users press brightness/warmth adjustment buttons, the integration changes the lights but doesn't tell the Adaptive Lighting integration about manual control. Result: User presses "Brighter" button, lights get brighter for 30 seconds, then AL changes them back.

**Current Code** (button.py:50-85):
```python
async def async_press(self) -> None:
    """Handle button press."""
    zone_id = self._zone_id
    adjustment_type = self._adjustment_type
    adjustment_value = self._adjustment_value

    if adjustment_type == "brightness":
        await self.coordinator.set_brightness_adjustment(zone_id, adjustment_value)
    elif adjustment_type == "warmth":
        await self.coordinator.set_warmth_adjustment(zone_id, adjustment_value)
```

**Required Fix**:
```python
async def async_press(self) -> None:
    """Handle button press.

    Sets adjustment AND notifies AL about manual control to prevent fighting.
    """
    zone_id = self._zone_id
    adjustment_type = self._adjustment_type
    adjustment_value = self._adjustment_value

    # Step 1: Apply the adjustment
    if adjustment_type == "brightness":
        await self.coordinator.set_brightness_adjustment(zone_id, adjustment_value)
    elif adjustment_type == "warmth":
        await self.coordinator.set_warmth_adjustment(zone_id, adjustment_value)

    # Step 2: CRITICAL - Tell AL about manual control
    zone_config = self.coordinator.data.get("zones", {}).get(zone_id, {})
    zone_lights = zone_config.get("lights", [])

    if zone_lights:
        # Mark these specific lights as manually controlled
        await self.coordinator.hass.services.async_call(
            "adaptive_lighting",
            "set_manual_control",
            {
                "entity_id": f"switch.adaptive_lighting_{zone_id}",
                "lights": zone_lights,
                "manual_control": True
            },
            blocking=False
        )
        _LOGGER.debug(
            f"Set manual control for {len(zone_lights)} lights in zone {zone_id} "
            f"after {adjustment_type} adjustment of {adjustment_value}"
        )
```

**Also Required in** `platforms/select.py` when scenes are selected:
```python
# After applying scene in async_select_option():
if zone_lights and option_value != Scene.NONE:
    await self.coordinator.hass.services.async_call(
        "adaptive_lighting",
        "set_manual_control",
        {
            "entity_id": f"switch.adaptive_lighting_{zone_id}",
            "lights": zone_lights,
            "manual_control": True
        },
        blocking=False
    )
```

**User Impact**: Every button press is undone 30 seconds later by AL.

---

### Issue #3: Environmental Time Multiplier Uses Clock Instead of Sun
**Severity**: HIGH - Feature works backwards
**Location**: `custom_components/adaptive_lighting_pro/features/environmental.py` lines 318-360

**Problem**:
The time multiplier reduces environmental boost during early morning hours (6-8am gets 0.7x) based on CLOCK TIME. This is backwards - dark winter mornings at 7am need MORE boost, not less! Should use sun elevation exclusively.

**Current Code** (environmental.py:318-360):
```python
def _calculate_time_multiplier(self) -> float:
    """Calculate time-based multiplier with intelligent fallbacks."""
    try:
        # Try sun-based calculation first
        sun_state = self.hass.states.get("sun.sun")
        if sun_state and sun_state.attributes.get("elevation") is not None:
            elevation = float(sun_state.attributes.get("elevation"))
            # ... sun logic ...
        else:
            # PROBLEM: Falls back to clock time!
            current_hour = datetime.now().hour
            if 6 <= current_hour < 8:  # Early morning
                return 0.7
            elif 8 <= current_hour < 10:  # Morning
                return 0.85
            # ... more clock-based logic ...
```

**Required Fix**:
```python
def _calculate_time_multiplier(self) -> float:
    """Calculate time-based multiplier using sun elevation only.

    Returns 1.0 if sun data unavailable rather than reducing boost
    during clock-based morning hours which may still be dark.
    """
    try:
        sun_state = self.hass.states.get("sun.sun")
        if sun_state and sun_state.attributes.get("elevation") is not None:
            elevation = float(sun_state.attributes.get("elevation"))

            if elevation < -12:  # Nautical twilight
                return 0.0  # Night - no environmental boost needed
            elif -12 <= elevation < -6:  # Between nautical and civil twilight
                return 0.3  # Very early dawn
            elif -6 <= elevation < 0:  # Civil twilight to sunrise
                return 0.7  # Dawn/dusk transitional period
            elif 0 <= elevation < 6:  # Just after sunrise/before sunset
                return 0.85  # Early morning/late evening
            else:  # elevation >= 6
                return 1.0  # Full daylight
        else:
            # NO SUN DATA - return neutral rather than penalizing mornings
            _LOGGER.warning(
                "Sun elevation unavailable for time multiplier, using neutral 1.0"
            )
            return 1.0  # Don't reduce boost when we can't determine sun position

    except Exception as e:
        _LOGGER.error(f"Error calculating time multiplier: {e}")
        return 1.0  # Safe default - don't reduce boost on errors
```

**User Impact**: Dark winter mornings get LESS brightness boost (opposite of intended).

---

### Issue #4: Sunset Boost Missing Warmth Component
**Severity**: HIGH - Feature incomplete
**Location**: `custom_components/adaptive_lighting_pro/features/sunset_boost.py` lines 63-177
**Test Files Affected**: 21 test files expecting int, need tuple[int, int]

**Problem**:
Sunset boost only returns brightness adjustment. The whole point of sunset compensation is the "golden hour" warm glow. Without warmth adjustment, it's just making lights brighter at sunset without the aesthetic color shift.

**Current Code** (sunset_boost.py:63-177):
```python
def calculate_boost(
    self, zone_id: str, current_lux: float | None = None
) -> int:  # Returns only brightness!
    """Calculate brightness boost percentage during sunset."""
    # ... calculation ...
    return final_boost  # Just an int
```

**Required Fix**:
```python
from typing import NamedTuple

class BoostResult(NamedTuple):
    """Result from boost calculation containing both brightness and warmth."""
    brightness: int  # Percentage boost for brightness (0-100)
    warmth: int     # Kelvin adjustment for color temp (negative = warmer)

def calculate_boost(
    self, zone_id: str, current_lux: float | None = None
) -> BoostResult:
    """Calculate brightness AND warmth boost during sunset.

    Returns:
        BoostResult with brightness percentage and warmth Kelvin adjustment.
        Warmth is negative to make lights warmer (e.g., -500K).
    """
    try:
        sun_state = self.hass.states.get("sun.sun")
        if not sun_state:
            return BoostResult(0, 0)

        elevation = float(sun_state.attributes.get("elevation", 90))

        # Existing brightness calculation
        if not (-4 <= elevation <= 4):  # Outside sunset window
            return BoostResult(0, 0)

        # ... existing brightness calculation ...
        brightness_boost = int(final_boost)

        # NEW: Calculate warmth adjustment for golden hour
        # Maximum warmth at horizon (0°), decreasing as we move away
        if elevation <= 0:
            # Below horizon: maximum warmth that decreases with depth
            warmth_factor = min(1.0, (4 + elevation) / 4)  # 1.0 at 0°, 0 at -4°
        else:
            # Above horizon: warmth decreases as sun rises
            warmth_factor = (4 - elevation) / 4  # 1.0 at 0°, 0 at 4°

        # Apply darkness multiplier to warmth too
        darkness_mult = self._calculate_darkness_multiplier(current_lux)
        warmth_factor *= darkness_mult

        # Convert to Kelvin adjustment (max -500K for very warm golden hour)
        warmth_adjustment = -int(warmth_factor * 500)

        _LOGGER.debug(
            f"Sunset boost for {zone_id}: "
            f"brightness={brightness_boost}%, warmth={warmth_adjustment}K "
            f"(elevation={elevation:.1f}°, lux={current_lux})"
        )

        return BoostResult(brightness_boost, warmth_adjustment)

    except Exception as e:
        _LOGGER.error(f"Error calculating sunset boost: {e}")
        return BoostResult(0, 0)
```

**Required Coordinator Update** (coordinator.py:405-420):
```python
# In async_update():
if zone_config.get("sunset_boost_enabled", True):
    boost_result = self._sunset_boost.calculate_boost(zone_id, current_lux)
    adjustments["sunset_brightness_boost"] = boost_result.brightness
    adjustments["sunset_warmth_offset"] = boost_result.warmth  # NEW!
```

**Test Updates Required**: All 21 test files mocking sunset boost need:
```python
# OLD:
mock_sunset.calculate_boost.return_value = 15

# NEW:
from custom_components.adaptive_lighting_pro.features.sunset_boost import BoostResult
mock_sunset.calculate_boost.return_value = BoostResult(15, -200)
```

**User Impact**: Sunset boost makes lights brighter but not warmer (missing golden hour aesthetic).

---

### Issue #5: Services Missing Temporary Parameter
**Severity**: MEDIUM - Automation limitation
**Location**: `custom_components/adaptive_lighting_pro/services.py` and `services.yaml`

**Problem**:
All service adjustments are temporary (start timers). Automations might want persistent adjustments that don't expire. For example, "Kids studying" automation wants brightness boost until explicitly cleared.

**Current services.yaml**:
```yaml
adjust_brightness:
  description: Adjust brightness for a zone
  fields:
    zone_id:
      description: The zone to adjust
    adjustment:
      description: Brightness adjustment (-100 to 100)
```

**Required Fix** (services.yaml):
```yaml
adjust_brightness:
  description: Adjust brightness for a zone
  fields:
    zone_id:
      description: The zone to adjust
      required: true
      selector:
        text:
    adjustment:
      description: Brightness adjustment percentage (-100 to 100)
      required: true
      selector:
        number:
          min: -100
          max: 100
    temporary:
      description: >
        If true (default), adjustment expires after manual_timeout.
        If false, adjustment persists until explicitly cleared.
      default: true
      selector:
        boolean:
```

**Required Fix** (services.py:35-89):
```python
async def adjust_brightness(call: ServiceCall) -> None:
    """Handle brightness adjustment service call."""
    zone_id = call.data.get("zone_id")
    adjustment = call.data.get("adjustment")
    temporary = call.data.get("temporary", True)  # NEW parameter

    coordinator = hass.data[DOMAIN]["coordinator"]

    # Apply adjustment
    await coordinator.set_brightness_adjustment(zone_id, adjustment)

    # Only start timer if temporary
    if temporary:
        timeout = coordinator.data["zones"][zone_id].get("manual_timeout", 1800)
        # Start timer for auto-clear
        async_call_later(
            hass,
            timeout,
            lambda: coordinator.set_brightness_adjustment(zone_id, 0)
        )
        _LOGGER.info(
            f"Temporary brightness adjustment {adjustment}% for {zone_id}, "
            f"expires in {timeout}s"
        )
    else:
        _LOGGER.info(
            f"Persistent brightness adjustment {adjustment}% for {zone_id}"
        )
```

**User Impact**: Automations can't make persistent adjustments.

---

### Issue #6: Scene Timer Behavior Undefined
**Severity**: MEDIUM - Confusing UX
**Location**: `custom_components/adaptive_lighting_pro/coordinator.py` lines 623-671

**Problem**:
When a scene is applied, it's unclear if it should:
1. Be temporary (start a timer like manual adjustments)
2. Be persistent until another scene is selected
3. Depend on the scene type (COZY temporary, MANUAL persistent)

**Current Code** (coordinator.py:623-671):
```python
async def apply_scene(self, zone_id: str, scene: Scene) -> None:
    """Apply scene to a zone."""
    # ... apply scene offsets ...
    # No timer logic at all!
```

**Required Fix - Option 1 (All Temporary)**:
```python
async def apply_scene(self, zone_id: str, scene: Scene) -> None:
    """Apply scene to a zone (temporary with timer)."""

    # ... existing scene application ...

    # Start timer for all scenes except NONE and MANUAL
    if scene not in [Scene.NONE, Scene.MANUAL]:
        # Use extended timeout for scenes (2x normal)
        base_timeout = self.data["zones"][zone_id].get("manual_timeout", 1800)
        scene_timeout = base_timeout * 2

        # Schedule scene clear
        self._scene_timers[zone_id] = async_call_later(
            self.hass,
            scene_timeout,
            lambda: self.apply_scene(zone_id, Scene.NONE)
        )
        _LOGGER.info(
            f"Scene {scene.value} applied to {zone_id}, expires in {scene_timeout}s"
        )
```

**Required Fix - Option 2 (Scene-Specific)**:
```python
# In const.py, add to SCENE_CONFIGS:
SCENE_CONFIGS = {
    Scene.COZY: {
        "brightness_offset": -40,
        "warmth_offset": -500,
        "persistent": False,  # Temporary scene
        "timeout_multiplier": 3,  # 3x normal timeout
    },
    Scene.MANUAL: {
        "brightness_offset": 0,
        "warmth_offset": 0,
        "persistent": True,  # Stays until changed
    },
    # ...
}
```

**User Impact**: Users don't know if scenes will expire or stay active.

---

### Issue #7: SCENE_CONFIGS Contains Hardcoded User-Specific Entities
**Severity**: CRITICAL - Blocks other users
**Location**: `custom_components/adaptive_lighting_pro/const.py` lines 580-691

**Problem**:
The SCENE_CONFIGS contains entity IDs specific to YOUR home. Any other user who installs this integration will get errors because they don't have "light.accent_spots_lights".

**Current Code** (const.py:580-691):
```python
SCENE_CONFIGS = {
    Scene.ALL_LIGHTS: {
        "brightness_offset": 0,
        "actions": [
            {"action": "light.turn_on", "entity_id": ["light.accent_spots_lights"]},
            {"action": "light.turn_on", "entity_id": ["light.kitchen_island_lights"]},
            # MORE HARDCODED ENTITIES!
        ]
    }
}
```

**Required Fix**:
```python
# const.py - Remove ALL entity-specific content:
SCENE_CONFIGS = {
    Scene.ALL_LIGHTS: {
        "brightness_offset": 0,
        "warmth_offset": 0,
        "description": "Reset to adaptive defaults with all lights on"
    },
    Scene.COZY: {
        "brightness_offset": -40,
        "warmth_offset": -500,
        "description": "Warm, dim lighting for evening relaxation"
    },
    Scene.FOCUS: {
        "brightness_offset": 30,
        "warmth_offset": 1000,
        "description": "Bright, cool lighting for concentration"
    },
    Scene.MANUAL: {
        "brightness_offset": 0,
        "warmth_offset": 0,
        "description": "Pause adaptive changes, maintain current state"
    },
    Scene.NONE: {
        "brightness_offset": 0,
        "warmth_offset": 0,
        "description": "No scene active"
    }
}
```

**Move Choreography to implementation_2.yaml**:
```yaml
# implementation_2.yaml
script:
  apply_scene_all_lights:
    sequence:
      # Step 1: Apply scene offsets to AL Pro
      - service: adaptive_lighting_pro.apply_scene
        data:
          zone: main_living
          scene: all_lights

      # Step 2: User-specific light choreography
      - service: light.turn_on
        target:
          entity_id:
            - light.accent_spots_lights  # User's specific lights
            - light.kitchen_island_lights
            - light.fireplace_accent_light
```

**User Impact**: Integration fails on any system except yours.

---

## 🟡 UX ISSUES (Should Fix)

### Issue #8: Sensor Platform Shows Raw Seconds
**Location**: `custom_components/adaptive_lighting_pro/platforms/sensor.py` lines 146-169

**Problem**: Shows "3247 seconds" instead of human-readable "54 minutes" or "1.2 hours"

**Fix**:
```python
@property
def native_value(self) -> StateType:
    """Return timer remaining in seconds for graphs, history."""
    # ... existing calculation ...
    return remaining_seconds  # Keep raw for history graphs

@property
def state(self) -> str:
    """Return human-readable timer remaining for UI display."""
    remaining = self.native_value
    if remaining is None or remaining <= 0:
        return "Expired"

    # Convert to human readable
    if remaining < 60:
        return f"{int(remaining)} seconds"
    elif remaining < 3600:
        minutes = remaining / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = remaining / 3600
        return f"{hours:.1f} hours"
```

---

### Issue #9: No Smart Timeout Scaling
**Location**: `custom_components/adaptive_lighting_pro/coordinator.py`

**Problem**: Late night dim scenes should have longer timeouts than bright daytime adjustments

**Implementation Required**:
```python
def calculate_smart_timeout(
    self,
    zone_id: str,
    base_timeout: int,
    adjustment_type: str
) -> int:
    """Calculate intelligent timeout based on context."""

    # Time-based scaling
    hour = datetime.now().hour
    if 22 <= hour or hour < 6:  # Late night
        time_multiplier = 2.0
    elif 6 <= hour < 8:  # Early morning
        time_multiplier = 1.5
    else:
        time_multiplier = 1.0

    # Adjustment-based scaling
    if adjustment_type == "scene":
        current_scene = self.data["zones"][zone_id].get("scene_active")
        if current_scene == Scene.COZY:
            scene_multiplier = 3.0  # Cozy scenes last longer
        elif current_scene == Scene.MANUAL:
            return 0  # Manual never expires
        else:
            scene_multiplier = 1.5
    else:
        scene_multiplier = 1.0

    return int(base_timeout * time_multiplier * scene_multiplier)
```

---

### Issue #10: Wake Sequence Lacks Notification System
**Location**: Missing feature

**Problem**: Users don't know if wake sequence activated successfully

**Required Implementation**:
```python
# In coordinator.py when wake sequence starts:
await self.hass.services.async_call(
    "notify",
    "persistent_notification",
    {
        "title": "Wake Sequence Started",
        "message": f"Good morning! Wake sequence active in {zone_id} "
                   f"for {duration} minutes with {wake_boost}% boost",
        "notification_id": f"wake_sequence_{zone_id}"
    }
)
```

---

## 📊 MISSING FEATURES FROM IMPLEMENTATION_1

### Feature: Multiple Wake Alarms Per Zone
**implementation_1.yaml lines 1923-1975**: Supports alarm1_time through alarm5_time
**Current Integration**: Only single wake_alarm_time per zone

### Feature: Midnight OFF Lights Pattern
**implementation_1.yaml lines 1687-1701**: Complex midnight light management
**Current Integration**: No scheduled light control

### Feature: Good Morning TTS via Sonos
**implementation_1.yaml lines 3142-3201**: Alexa announces weather, calendar
**Current Integration**: Sonos only plays music, no TTS

### Feature: Zone Snapshot/Restore
**implementation_1.yaml lines 891-921**: Store/restore zone state
**Current Integration**: No snapshot capability

---

## 🏗️ ARCHITECTURAL VIOLATIONS

### Violation: Direct Coordinator Data Access
**Found In**: Multiple test files and some platforms
**Pattern**: `coordinator.data["zones"][zone_id]["lights"]`
**Should Be**: `coordinator.get_zone_lights(zone_id)`

Run this check:
```bash
grep -r "coordinator\.data\[" custom_components/adaptive_lighting_pro/platforms/
grep -r "coordinator\._" custom_components/adaptive_lighting_pro/platforms/
```

Any matches indicate architectural violations that create coupling.

---

## 📋 FIX PRIORITY ORDER

### Before Deployment (MUST FIX):
1. **Issue #7**: Remove hardcoded entities from const.py
2. **Issue #1**: Wake sequence override manual control
3. **Issue #2**: Buttons set manual control on AL
4. **Issue #4**: Sunset boost with warmth component (+ 21 test updates)

### Week 1 (SHOULD FIX):
5. **Issue #3**: Environmental time multiplier use sun only
6. **Issue #5**: Services temporary parameter
7. **Issue #6**: Define scene timer behavior
8. **Issue #8**: Human-readable sensor displays

### Nice to Have:
9. **Issue #9**: Smart timeout scaling
10. **Issue #10**: Wake sequence notifications
11. Missing features from implementation_1.yaml

---

## 🧪 TEST IMPACTS

When fixing Issue #4 (sunset boost tuple), update these test files:
- test_sunset_boost.py - Mock returns BoostResult(brightness, warmth)
- test_coordinator_integration.py - Handle tuple in boost assertions
- test_environmental.py - Update boost combination logic
- test_combined_boosts.py - Verify warmth + brightness handling
- test_sensor_platform.py - Sensor shows both values
- test_services.py - Service tests with warmth
- All 21 files using sunset boost mocks

Example test update:
```python
# Before:
mock_sunset_boost.calculate_boost.return_value = 20

# After:
from custom_components.adaptive_lighting_pro.features.sunset_boost import BoostResult
mock_sunset_boost.calculate_boost.return_value = BoostResult(20, -300)
```

---

## 📝 DEPLOYMENT CHECKLIST

Before deploying to production Home Assistant:

□ Remove ALL hardcoded entity IDs from const.py
□ Fix wake sequence manual control override
□ Add manual control calls to all buttons/selects
□ Update sunset boost to return tuple
□ Update all 21 test mocks for tuple return
□ Run full test suite: `pytest tests/unit/ -v`
□ Verify 210+ tests pass
□ Update implementation_2.yaml with scene choreography
□ Test on development HA instance first
□ Document timer behavior for users

---

**End of Critical Issues Document**