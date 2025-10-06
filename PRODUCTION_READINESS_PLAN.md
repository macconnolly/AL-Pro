# ADAPTIVE LIGHTING PRO - PRODUCTION READINESS PLAN
**Version**: 1.0
**Created**: 2025-10-06
**Status**: Ready for Implementation
**Quality Bar**: @claude.md - "Would I want to live with this every day?"

---

## EXECUTIVE SUMMARY

**Current Status**: 207/211 tests passing (98.1% pass rate)

**Critical Fixes Completed**: All blocking issues resolved
- ✅ Wake sequence manual_control lifecycle (sets True to lock lights)
- ✅ Environmental boost disabled during wake
- ✅ Scene per-zone tracking + manual_control
- ✅ All blocking=False race conditions eliminated
- ✅ Architectural violations fixed (switch.py)

**Remaining Work**: Enhancements + polish for "lives here" quality standard

**User Requirements**:
- Personal deployment (not HACS sharing)
- Scenes persistent (until cleared)
- Need quick "return to auto" mechanism
- Dashboard control matching implementation_1.yaml functionality

---

## DOCUMENT REVIEW & VALIDATION

### Analysis of Existing Tactical Plans

I reviewed all 5 tactical planning documents to identify what's valid vs. what's been misdiagnosed:

#### TACTICAL_FIX_PLAN.md

**Issue #1: Wake Sequence vs Manual Control**
- ❌ **DOCUMENT IS WRONG** - Claims wake should CLEAR manual_control (set to False)
- ✅ **USER CONFIRMED OPPOSITE** - "Set manual_control=True when wake starts"
- ✅ **CORRECTLY IMPLEMENTED** - Commit 4294b6fe sets manual_control=True to LOCK lights during wake
- **VERDICT**: Document analysis was backwards

**Issue #2: Button Press Race Condition**
- ✅ **CORRECTLY IDENTIFIED** - blocking=False could cause race where boundaries update before manual_control sets
- ✅ **FIXED** - Removed all blocking=False parameters from critical service calls
- **VERDICT**: Valid issue, correctly fixed

**Issue #3: Environmental Time Multiplier**
- ❌ **FALSE POSITIVE** - Document wants sun-only logic, remove clock-based fallback
- ✅ **USER CONFIRMED CURRENT IS CORRECT** - "Suppress boost during dark periods is fine"
- ✅ **NO CHANGE NEEDED** - Current implementation matches user requirements
- **VERDICT**: Document misunderstood user requirements

**Issue #4: Scene Zone Targeting**
- ✅ **CORRECTLY IDENTIFIED** - Global scene offsets should be per-zone
- ✅ **FIXED** - Implemented `_scene_offsets_by_zone: dict[str, tuple[int, int]]`
- **VERDICT**: Valid issue, correctly fixed

#### TACTICAL_FIX_PLAN_V2.md

Same issues as above with same conclusions. This was the "complete rewrite with correct understanding" but still had wake sequence logic backwards.

#### TACTICAL_FIX_PLAN_FINAL.md

**Most Accurate Document** - Reflects actual user confirmations:
- ✅ Wake manual_control lifecycle - **FIXED**
- ✅ Wake disable environmental boost - **FIXED**
- ✅ Scene per-zone + manual_control - **FIXED**
- ✅ Remove blocking=False - **FIXED**

Enhancements listed (NOT CRITICAL):
- Quick Setup Config Flow
- Per-Zone Timeout Overrides
- Sonos features
- Notifications
- Diagnostic sensors

#### CRITICAL_ARCHITECTURE_ANALYSIS.md

**Architectural Philosophy**, not bugs:
- implementation_1.yaml = business logic in YAML (anti-pattern)
- implementation_2.yaml = user config only (correct pattern)
- ✅ **Current integration architecture is correct**

No action required - this is guidance, not issues.

#### CRITICAL_ISSUES.md - Detailed Validation

**Issue #1: "Wake Sequence Doesn't Override Manual Control"**
- ❌ **DOCUMENT IS WRONG** - Says to clear manual_control (set False)
- ✅ **USER CONFIRMED OPPOSITE** - Should set True to lock lights
- ✅ **CORRECTLY IMPLEMENTED** - Wake sets manual_control=True

**Issue #2: "Button Platform Doesn't Set Manual Control"**
- ❌ **MISDIAGNOSED** - Buttons DO call set_manual_control via coordinator chain:
  - button → coordinator.set_brightness_adjustment(start_timers=True)
  - → start_manual_timer → _mark_zone_lights_as_manual
  - → set_manual_control
- ✅ **REAL ISSUE WAS RACE CONDITION** - Fixed by removing blocking=False
- ✅ **FIXED**

**Issue #3: "Environmental Time Multiplier Uses Clock Instead of Sun"**
- ❌ **FALSE POSITIVE** - Current logic is correct per user
- ✅ **NO CHANGE NEEDED**

**Issue #4: "Sunset Boost Missing Warmth Component"**
- ✅ **VALID ISSUE** - Returns int, should return tuple(brightness, warmth)
- ❌ **NOT YET FIXED**
- ⚠️ **REQUIRES**: Return type change + 21 test updates
- **USER DECISION NEEDED**: Is golden hour warmth aesthetic critical?
- **FOR PERSONAL DEPLOYMENT**: Enhancement, not blocker

**Issue #5: "Services Missing Temporary Parameter"**
- ✅ **VALID ENHANCEMENT** - Not critical for personal deployment

**Issue #6: "Scene Timer Behavior Undefined"**
- ✅ **VALID UX ISSUE** - Needs design decision
- **USER CONFIRMED**: Scenes should be persistent
- **REQUIREMENT**: Need quick "return to auto" mechanism

**Issue #7: "SCENE_CONFIGS Contains Hardcoded Entities"**
- ✅ **VALID CRITICAL ISSUE** - IF sharing code
- **For personal deployment**: Not critical
- **For HACS release**: CRITICAL BLOCKER
- **USER CONFIRMED**: Personal deployment only
- **VERDICT**: Not a blocker for this deployment

**Issue #8-10**: Valid UX enhancements, not critical

---

## WHAT'S ALREADY DONE

### ✅ All Critical Fixes Implemented (Commit 4294b6fe)

**Wake Sequence Manual Control Lifecycle**
- **File**: `coordinator.py:208`
- **Added**: `self._wake_active_zones: set[str] = set()`
- **Location**: `coordinator.py:361-429`
- **Implementation**: Complete lifecycle
  - Sets manual_control=True when wake starts (locks lights)
  - Clears manual_control=False when wake ends (restores AL)
  - Tracks active zones to detect transitions

**Wake Sequence Disable Environmental Boost**
- **File**: `coordinator.py:507-510`
- **Implementation**: Environmental boost skips wake zones
- **Check**: `if zone_id not in self._wake_active_zones`

**Scene Manual Control & Per-Zone Offsets**
- **File**: `coordinator.py:212`
- **Added**: `_scene_offsets_by_zone: dict[str, tuple[int, int]]`
- **File**: `coordinator.py:1385-1424`
- **Added**: `_extract_lights_from_scene_actions()` helper method
- **File**: `coordinator.py:1537-1561`
- **Implementation**: Sets manual_control for scene lights
- **File**: `coordinator.py:1599-1608`
- **Implementation**: Per-zone offset application (not global)

**Remove All blocking=False**
- All `set_manual_control` calls - blocking removed
- All `change_switch_settings` calls - blocking removed
- Scene action execution - blocking removed
- **Result**: No race conditions

**Architectural Violations Fixed**
- **File**: `switch.py:249-262`
- **Added**: `coordinator.get_next_alarm_time()` getter method
- **Improved**: `coordinator.get_wake_start_time()` to use state dict
- **Result**: Switch platform uses coordinator API (no `_wake_sequence._next_alarm` access)
- **Verification**: ✅ 0 violations found

### ❌ What's NOT Implemented

**Missing Coordinator Method**:
- `_clear_zone_manual_control()` - Centralized method to restore AL control
- Currently: Wake end, timer expiry, scene clear all have duplicate logic
- **Required**: Phase 1, Task 1.1

**Missing Scene Functionality**:
- "Return to Auto" scene (Scene.AUTO)
- Quick mechanism to clear all scenes and restore automatic control
- **Required**: Phase 1, Task 1.2

**Missing Enhancements** (All 6):
1. Quick Setup Config Flow
2. Per-Zone Timeout Overrides
3. Sonos Wake Notifications
4. Smart Timeout Scaling
5. Wake Sequence Status Sensor
6. Additional Diagnostic Sensors

**Missing Dashboard**:
- implementation_2.yaml dashboard control scripts
- Lovelace card templates
- Overnight reset automation

---

## IMPLEMENTATION PLAN

### PHASE 1: COMPLETE CRITICAL FOUNDATION (2-3 hours)

**User Requirement**: Scenes persistent, need quick "return to auto"

#### Task 1.1: Add `_clear_zone_manual_control()` Method

**WHY**: Centralize manual_control clearing logic used by wake end, scene clear, timer expiry. Currently duplicated in 3 places.

**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Location**: After `_mark_zone_lights_as_manual()` (currently line 709)

**Action**: INSERT new method:

```python
async def _clear_zone_manual_control(self, zone_id: str) -> None:
    """Clear manual control for all lights in a zone (restore AL control).

    Used when:
    - Wake sequence completes
    - Scene is cleared (return to auto)
    - Manual timer expires

    Args:
        zone_id: Zone identifier
    """
    try:
        zone_config = self.zones.get(zone_id)
        if not zone_config:
            _LOGGER.warning("Cannot clear manual control for zone %s - config not found", zone_id)
            return

        al_switch = zone_config.get("adaptive_lighting_switch")
        if not al_switch:
            _LOGGER.debug("Zone %s has no AL switch - skipping manual control clear", zone_id)
            return

        lights = zone_config.get("lights", [])
        if not lights:
            _LOGGER.debug("Zone %s has no lights configured", zone_id)
            return

        # Clear manual control in AL integration
        await self.hass.services.async_call(
            ADAPTIVE_LIGHTING_DOMAIN,
            "set_manual_control",
            {
                "entity_id": al_switch,
                "lights": lights,
                "manual_control": False,  # Restore AL control
            },
        )

        _LOGGER.info(
            "Cleared manual control for %d lights in zone %s (restored AL control)",
            len(lights),
            zone_id,
        )

    except Exception as err:
        _LOGGER.error(
            "Failed to clear manual control for zone %s: %s",
            zone_id,
            err,
            exc_info=True,
        )
```

**Benefits**:
- Single source of truth for clearing manual_control
- Consistent error handling
- Comprehensive logging
- Easier to test and maintain

**Testing**: Mock coordinator, call method, verify service call with manual_control=False

---

#### Task 1.2: Implement "Return to Auto" Scene

**WHY**: User needs quick way to clear all scenes and return to automatic adaptive lighting. Currently only ALL_LIGHTS scene does this, but semantically unclear.

**Part A: Add Scene.AUTO to Enum**

**File**: `custom_components/adaptive_lighting_pro/const.py`
**Location**: Line 456 (Scene enum definition)

**Action**: ADD new enum value:

```python
class Scene(str, Enum):
    """Scene types for lighting control."""

    DEFAULT = "default"
    ALL_LIGHTS = "all_lights"
    NO_SPOTLIGHTS = "no_spotlights"
    EVENING_COMFORT = "evening_comfort"
    ULTRA_DIM = "ultra_dim"
    AUTO = "auto"  # NEW: Return to automatic control
```

**Part B: Add Scene Configuration**

**File**: `custom_components/adaptive_lighting_pro/const.py`
**Location**: Line 587 (SCENE_CONFIGS dictionary)

**Action**: ADD new scene config:

```python
Scene.AUTO: {
    "name": "Auto (Return to Adaptive)",
    "brightness_offset": 0,
    "warmth_offset": 0,
    "actions": []  # No light choreography, just restore AL control
},
```

**Part C: Update Scene Application Logic**

**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Location**: Line 1567 (apply_scene method, ALL_LIGHTS special case)

**Current Code** (line 1567-1593):
```python
if scene == Scene.ALL_LIGHTS:
    _LOGGER.info("ALL_LIGHTS scene - clearing all scene offsets and manual_control")

    # Clear per-zone offsets
    self._scene_offsets_by_zone = {}

    # DEPRECATED: Also clear global offsets for backward compatibility
    self._scene_brightness_offset = 0
    self._scene_warmth_offset = 0

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
                    "manual_control": False,  # Restore AL control
                },
            )
```

**Action**: REPLACE with more general logic:

```python
# Special case: AUTO and ALL_LIGHTS both clear scenes and restore control
if scene in [Scene.ALL_LIGHTS, Scene.AUTO]:
    _LOGGER.info("Clearing all scene offsets and restoring AL control (scene: %s)", scene.value)

    # Clear per-zone offsets
    self._scene_offsets_by_zone = {}

    # DEPRECATED: Also clear global offsets for backward compatibility with tests
    self._scene_brightness_offset = 0
    self._scene_warmth_offset = 0

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
                    "manual_control": False,  # Restore AL control
                },
            )
            _LOGGER.debug("Restored AL control for zone %s", zone_id)

    _LOGGER.info("Scene cleared, all zones restored to automatic adaptive lighting")
```

**Benefits**:
- Clear semantic meaning: Scene.AUTO = "return to automatic"
- ALL_LIGHTS maintains backward compatibility
- Single code path for both (DRY principle)
- Explicit logging for debugging

**Testing**:
- Apply Scene.AUTO → verify all zones have manual_control=False
- Apply Scene.EVENING_COMFORT then Scene.AUTO → verify offsets cleared

---

#### Task 1.3: Update Scene Persistence Documentation

**WHY**: Document intended behavior for future maintenance and user understanding.

**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Location**: Line 1497 (apply_scene method docstring)

**Current Docstring**:
```python
async def apply_scene(self, scene: Scene) -> bool:
    """Apply a scene to all zones.

    Args:
        scene: Scene type to apply

    Returns:
        True if scene applied successfully, False otherwise
    """
```

**Action**: REPLACE with comprehensive documentation:

```python
async def apply_scene(self, scene: Scene) -> bool:
    """Apply a scene to all zones.

    SCENE PERSISTENCE BEHAVIOR:
    Scenes are PERSISTENT - they remain active until:
    1. Another scene is applied (replaces current scene)
    2. Scene.AUTO or Scene.ALL_LIGHTS is selected (restores AL control)
    3. Manual timer expires (if user makes manual adjustment after scene)

    WHAT SCENES DO:
    1. Execute choreography actions (turn lights on/off at specific levels)
    2. Set manual_control=True for choreographed lights (locks at scene levels)
    3. Apply brightness/warmth offsets to affected zones only
    4. Offsets remain active until scene cleared

    SCENE TYPES:
    - Scene.AUTO: Clear all scenes, restore automatic adaptive lighting
    - Scene.ALL_LIGHTS: Turn on all lights, restore automatic control
    - Scene.EVENING_COMFORT: Dim warm lighting with choreography
    - Scene.ULTRA_DIM: Minimal lighting for movies/late night
    - Scene.NO_SPOTLIGHTS: Disable accent zones for reading/focus

    Args:
        scene: Scene type to apply

    Returns:
        True if scene applied successfully, False otherwise

    Example:
        # Apply evening comfort scene (persists until cleared)
        await coordinator.apply_scene(Scene.EVENING_COMFORT)

        # Later: return to automatic adaptive lighting
        await coordinator.apply_scene(Scene.AUTO)
    """
```

**Benefits**:
- Clear documentation of persistence model
- Examples for future developers
- Documents all scene types
- Explains interaction with manual_control

---

### PHASE 2: ENHANCEMENT #1 - QUICK SETUP CONFIG FLOW (2-3 hours)

**WHY**: Reduce setup time from 15 minutes to 2 minutes by auto-detecting existing Adaptive Lighting switches.

**USER VALUE**:
- Detects `switch.adaptive_lighting_bedroom`, `switch.adaptive_lighting_kitchen`, etc.
- Extracts zone names automatically
- Pre-fills configurations with sensible defaults
- User just confirms and tweaks

#### Task 2.1: Add AL Switch Detection Logic

**File**: `custom_components/adaptive_lighting_pro/config_flow.py`
**Location**: Before `async_step_user` method (line ~40)

**Action**: INSERT helper methods:

```python
def _detect_al_switches(self) -> list[str]:
    """Detect existing Adaptive Lighting switches in Home Assistant.

    Searches for switch entities with naming pattern:
    - switch.adaptive_lighting_<zone_name>

    Excludes AL control switches:
    - switch.adaptive_lighting_*_adapt_brightness
    - switch.adaptive_lighting_*_adapt_color

    Returns:
        List of AL switch entity_ids found, sorted alphabetically

    Example:
        ['switch.adaptive_lighting_bedroom',
         'switch.adaptive_lighting_kitchen',
         'switch.adaptive_lighting_living_room']
    """
    try:
        # Get all switch entities from Home Assistant
        all_switches = self.hass.states.async_entity_ids("switch")

        # Filter for AL switches (exclude control switches)
        al_switches = [
            entity_id for entity_id in all_switches
            if entity_id.startswith("switch.adaptive_lighting_")
            and not entity_id.endswith("_adapt_brightness")
            and not entity_id.endswith("_adapt_color")
        ]

        return sorted(al_switches)

    except Exception as err:
        _LOGGER.error("Error detecting AL switches: %s", err)
        return []

def _extract_zone_name(self, switch_entity_id: str) -> str:
    """Extract zone name from AL switch entity_id.

    Args:
        switch_entity_id: Entity ID like 'switch.adaptive_lighting_bedroom'

    Returns:
        Zone name like 'bedroom'

    Example:
        _extract_zone_name('switch.adaptive_lighting_main_living')
        # Returns: 'main_living'
    """
    # Remove prefix 'switch.adaptive_lighting_'
    prefix = "switch.adaptive_lighting_"
    if switch_entity_id.startswith(prefix):
        return switch_entity_id[len(prefix):]
    return switch_entity_id
```

**Benefits**:
- Robust entity filtering (excludes control switches)
- Error handling for HA state access
- Clear examples in docstrings
- Sorted output for consistent UX

---

#### Task 2.2: Modify User Step to Offer Quick Setup

**File**: `custom_components/adaptive_lighting_pro/config_flow.py`
**Location**: Line 47 (async_step_user method)

**Current Code**: Goes directly to manual configuration

**Action**: REPLACE entire `async_step_user` method:

```python
async def async_step_user(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Handle initial configuration step with Quick Setup option.

    Flow:
    1. Detect existing AL switches
    2. If found: Offer Quick Setup vs Manual Setup choice
    3. If not found: Go directly to Manual Setup
    """

    # Detect existing AL switches
    al_switches = self._detect_al_switches()

    # If AL switches found and no user input yet, offer choice
    if al_switches and user_input is None:
        return self.async_show_form(
            step_id="setup_choice",
            data_schema=vol.Schema({
                vol.Required("setup_type", default="quick"): vol.In({
                    "quick": f"✨ Quick Setup ({len(al_switches)} AL switches detected)",
                    "manual": "⚙️ Manual Setup (configure everything)",
                }),
            }),
            description_placeholders={
                "detected_switches": "\n".join(f"  • {sw}" for sw in al_switches[:5]),
                "total_count": str(len(al_switches)),
                "more_count": str(max(0, len(al_switches) - 5)),
            },
        )

    # No AL switches detected or manual setup chosen - go to manual flow
    return await self.async_step_manual_setup(user_input)
```

**UI Text** (shown to user):
```
Detected 3 Adaptive Lighting switches:
  • switch.adaptive_lighting_bedroom
  • switch.adaptive_lighting_kitchen
  • switch.adaptive_lighting_living_room

Choose setup method:
  ✨ Quick Setup (3 AL switches detected)
  ⚙️ Manual Setup (configure everything)
```

**Benefits**:
- Non-intrusive (only shows if AL switches found)
- Clear indication of what was detected
- User maintains full control (can choose manual)
- Emoji icons for visual clarity

---

#### Task 2.3: Add Setup Flow Handlers

**File**: `custom_components/adaptive_lighting_pro/config_flow.py`
**Location**: After `async_step_user`

**Action**: ADD three new step handlers:

**Part A: Setup Choice Handler**

```python
async def async_step_setup_choice(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Handle Quick vs Manual setup choice.

    Redirects to appropriate flow based on user selection.
    """
    if user_input is None:
        # Should not happen (no-input handled in async_step_user)
        return await self.async_step_user(None)

    if user_input["setup_type"] == "quick":
        return await self.async_step_quick_setup(None)
    else:
        return await self.async_step_manual_setup(None)
```

**Part B: Quick Setup Handler**

```python
async def async_step_quick_setup(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Handle Quick Setup with auto-detected AL switches.

    Flow:
    1. Show detected switches and global settings
    2. User confirms and sets global defaults
    3. Create config entry with auto-generated zone configs
    4. User can refine per-zone settings via Options Flow later
    """

    al_switches = self._detect_al_switches()

    if not al_switches:
        # AL switches disappeared (unlikely)
        _LOGGER.warning("AL switches not found during quick setup")
        return await self.async_step_manual_setup(None)

    if user_input is None:
        # Show confirmation form with global settings
        return self.async_show_form(
            step_id="quick_setup",
            data_schema=vol.Schema({
                vol.Required("confirm", default=True): bool,
                vol.Optional("brightness_increment", default=10): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=50)
                ),
                vol.Optional("color_temp_increment", default=500): vol.All(
                    vol.Coerce(int), vol.Range(min=100, max=2000)
                ),
                vol.Optional("manual_timeout", default=1800): vol.All(
                    vol.Coerce(int), vol.Range(min=300, max=14400)
                ),
            }),
            description_placeholders={
                "zones": "\n".join(
                    f"  • {self._extract_zone_name(sw)}"
                    for sw in al_switches
                ),
                "zone_count": str(len(al_switches)),
            },
        )

    # User confirmed - create zone configs from detected switches
    zones = {}
    for switch_id in al_switches:
        zone_name = self._extract_zone_name(switch_id)
        zones[zone_name] = {
            "adaptive_lighting_switch": switch_id,
            "lights": [],  # User will configure via Options Flow if needed
            "brightness_min": 1,
            "brightness_max": 100,
            "color_temp_min": 2000,
            "color_temp_max": 5500,
        }

    # Create config entry
    return self.async_create_entry(
        title="Adaptive Lighting Pro",
        data={
            "brightness_increment": user_input["brightness_increment"],
            "color_temp_increment": user_input["color_temp_increment"],
            "manual_control_timeout": user_input["manual_timeout"],
            "zones": zones,
        },
    )
```

**UI Text** (shown to user):
```
Quick Setup will create 3 zones:
  • bedroom
  • kitchen
  • living_room

You can customize individual zones later in Options.

Global Settings:
  ☑️ Confirm setup
  Brightness Increment: 10%
  Color Temp Increment: 500K
  Manual Timeout: 1800 seconds (30 minutes)
```

**Part C: Manual Setup Handler**

```python
async def async_step_manual_setup(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Handle Manual Setup (original flow).

    This is the existing async_step_user logic moved here.
    """
    if user_input is None:
        return self.async_show_form(
            step_id="manual_setup",
            data_schema=vol.Schema({
                vol.Required("brightness_increment", default=10): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=50)
                ),
                vol.Required("color_temp_increment", default=500): vol.All(
                    vol.Coerce(int), vol.Range(min=100, max=2000)
                ),
                vol.Required("manual_control_timeout", default=1800): vol.All(
                    vol.Coerce(int), vol.Range(min=300, max=14400)
                ),
            }),
        )

    # Store data and proceed to zones configuration
    self.config_data = user_input
    return await self.async_step_zones(None)
```

**Benefits**:
- Quick Setup: 3 clicks to complete configuration
- Manual Setup: Full control maintained
- Options Flow: User can refine later
- Clear user feedback at each step

**Testing**:
- Mock 3 AL switches → verify Quick Setup creates 3 zones
- Mock 0 AL switches → verify goes to Manual Setup
- Test both Quick and Manual paths create valid config entries

---

### PHASE 3: ENHANCEMENT #2 - PER-ZONE TIMEOUT OVERRIDES (2-3 hours)

**WHY**: Different zones have different usage patterns:
- Bedroom: 30 minutes (quick adjustments during sleep)
- Kitchen: 2 hours (cooking, cleaning)
- Living Room: 1 hour (reading, TV)

**USER VALUE**: Respect context-specific needs without global compromise.

#### Task 3.1: Add Zone Timeout to Config Schema

**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Location**: Line 154 (_validate_zone_config method)

**Current Validation**: Brightness min/max, color temp min/max

**Action**: ADD timeout validation:

```python
# Existing validation for color_temp_min/max...
if "color_temp_min" in zone_config:
    color_temp_min = zone_config["color_temp_min"]
    if not isinstance(color_temp_min, int) or color_temp_min < 1500 or color_temp_min > 6500:
        raise ValueError(
            f"Zone '{zone_id}' color_temp_min must be integer between 1500-6500, got {color_temp_min}"
        )

    color_temp_max = zone_config.get("color_temp_max")
    if color_temp_max is not None:
        if not isinstance(color_temp_max, int) or color_temp_max < 1500 or color_temp_max > 6500:
            raise ValueError(
                f"Zone '{zone_id}' color_temp_max must be integer between 1500-6500, got {color_temp_max}"
            )
        if color_temp_min >= color_temp_max:
            raise ValueError(
                f"Zone '{zone_id}' color_temp_min ({color_temp_min}) must be less than "
                f"color_temp_max ({color_temp_max})"
            )

# NEW: Validate manual_timeout if present
if "manual_timeout" in zone_config:
    timeout = zone_config["manual_timeout"]
    if not isinstance(timeout, int):
        raise ValueError(
            f"Zone '{zone_id}' manual_timeout must be integer, got {type(timeout).__name__}"
        )
    if timeout < 60 or timeout > 14400:
        raise ValueError(
            f"Zone '{zone_id}' manual_timeout must be between 60-14400 seconds (1min-4hr), got {timeout}"
        )
```

**Benefits**:
- Type safety (must be int)
- Range validation (1min - 4hr)
- Clear error messages for config debugging

---

#### Task 3.2: Add Get/Set Methods for Zone Timeout

**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Location**: After `get_manual_control_timeout()` method (line ~1250)

**Action**: INSERT two new methods:

**Part A: Getter Method**

```python
def get_zone_manual_timeout(self, zone_id: str) -> int:
    """Get manual control timeout for a specific zone.

    Falls back to global timeout if zone doesn't have override.

    This allows zones to have different timeout durations based on usage:
    - Bedroom: 30 minutes (quick sleep adjustments)
    - Kitchen: 2 hours (cooking takes time)
    - Office: 4 hours (focus sessions)

    Args:
        zone_id: Zone identifier

    Returns:
        Timeout duration in seconds (60-14400)

    Example:
        >>> coordinator.get_zone_manual_timeout("bedroom")
        1800  # 30 minutes (uses global default)

        >>> coordinator.get_zone_manual_timeout("kitchen")
        7200  # 2 hours (zone override)
    """
    zone_config = self.zones.get(zone_id, {})
    zone_timeout = zone_config.get("manual_timeout")

    if zone_timeout is not None:
        _LOGGER.debug(
            "Using zone-specific timeout for %s: %d seconds",
            zone_id,
            zone_timeout,
        )
        return zone_timeout

    # Fall back to global timeout
    global_timeout = self.get_manual_control_timeout()
    _LOGGER.debug(
        "Using global timeout for %s: %d seconds (no zone override)",
        zone_id,
        global_timeout,
    )
    return global_timeout
```

**Part B: Setter Method**

```python
async def set_zone_manual_timeout(self, zone_id: str, timeout: int) -> None:
    """Set manual control timeout for a specific zone.

    Persists to config entry so timeout survives HA restart.

    Args:
        zone_id: Zone identifier
        timeout: Timeout duration in seconds (60-14400)

    Raises:
        ValueError: If timeout out of range or zone not found

    Example:
        # Set kitchen to 2 hour timeout
        await coordinator.set_zone_manual_timeout("kitchen", 7200)

        # Set bedroom to 30 minute timeout
        await coordinator.set_zone_manual_timeout("bedroom", 1800)
    """
    # Validate zone exists
    if zone_id not in self.zones:
        available_zones = ", ".join(self.zones.keys())
        raise ValueError(
            f"Zone '{zone_id}' not found. Available zones: {available_zones}"
        )

    # Validate timeout range
    if timeout < 60 or timeout > 14400:
        raise ValueError(
            f"Timeout must be 60-14400 seconds (1min-4hr), got {timeout}"
        )

    # Update in-memory zone config
    self.zones[zone_id]["manual_timeout"] = timeout

    # Persist to config entry (survives HA restart)
    new_data = self.config_entry.data.copy()
    if "zones" not in new_data:
        new_data["zones"] = {}
    if zone_id not in new_data["zones"]:
        new_data["zones"][zone_id] = {}

    new_data["zones"][zone_id]["manual_timeout"] = timeout

    self.hass.config_entries.async_update_entry(
        self.config_entry,
        data=new_data,
    )

    # Fire event for sensor/UI updates
    self.async_update_listeners()

    _LOGGER.info(
        "Updated zone '%s' manual timeout: %d seconds (%.1f minutes)",
        zone_id,
        timeout,
        timeout / 60,
    )
```

**Benefits**:
- Getter: Graceful fallback to global (zones without override still work)
- Setter: Validates before setting (prevents invalid configs)
- Setter: Persists to config entry (survives restart)
- Both: Comprehensive logging for debugging
- Both: Examples in docstrings

**API Contract**:
- Following @claude.md: API layer provides public methods
- Number platform will call these (consumer layer)
- No direct zone config access from platforms

---

#### Task 3.3: Update Timer Start to Use Zone Timeout

**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Location**: Line 1354 (start_manual_timer method)

**Current Code** (line ~1362):
```python
if duration_seconds is None:
    duration_seconds = self.get_manual_control_timeout()
```

**Action**: REPLACE with zone-aware timeout:

```python
if duration_seconds is None:
    # Use zone-specific timeout if configured, otherwise global
    duration_seconds = self.get_zone_manual_timeout(zone_id)
    _LOGGER.debug(
        "Starting timer for %s with timeout: %d seconds (%.1f minutes)",
        zone_id,
        duration_seconds,
        duration_seconds / 60,
    )
```

**Impact**: All manual adjustments (buttons, sliders, services) automatically use zone-specific timeouts.

**Testing**:
- Set kitchen timeout to 2hr → press kitchen brighter button → timer should be 2hr
- Set bedroom timeout to 30min → press bedroom dimmer button → timer should be 30min
- Zone without override → should use global default

---

#### Task 3.4: Create Number Platform Entities

**File**: `custom_components/adaptive_lighting_pro/platforms/number.py`
**Location**: Line 36 (async_setup_entry function)

**Current Code**: Creates 3 global entities (brightness increment, color temp increment, manual timeout)

**Action A**: ADD per-zone timeout entities:

```python
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up ALP number entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[ALPNumberBase] = []

    # Global configuration entities
    entities.extend([
        ALPBrightnessIncrementNumber(coordinator),
        ALPColorTempIncrementNumber(coordinator),
        ALPManualTimeoutNumber(coordinator),
    ])

    # NEW: Per-zone timeout override entities
    for zone_id in coordinator.zones:
        entities.append(ALPZoneTimeoutNumber(coordinator, zone_id))

    async_add_entities(entities)
    return True
```

**Action B**: ADD new entity class at end of file:

```python
class ALPZoneTimeoutNumber(ALPNumberBase):
    """Number entity for per-zone manual control timeout override.

    Allows setting different timeout durations per zone:
    - Kitchen: 2 hours (cooking takes time)
    - Bedroom: 30 minutes (quick sleep adjustments)
    - Office: 4 hours (focus work sessions)

    Falls back to global timeout if not set.
    """

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        zone_id: str
    ) -> None:
        """Initialize zone timeout number.

        Args:
            coordinator: ALP coordinator instance
            zone_id: Zone identifier (e.g., "bedroom", "kitchen")
        """
        super().__init__(coordinator)
        self._zone_id = zone_id

        # Entity configuration
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{zone_id}_timeout"
        self._attr_name = f"ALP {zone_id.replace('_', ' ').title()} Timeout"
        self._attr_icon = "mdi:timer-outline"

        # Number constraints (1 minute to 4 hours)
        self._attr_native_min_value = 60  # 1 minute
        self._attr_native_max_value = 14400  # 4 hours
        self._attr_native_step = 60  # 1 minute increments

        # Unit configuration
        self._attr_native_unit_of_measurement = "seconds"
        self._attr_device_class = NumberDeviceClass.DURATION

        # Entity category (shows in Configuration section)
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> float:
        """Return current zone timeout (or global if no override).

        Returns:
            Current timeout in seconds
        """
        return float(self.coordinator.get_zone_manual_timeout(self._zone_id))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes.

        Shows whether using zone override or global default.
        """
        zone_config = self.coordinator.zones.get(self._zone_id, {})
        has_override = "manual_timeout" in zone_config

        attrs = {
            "zone_id": self._zone_id,
            "has_override": has_override,
            "using_global_default": not has_override,
        }

        if not has_override:
            attrs["global_default"] = self.coordinator.get_manual_control_timeout()

        return attrs

    async def async_set_native_value(self, value: float) -> None:
        """Set zone timeout override.

        Args:
            value: Timeout duration in seconds (60-14400)
        """
        try:
            await self.coordinator.set_zone_manual_timeout(
                self._zone_id,
                int(value)
            )
            _LOGGER.info(
                "User set %s timeout to %d seconds (%.1f minutes)",
                self._zone_id,
                int(value),
                value / 60,
            )
        except ValueError as err:
            _LOGGER.error(
                "Failed to set timeout for %s: %s",
                self._zone_id,
                err,
            )
            # Re-raise to show error in UI
            raise
```

**UI Appearance**:
```
Configuration Entities:
  number.alp_bedroom_timeout
    Current: 1800 seconds (30.0 minutes)
    Min: 60 | Max: 14400 | Step: 60
    Using: Global Default ✓

  number.alp_kitchen_timeout
    Current: 7200 seconds (120.0 minutes)
    Min: 60 | Max: 14400 | Step: 60
    Using: Zone Override ✓
```

**Benefits**:
- One entity per zone (clear which zone you're configuring)
- Shows override status in attributes
- Slider UI with 1-minute increments
- Validates on set (shows error if out of range)
- Duration device class (HA formats nicely)

**Testing**:
- Set kitchen timeout via UI → verify persists after HA restart
- Set invalid value (30 seconds) → should show error
- Delete override → should fall back to global default

---

### PHASE 4: ENHANCEMENT #3 - SONOS WAKE NOTIFICATIONS (1 hour)

**WHY**: User wants confirmation that wake sequence activated. Passive notification prevents "did it work?" anxiety.

**USER VALUE**:
- Gentle chime when wake starts
- Optional TTS announcement
- Confirmation when complete

#### Task 4.1: Add Wake Start Event Trigger

**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Location**: Line 370 (inside wake_in_progress block, after manual_control set)

**Current Code** (line ~390):
```python
        # Mark zone as having active wake
        self._wake_active_zones.add(zone_id)

    # Apply wake adjustments (boundaries will change gradually)
    await self._apply_adjustments_to_zone(zone_id, zone_config)
```

**Action**: INSERT event firing between add and apply:

```python
        # Mark zone as having active wake
        self._wake_active_zones.add(zone_id)

        # NEW: Fire event for wake sequence start (triggers notifications)
        wake_state = self.get_wake_sequence_state()
        self.hass.bus.async_fire(
            "adaptive_lighting_pro_wake_started",
            {
                "zone_id": zone_id,
                "wake_alarm": self.get_next_alarm_time().isoformat() if self.get_next_alarm_time() else None,
                "wake_start_time": self.get_wake_start_time().isoformat() if self.get_wake_start_time() else None,
                "duration_minutes": wake_state.get("duration_seconds", 900) / 60,
                "boost_percent": self._wake_sequence.calculate_boost(zone_id),
                "timestamp": dt_util.now().isoformat(),
            },
        )
        _LOGGER.info(
            "Wake sequence STARTED for zone %s - notification event fired (alarm: %s, duration: %.1f min)",
            zone_id,
            wake_state.get("alarm_time", "unknown"),
            wake_state.get("duration_seconds", 900) / 60,
        )

    # Apply wake adjustments (boundaries will change gradually)
    await self._apply_adjustments_to_zone(zone_id, zone_config)
```

**Event Data**:
```python
{
    "zone_id": "bedroom",
    "wake_alarm": "2025-10-06T06:30:00+00:00",
    "wake_start_time": "2025-10-06T06:15:00+00:00",
    "duration_minutes": 15.0,
    "boost_percent": 5,  # Current boost at start (increases over time)
    "timestamp": "2025-10-06T06:15:00+00:00"
}
```

**Benefits**:
- Automation can trigger on this event
- Rich data (alarm time, duration, boost)
- Timestamp for logging/debugging

---

#### Task 4.2: Add Wake Complete Event Trigger

**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Location**: Line 418 (inside wake complete block, after clearing manual_control)

**Current Code** (line ~421):
```python
        _LOGGER.info(
            "Wake sequence COMPLETED for zone %s - cleared manual_control to restore AL",
            zone_id,
        )

    # Remove from active wake zones
    self._wake_active_zones.discard(zone_id)
```

**Action**: INSERT event firing before discard:

```python
        _LOGGER.info(
            "Wake sequence COMPLETED for zone %s - cleared manual_control to restore AL",
            zone_id,
        )

    # NEW: Fire event for wake sequence complete (triggers completion notifications)
    wake_state = self.get_wake_sequence_state()
    self.hass.bus.async_fire(
        "adaptive_lighting_pro_wake_completed",
        {
            "zone_id": zone_id,
            "duration_minutes": wake_state.get("duration_seconds", 900) / 60,
            "final_boost": wake_state.get("max_boost_pct", 20),
            "timestamp": dt_util.now().isoformat(),
        },
    )

    # Remove from active wake zones
    self._wake_active_zones.discard(zone_id)
```

**Event Data**:
```python
{
    "zone_id": "bedroom",
    "duration_minutes": 15.0,
    "final_boost": 20,
    "timestamp": "2025-10-06T06:30:00+00:00"
}
```

---

#### Task 4.3: Create Sonos Notification Automation Template

**File**: `implementation_2.yaml`
**Location**: Line 742 (Tier 2 - Commented Automations section)

**Action**: ADD comprehensive automation template:

```yaml
# ============================================================================
# TIER 2: SONOS WAKE SEQUENCE NOTIFICATIONS (OPTIONAL - COMMENTED BY DEFAULT)
# ============================================================================
# Uncomment and customize these automations for your Sonos setup

# WAKE SEQUENCE START - Gentle chime + optional TTS
# - id: alp_wake_sequence_start_notification
#   alias: "ALP: Wake Sequence Started - Sonos Notification"
#   description: "Play gentle chime and TTS when wake sequence starts"
#   mode: single  # Prevent multiple simultaneous wake notifications
#
#   trigger:
#     - platform: event
#       event_type: adaptive_lighting_pro_wake_started
#       event_data:
#         zone_id: bedroom  # ⚠️ CUSTOMIZE: Your wake zone
#
#   action:
#     # Step 1: Save current Sonos state (volume, playing state)
#     - service: sonos.snapshot
#       target:
#         entity_id: media_player.bedroom_sonos  # ⚠️ CUSTOMIZE: Your Sonos speaker
#
#     # Step 2: Set gentle volume for wake
#     - service: media_player.volume_set
#       target:
#         entity_id: media_player.bedroom_sonos
#       data:
#         volume_level: 0.15  # 15% volume (gentle wake)
#
#     # Step 3: Play gentle wake chime (soothing sound)
#     # NOTE: Place wake_chime.mp3 in /config/www/sounds/
#     - service: media_player.play_media
#       target:
#         entity_id: media_player.bedroom_sonos
#       data:
#         media_content_id: "http://YOUR_HA_URL/local/sounds/wake_chime.mp3"
#         media_content_type: music
#
#     # Step 4: Wait for chime to finish
#     - delay:
#         seconds: 3
#
#     # Step 5: Optional TTS announcement (comment out if you prefer silence)
#     # - service: tts.cloud_say  # Or tts.google_say, tts.amazon_polly_say, etc.
#     #   target:
#     #     entity_id: media_player.bedroom_sonos
#     #   data:
#     #     message: >
#     #       Good morning. Wake sequence started.
#     #       Lights will gradually brighten over the next
#     #       {{ trigger.event.data.duration_minutes | int }} minutes.
#     #       Your alarm is set for
#     #       {{ (trigger.event.data.wake_alarm | as_datetime).strftime('%I:%M %p') }}.
#
#     # Step 6: Wait for TTS to finish
#     # - delay:
#     #     seconds: 8
#
#     # Step 7: Restore Sonos to previous state
#     - service: sonos.restore
#       target:
#         entity_id: media_player.bedroom_sonos

# WAKE SEQUENCE COMPLETE - Optional completion notification
# - id: alp_wake_sequence_complete_notification
#   alias: "ALP: Wake Sequence Completed"
#   description: "Optional mobile notification when wake completes"
#   mode: single
#
#   trigger:
#     - platform: event
#       event_type: adaptive_lighting_pro_wake_completed
#       event_data:
#         zone_id: bedroom  # ⚠️ CUSTOMIZE: Your wake zone
#
#   action:
#     # Mobile notification (requires Home Assistant Companion App)
#     - service: notify.mobile_app_YOUR_PHONE  # ⚠️ CUSTOMIZE: Your device
#       data:
#         title: "Good Morning! ☀️"
#         message: "Wake sequence completed - lights at full morning brightness"
#         data:
#           notification_icon: "mdi:weather-sunset-up"
#           tag: "alp_wake_complete"
#           timeout: 60  # Auto-dismiss after 60 seconds

# ALTERNATIVE: Simple persistent notification (no Sonos required)
# - id: alp_wake_start_persistent_notification
#   alias: "ALP: Wake Started - Persistent Notification"
#   description: "Show in-HA notification when wake starts"
#
#   trigger:
#     - platform: event
#       event_type: adaptive_lighting_pro_wake_started
#       event_data:
#         zone_id: bedroom
#
#   action:
#     - service: notify.persistent_notification
#       data:
#         title: "Wake Sequence Started ☀️"
#         message: |
#           Wake sequence active in {{ trigger.event.data.zone_id }}
#           Duration: {{ trigger.event.data.duration_minutes | int }} minutes
#           Alarm: {{ (trigger.event.data.wake_alarm | as_datetime).strftime('%I:%M %p') }}
#           Current boost: {{ trigger.event.data.boost_percent }}%
#         notification_id: "alp_wake_active"
```

**Customization Instructions** (add to top of file):

```yaml
# ============================================================================
# CUSTOMIZATION GUIDE FOR SONOS WAKE NOTIFICATIONS
# ============================================================================
#
# STEP 1: Place wake_chime.mp3 in /config/www/sounds/
#   - Recommended: Gentle chime, bell, or nature sound (2-3 seconds)
#   - Free sources: freesound.org, zapsplat.com
#   - Volume should be normalized (not too loud)
#
# STEP 2: Update entity IDs
#   - media_player.bedroom_sonos → your Sonos speaker entity
#   - notify.mobile_app_YOUR_PHONE → your mobile app notify service
#
# STEP 3: Customize messages
#   - Change TTS message to your preference
#   - Adjust volume_level (0.15 = 15%)
#   - Modify delay timings if needed
#
# STEP 4: Uncomment automation
#   - Remove leading '#' from lines you want to enable
#   - Test with Developer Tools → Events → Listen to events
#
# STEP 5: Optional enhancements
#   - Add weather in TTS: "{{ states('weather.home') }}"
#   - Add calendar events: Check next 2 hours of calendar
#   - Play music instead of chime: Spotify playlist, local media, etc.
```

**Benefits**:
- Fully commented (safe to include)
- Comprehensive instructions
- Multiple options (Sonos TTS, mobile notification, persistent notification)
- Preserves Sonos state (snapshot/restore)
- User customization clear and guided

**Testing**:
- Set wake alarm for 2 minutes from now
- Watch for event firing in Developer Tools → Events
- Verify chime plays at gentle volume
- Check snapshot/restore works (doesn't interrupt music)

---

### PHASE 5: ENHANCEMENT #4 - SMART TIMEOUT SCALING (1-2 hours)

**WHY**: Context-aware timeouts improve UX:
- Late night (22:00-05:00): 2x timeout (respect sleep, preserve ambiance longer)
- Dark day (env boost > 15%): 1.2x timeout (user needs boost longer)
- Dim scenes (brightness < -20%): 1.3x timeout (preserve mood)

**USER VALUE**: System intuitively extends timeouts when appropriate without manual adjustment.

#### Task 5.1: Enhance Smart Timeout Calculation

**File**: `custom_components/adaptive_lighting_pro/features/zone_manager.py`
**Location**: Line 89 (_calculate_smart_timeout method)

**Current Implementation**: Basic calculation (exists but minimal)

**Action**: REPLACE with comprehensive scaling logic:

```python
def _calculate_smart_timeout(
    self,
    zone_id: str,
    base_duration: int,
    context: dict[str, Any] | None = None,
) -> int:
    """Calculate intelligent timeout based on time, adjustment type, and environment.

    SCALING FACTORS:

    Time-Based:
    - Late night (22:00-05:00): 2.0x - Respect sleep patterns, preserve ambiance
    - Early morning (05:00-08:00): 1.5x - Morning routines take longer
    - Normal hours (08:00-22:00): 1.0x - Standard timeout

    Adjustment-Based:
    - Dim adjustments (< -20%): 1.3x - Preserve cozy ambiance longer
    - Bright adjustments (> +20%): 1.0x - Normal timeout (likely temporary)

    Environment-Based:
    - Dark day (env boost > 15%): 1.2x - User needs boost longer on cloudy days
    - Normal day: 1.0x - Standard timeout

    Scene-Based:
    - Active scene (not default): 1.5x - Scenes are intentional, extend timeout
    - No scene: 1.0x - Normal timeout

    Args:
        zone_id: Zone identifier
        base_duration: Base timeout from config (zone or global)
        context: Optional context with current state:
            - brightness_adjustment: int (percentage)
            - warmth_adjustment: int (Kelvin)
            - environmental_boost: int (percentage)
            - scene: str | None (scene name)

    Returns:
        Calculated timeout in seconds (clamped to 300-7200)

    Example:
        Late night + dim scene = 1800s * 2.0 * 1.3 * 1.5 = 7020s (1.95hr)
        Daytime + bright = 1800s * 1.0 = 1800s (30min)
    """
    from datetime import datetime

    multiplier = 1.0
    reasons = []

    # ========== TIME-BASED SCALING ==========
    hour = datetime.now().hour

    if 22 <= hour or hour < 5:
        # Late night (10 PM - 5 AM) - respect sleep patterns
        multiplier *= 2.0
        reasons.append("late night (2.0x)")
    elif 5 <= hour < 8:
        # Early morning (5 AM - 8 AM) - morning routine
        multiplier *= 1.5
        reasons.append("early morning (1.5x)")
    else:
        # Normal daytime hours
        reasons.append("normal hours (1.0x)")

    # ========== CONTEXT-BASED SCALING ==========
    if context:
        brightness_adj = context.get("brightness_adjustment", 0)
        warmth_adj = context.get("warmth_adjustment", 0)
        env_boost = context.get("environmental_boost", 0)
        scene = context.get("scene")

        # Dim adjustments get longer timeout (preserve ambiance)
        if brightness_adj < -20:
            multiplier *= 1.3
            reasons.append(f"dim adjustment ({brightness_adj}%, 1.3x)")

        # Warm adjustments in evening (cozy mood)
        if warmth_adj < -300 and 18 <= hour < 23:
            multiplier *= 1.2
            reasons.append(f"warm evening ({warmth_adj}K, 1.2x)")

        # Dark day gets longer timeout (user needs environmental boost)
        if env_boost > 15:
            multiplier *= 1.2
            reasons.append(f"dark day ({env_boost}% boost, 1.2x)")

        # Active scene gets extended timeout (intentional state)
        if scene and scene not in ["default", "none"]:
            multiplier *= 1.5
            reasons.append(f"scene active ({scene}, 1.5x)")

    # ========== CALCULATE & CLAMP ==========
    calculated = int(base_duration * multiplier)
    clamped = max(300, min(calculated, 7200))  # 5min - 2hr hard limits

    # If we hit the ceiling, note it
    if calculated > 7200:
        reasons.append(f"capped at max (calculated {calculated}s)")

    reason_str = ", ".join(reasons)
    _LOGGER.debug(
        "Smart timeout for %s: base=%ds, multiplier=%.2fx (%s), final=%ds (%.1fmin)",
        zone_id,
        base_duration,
        multiplier,
        reason_str,
        clamped,
        clamped / 60,
    )

    return clamped
```

**Example Scenarios**:

```python
# Scenario 1: Late night movie scene
# Time: 11 PM (late night = 2.0x)
# Scene: Ultra Dim (scene = 1.5x)
# Base: 1800s (30min)
# Result: 1800 * 2.0 * 1.5 = 5400s (90min)

# Scenario 2: Dark cloudy morning
# Time: 7 AM (early morning = 1.5x)
# Env: 18% boost (dark day = 1.2x)
# Base: 1800s (30min)
# Result: 1800 * 1.5 * 1.2 = 3240s (54min)

# Scenario 3: Daytime bright boost
# Time: 2 PM (normal = 1.0x)
# Adjustment: +30% brightness
# Base: 1800s (30min)
# Result: 1800 * 1.0 = 1800s (30min) - no scaling needed
```

**Benefits**:
- Intuitive behavior (extends when it makes sense)
- Comprehensive logging (debugging why timeout is X minutes)
- Hard limits prevent excessive timeouts (max 2hr)
- Composable factors (multiple can apply)

---

#### Task 5.2: Update Timer Start to Pass Context

**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Location**: Line 1354 (start_manual_timer method)

**Current Code**:
```python
async def start_manual_timer(
    self, zone_id: str, duration_seconds: int | None = None, skip_refresh: bool = False
) -> bool:
    """Start manual control timer for a zone."""

    if zone_id not in self.zones:
        _LOGGER.warning("Cannot start timer for unknown zone: %s", zone_id)
        return False

    # Get base timeout
    if duration_seconds is None:
        duration_seconds = self.get_zone_manual_timeout(zone_id)

    # ... rest of method ...
```

**Action**: UPDATE to build context and apply smart scaling:

```python
async def start_manual_timer(
    self, zone_id: str, duration_seconds: int | None = None, skip_refresh: bool = False
) -> bool:
    """Start manual control timer for a zone with smart timeout calculation.

    Smart timeout considers:
    - Time of day (late night = longer timeout)
    - Current adjustments (dim scenes = longer timeout)
    - Environmental conditions (dark day = longer timeout)
    - Active scene (scenes get extended timeout)

    Args:
        zone_id: Zone identifier
        duration_seconds: Optional timeout override (bypasses smart calculation)
        skip_refresh: Skip coordinator refresh if True

    Returns:
        True if timer started successfully
    """
    if zone_id not in self.zones:
        _LOGGER.warning("Cannot start timer for unknown zone: %s", zone_id)
        return False

    # Get base timeout (zone-specific or global)
    if duration_seconds is None:
        base_duration = self.get_zone_manual_timeout(zone_id)
    else:
        # User provided explicit duration - use as base
        base_duration = duration_seconds

    # Build context for smart timeout calculation
    context = {
        "brightness_adjustment": self._brightness_adjustment,
        "warmth_adjustment": self._warmth_adjustment,
        "environmental_boost": self._env_adapter.calculate_boost() if hasattr(self, "_env_adapter") else 0,
        "scene": self._current_scene.value if self._current_scene else None,
    }

    # Apply smart scaling (unless user provided explicit duration)
    if duration_seconds is None:
        # Let zone manager calculate smart timeout
        smart_duration = self.zone_manager._calculate_smart_timeout(
            zone_id,
            base_duration,
            context,
        )
        _LOGGER.info(
            "Starting smart timer for %s: base=%ds, smart=%ds (%.1fmin)",
            zone_id,
            base_duration,
            smart_duration,
            smart_duration / 60,
        )
    else:
        # User provided explicit duration - respect it
        smart_duration = duration_seconds
        _LOGGER.info(
            "Starting manual timer for %s: explicit duration=%ds (%.1fmin)",
            zone_id,
            smart_duration,
            smart_duration / 60,
        )

    # Mark zone lights as manual
    await self._mark_zone_lights_as_manual(zone_id)

    # Start the actual timer with smart duration
    success = await self.zone_manager.async_start_manual_timer(
        zone_id,
        smart_duration,
    )

    if not success:
        _LOGGER.error("Failed to start timer for zone %s", zone_id)
        return False

    # Refresh coordinator state (unless caller will refresh)
    if not skip_refresh:
        await self.async_request_refresh()

    return True
```

**Benefits**:
- Smart timeouts applied automatically
- Explicit duration still supported (service calls can override)
- Rich logging shows base vs smart duration
- Context built from current coordinator state

**Testing**:
- Late night + dim scene → should see 2.0x * 1.5x scaling in logs
- Daytime bright → should see 1.0x (no scaling)
- Explicit duration → should use exact duration (no scaling)

---

### PHASE 6: ENHANCEMENT #5 - WAKE SEQUENCE STATUS SENSOR (1 hour)

**WHY**: Dashboard visibility into wake sequence state. User can see:
- Is wake scheduled?
- When is next alarm?
- Is wake currently active?
- Progress percentage

**USER VALUE**: Glanceable status without checking AL switch attributes.

#### Task 6.1: Add Wake Sequence Status Sensor

**File**: `custom_components/adaptive_lighting_pro/platforms/sensor.py`
**Location**: Line 85 (async_setup_entry function)

**Current Code**:
```python
sensors.extend([
    ALPHealthScoreSensor(coordinator),
    ALPCurrentSceneSensor(coordinator),
    ALPBrightnessAdjustmentSensor(coordinator),
    # ... other sensors ...
])
```

**Action A**: ADD wake sequence sensor to setup:

```python
sensors.extend([
    ALPHealthScoreSensor(coordinator),
    ALPCurrentSceneSensor(coordinator),
    ALPBrightnessAdjustmentSensor(coordinator),
    # ... other sensors ...
    ALPWakeSequenceStatusSensor(coordinator),  # NEW
])
```

**Action B**: ADD sensor class at end of file:

```python
class ALPWakeSequenceStatusSensor(ALPSensorBase):
    """Sensor showing wake sequence status and progress.

    States:
    - "Not Scheduled" - No alarm set
    - "Scheduled for HH:MM" - Alarm set but not yet active
    - "Active (X% complete, Y% boost)" - Wake sequence in progress

    Attributes:
    - active: bool - Is wake currently running?
    - next_alarm: datetime - When is alarm?
    - wake_start_time: datetime - When does wake begin?
    - duration_minutes: float - How long is wake ramp?
    - progress_percent: float - How far through wake? (0-100)
    - current_boost: int - Current boost percentage
    - max_boost: int - Maximum boost percentage
    - target_zone: str - Which zone (usually "bedroom")
    - active_zones: list - Which zones currently have active wake
    """

    def __init__(self, coordinator: ALPDataUpdateCoordinator) -> None:
        """Initialize wake sequence status sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_wake_status"
        self._attr_name = "ALP Wake Sequence Status"
        self._attr_icon = "mdi:weather-sunset-up"
        self._attr_entity_category = None  # Show in main entities, not diagnostic

    @property
    def native_value(self) -> str:
        """Return wake sequence status as human-readable string.

        Returns:
            Status string like:
            - "Not Scheduled"
            - "Scheduled for 6:30 AM"
            - "Active (45% complete, 12% boost)"
        """
        wake_state = self.coordinator.get_wake_sequence_state()

        # Check if wake is currently active
        if wake_state.get("active", False):
            progress = wake_state.get("progress_pct", 0)
            boost = wake_state.get("current_boost_pct", 0)
            return f"Active ({progress:.0f}% complete, {boost}% boost)"

        # Not active - check if scheduled
        alarm_time = wake_state.get("alarm_time")
        if alarm_time:
            # Parse and format alarm time
            try:
                from datetime import datetime
                alarm_dt = datetime.fromisoformat(alarm_time)
                formatted = alarm_dt.strftime("%I:%M %p").lstrip("0")
                return f"Scheduled for {formatted}"
            except Exception:
                return f"Scheduled for {alarm_time}"

        # No alarm set
        return "Not Scheduled"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed wake sequence attributes.

        Returns comprehensive state for dashboard cards and automations.
        """
        wake_state = self.coordinator.get_wake_sequence_state()

        attrs = {
            "active": wake_state.get("active", False),
            "next_alarm": wake_state.get("alarm_time"),
            "wake_start_time": wake_state.get("wake_start_time"),
            "duration_minutes": wake_state.get("duration_seconds", 0) / 60,
            "progress_percent": wake_state.get("progress_pct", 0),
            "current_boost": wake_state.get("current_boost_pct", 0),
            "max_boost": wake_state.get("max_boost_pct", 20),
            "target_zone": wake_state.get("target_zone"),
        }

        # Add list of zones with active wake
        if hasattr(self.coordinator, "_wake_active_zones"):
            attrs["active_zones"] = list(self.coordinator._wake_active_zones)
        else:
            attrs["active_zones"] = []

        # Add time until alarm (if scheduled)
        if wake_state.get("alarm_time") and not wake_state.get("active"):
            try:
                from datetime import datetime
                import homeassistant.util.dt as dt_util
                alarm_dt = datetime.fromisoformat(wake_state["alarm_time"])
                now = dt_util.now()
                delta = alarm_dt - now

                if delta.total_seconds() > 0:
                    attrs["time_until_alarm_seconds"] = int(delta.total_seconds())
                    attrs["time_until_alarm_minutes"] = delta.total_seconds() / 60
                    attrs["time_until_alarm_hours"] = delta.total_seconds() / 3600
            except Exception as err:
                _LOGGER.debug("Error calculating time until alarm: %s", err)

        return attrs

    @property
    def icon(self) -> str:
        """Return dynamic icon based on wake state.

        Returns:
            Icon that reflects current state
        """
        wake_state = self.coordinator.get_wake_sequence_state()

        if wake_state.get("active", False):
            # Active wake - sunrise icon
            return "mdi:weather-sunset-up"
        elif wake_state.get("alarm_time"):
            # Scheduled - alarm icon
            return "mdi:alarm"
        else:
            # Not scheduled - alarm off icon
            return "mdi:alarm-off"
```

**Dashboard Display Examples**:

```
SENSOR: sensor.alp_wake_sequence_status

State: "Not Scheduled"
Icon: mdi:alarm-off

Attributes:
  active: false
  next_alarm: null
  wake_start_time: null
  duration_minutes: 15
  progress_percent: 0
  current_boost: 0
  max_boost: 20
  target_zone: "bedroom"
  active_zones: []
```

```
SENSOR: sensor.alp_wake_sequence_status

State: "Scheduled for 6:30 AM"
Icon: mdi:alarm

Attributes:
  active: false
  next_alarm: "2025-10-07T06:30:00+00:00"
  wake_start_time: "2025-10-07T06:15:00+00:00"
  duration_minutes: 15
  progress_percent: 0
  current_boost: 0
  max_boost: 20
  target_zone: "bedroom"
  active_zones: []
  time_until_alarm_seconds: 14328
  time_until_alarm_minutes: 238.8
  time_until_alarm_hours: 3.98
```

```
SENSOR: sensor.alp_wake_sequence_status

State: "Active (45% complete, 12% boost)"
Icon: mdi:weather-sunset-up

Attributes:
  active: true
  next_alarm: "2025-10-07T06:30:00+00:00"
  wake_start_time: "2025-10-07T06:15:00+00:00"
  duration_minutes: 15
  progress_percent: 45.2
  current_boost: 12
  max_boost: 20
  target_zone: "bedroom"
  active_zones: ["bedroom"]
```

**Benefits**:
- Human-readable state (glanceable)
- Dynamic icon (visual feedback)
- Rich attributes (automations can use)
- Time calculations (how long until alarm?)

**Dashboard Card Example**:

```yaml
type: entity
entity: sensor.alp_wake_sequence_status
name: Wake Sequence
secondary_info: last-changed
```

**Testing**:
- No alarm set → "Not Scheduled" with alarm-off icon
- Set alarm → "Scheduled for X" with alarm icon
- Wake starts → "Active (X% complete)" with sunrise icon
- Check attributes populated correctly

---

### PHASE 7: ENHANCEMENT #6 - ADDITIONAL DIAGNOSTIC SENSORS (2 hours)

**WHY**: Complete visibility for troubleshooting and monitoring. "Lives here" quality means user can see exactly what's happening.

**USER VALUE**:
- Last Action: When did coordinator last update? What changed?
- Timer Status: Which zones have active timers? How long remaining?
- Zone Health: Are all zones operational? Any issues?

#### Task 7.1: Last Action Timestamp Sensor

**File**: `custom_components/adaptive_lighting_pro/platforms/sensor.py`
**Location**: After ALPWakeSequenceStatusSensor

**Action**: ADD sensor class:

```python
class ALPLastActionSensor(ALPSensorBase):
    """Sensor tracking last coordinator action and timestamp.

    Use for:
    - Debugging: "When did coordinator last update?"
    - Monitoring: "Is coordinator stuck?"
    - Automation: Trigger on last_action change

    State: Timestamp of last coordinator update
    Attributes: What action occurred, what changed
    """

    def __init__(self, coordinator: ALPDataUpdateCoordinator) -> None:
        """Initialize last action sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_last_action"
        self._attr_name = "ALP Last Action"
        self._attr_icon = "mdi:history"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        """Return timestamp of last coordinator action.

        Returns:
            Datetime when coordinator last updated, or None if never updated
        """
        return self.coordinator.data.get("global", {}).get("last_update")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details about last action.

        Includes:
        - action_type: What happened (update, scene, adjustment, etc.)
        - affected_zones: Which zones changed
        - brightness_change: Current brightness adjustment
        - warmth_change: Current warmth adjustment
        - active_scene: Current scene name
        - health_score: System health at last update
        """
        global_data = self.coordinator.data.get("global", {})

        return {
            "action_type": global_data.get("last_action_type", "unknown"),
            "affected_zones": global_data.get("zones_updated", []),
            "brightness_adjustment": self.coordinator._brightness_adjustment,
            "warmth_adjustment": self.coordinator._warmth_adjustment,
            "active_scene": self.coordinator._current_scene.value if self.coordinator._current_scene else "none",
            "health_score": global_data.get("health_score", 100),
            "paused": global_data.get("paused", False),
        }

    @property
    def available(self) -> bool:
        """Return if sensor has valid data.

        Unavailable if coordinator has never updated.
        """
        return self.native_value is not None
```

**Dashboard Display**:
```
sensor.alp_last_action

State: 2025-10-06 15:32:18
Icon: mdi:history

Attributes:
  action_type: "manual_adjustment"
  affected_zones: ["kitchen", "living_room"]
  brightness_adjustment: 20
  warmth_adjustment: 0
  active_scene: "none"
  health_score: 95
  paused: false
```

---

#### Task 7.2: Timer Status Summary Sensor

**Action**: ADD sensor class:

```python
class ALPTimerStatusSensor(ALPSensorBase):
    """Sensor showing summary of all active manual timers.

    Use for:
    - Dashboard: Quick view of timer status
    - Automation: Trigger when all timers expire
    - Debugging: Which zones in manual mode?

    State: Human-readable count ("2 Active Timers", "No Active Timers")
    Attributes: Per-zone timer details with remaining time
    """

    def __init__(self, coordinator: ALPDataUpdateCoordinator) -> None:
        """Initialize timer status sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_timer_status"
        self._attr_name = "ALP Manual Timer Status"
        self._attr_icon = "mdi:timer-sand"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str:
        """Return count of active timers as human-readable string.

        Returns:
            "No Active Timers", "1 Active Timer", or "N Active Timers"
        """
        active_count = sum(
            1 for zone_id in self.coordinator.zones
            if self.coordinator.zone_manager.is_manual_control_active(zone_id)
        )

        if active_count == 0:
            return "No Active Timers"
        elif active_count == 1:
            return "1 Active Timer"
        else:
            return f"{active_count} Active Timers"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return per-zone timer details.

        Provides:
        - active_zones: List of zone IDs with active timers
        - timer_details: Per-zone remaining time (seconds, minutes, human-readable)
        - total_active: Count of active timers
        - next_expiry: When will first timer expire?
        """
        timers = {}

        for zone_id in self.coordinator.zones:
            if self.coordinator.zone_manager.is_manual_control_active(zone_id):
                remaining = self.coordinator.zone_manager.get_timer_remaining(zone_id)
                if remaining and remaining > 0:
                    minutes = remaining / 60

                    # Human-readable format
                    if minutes < 1:
                        human = f"{int(remaining)} sec"
                    elif minutes < 60:
                        human = f"{minutes:.1f} min"
                    else:
                        hours = minutes / 60
                        human = f"{hours:.1f} hr"

                    timers[zone_id] = {
                        "remaining_seconds": int(remaining),
                        "remaining_minutes": round(minutes, 1),
                        "remaining_human": human,
                    }

        attrs = {
            "active_zones": list(timers.keys()),
            "timer_details": timers,
            "total_active": len(timers),
        }

        # Find next timer to expire (soonest)
        if timers:
            next_zone = min(timers.items(), key=lambda x: x[1]["remaining_seconds"])
            attrs["next_expiry_zone"] = next_zone[0]
            attrs["next_expiry_seconds"] = next_zone[1]["remaining_seconds"]
            attrs["next_expiry_human"] = next_zone[1]["remaining_human"]

        return attrs

    @property
    def icon(self) -> str:
        """Return dynamic icon based on timer count.

        Returns:
            Icon reflecting timer state
        """
        active_count = sum(
            1 for zone_id in self.coordinator.zones
            if self.coordinator.zone_manager.is_manual_control_active(zone_id)
        )

        if active_count == 0:
            return "mdi:timer-off-outline"
        else:
            return "mdi:timer-sand"
```

**Dashboard Display**:
```
sensor.alp_manual_timer_status

State: "2 Active Timers"
Icon: mdi:timer-sand

Attributes:
  active_zones: ["kitchen", "bedroom"]
  timer_details:
    kitchen:
      remaining_seconds: 3420
      remaining_minutes: 57.0
      remaining_human: "57.0 min"
    bedroom:
      remaining_seconds: 1240
      remaining_minutes: 20.7
      remaining_human: "20.7 min"
  total_active: 2
  next_expiry_zone: "bedroom"
  next_expiry_seconds: 1240
  next_expiry_human: "20.7 min"
```

---

#### Task 7.3: Zone Health Summary Sensor

**Action**: ADD sensor class:

```python
class ALPZoneHealthSensor(ALPSensorBase):
    """Sensor showing health status of all zones.

    Use for:
    - Startup: "Are all zones operational?"
    - Troubleshooting: "Which zone has issues?"
    - Monitoring: "Has a zone become unavailable?"

    State: "All Zones Healthy", "N/M Zones Healthy", "All Zones Unavailable"
    Attributes: Per-zone health details (AL switch, lights, boundaries)
    """

    def __init__(self, coordinator: ALPDataUpdateCoordinator) -> None:
        """Initialize zone health sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_zone_health"
        self._attr_name = "ALP Zone Health"
        self._attr_icon = "mdi:heart-pulse"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str:
        """Return overall health status as human-readable string.

        Returns:
            "All Zones Healthy", "N/M Zones Healthy", or "All Zones Unavailable"
        """
        zone_states = self.coordinator.data.get("zones", {})

        healthy = sum(1 for state in zone_states.values() if state.get("available", False))
        total = len(zone_states)

        if total == 0:
            return "No Zones Configured"
        elif healthy == total:
            return "All Zones Healthy"
        elif healthy == 0:
            return "All Zones Unavailable"
        else:
            return f"{healthy}/{total} Zones Healthy"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return per-zone health details.

        For each zone provides:
        - available: Is zone operational?
        - al_switch_found: Is AL switch entity available?
        - lights_found: How many lights detected?
        - boundary_valid: Are min/max boundaries correct?
        """
        zone_states = self.coordinator.data.get("zones", {})

        health = {}
        for zone_id, state in zone_states.items():
            # Check boundary validity
            brightness_min = state.get("brightness_min", 0)
            brightness_max = state.get("brightness_max", 100)
            boundary_valid = brightness_min < brightness_max

            health[zone_id] = {
                "available": state.get("available", False),
                "al_switch_found": state.get("al_switch") is not None,
                "lights_count": len(state.get("lights", [])),
                "boundary_valid": boundary_valid,
                "brightness_range": f"{brightness_min}-{brightness_max}%",
            }

        attrs = {
            "zones": health,
            "healthy_count": sum(1 for h in health.values() if h["available"]),
            "total_zones": len(health),
        }

        # List unhealthy zones for quick identification
        unhealthy = [
            zone_id for zone_id, h in health.items()
            if not h["available"]
        ]
        if unhealthy:
            attrs["unhealthy_zones"] = unhealthy

        return attrs

    @property
    def icon(self) -> str:
        """Return dynamic icon based on health status.

        Returns:
            Icon reflecting health state
        """
        zone_states = self.coordinator.data.get("zones", {})

        if not zone_states:
            return "mdi:heart-off"

        healthy = sum(1 for state in zone_states.values() if state.get("available", False))
        total = len(zone_states)

        if healthy == total:
            return "mdi:heart"  # All healthy
        elif healthy == 0:
            return "mdi:heart-broken"  # All broken
        else:
            return "mdi:heart-half-full"  # Partial health
```

**Dashboard Display**:
```
sensor.alp_zone_health

State: "2/3 Zones Healthy"
Icon: mdi:heart-half-full

Attributes:
  zones:
    bedroom:
      available: true
      al_switch_found: true
      lights_count: 2
      boundary_valid: true
      brightness_range: "1-100%"
    kitchen:
      available: true
      al_switch_found: true
      lights_count: 3
      boundary_valid: true
      brightness_range: "10-100%"
    living_room:
      available: false  # ❌ Issue
      al_switch_found: false  # ❌ AL switch missing
      lights_count: 0
      boundary_valid: true
      brightness_range: "1-100%"
  healthy_count: 2
  total_zones: 3
  unhealthy_zones: ["living_room"]
```

---

#### Task 7.4: Register All New Sensors

**File**: `custom_components/adaptive_lighting_pro/platforms/sensor.py`
**Location**: Line 85 (async_setup_entry)

**Action**: UPDATE sensor registration:

```python
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up ALP sensor entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors: list[ALPSensorBase] = []

    # Existing sensors
    sensors.extend([
        ALPHealthScoreSensor(coordinator),
        ALPCurrentSceneSensor(coordinator),
        ALPBrightnessAdjustmentSensor(coordinator),
        ALPWarmthAdjustmentSensor(coordinator),
        ALPEnvironmentalBoostSensor(coordinator),
        ALPSunsetBoostSensor(coordinator),
        # ... other existing sensors ...
    ])

    # NEW: Additional diagnostic sensors
    sensors.extend([
        ALPWakeSequenceStatusSensor(coordinator),
        ALPLastActionSensor(coordinator),
        ALPTimerStatusSensor(coordinator),
        ALPZoneHealthSensor(coordinator),
    ])

    async_add_entities(sensors)
    return True
```

**Total Sensor Count**: 13 → 17 sensors (4 new)

**Benefits**:
- Complete visibility into system state
- Troubleshooting made easy
- Dashboard cards for monitoring
- Automation triggers on state changes

---

### PHASE 8: IMPLEMENTATION_2.YAML DASHBOARD CONTROLS (2-3 hours)

**WHY**: User needs dashboard control matching implementation_1.yaml functionality. One-click access to all features.

**USER REQUIREMENT**: Control everything from dashboard + see status + overnight reset.

#### Task 8.1: Create Dashboard Control Scripts

**File**: `implementation_2.yaml`
**Location**: After scene definitions (line ~200)

**Action**: ADD comprehensive script collection:

```yaml
# ============================================================================
# DASHBOARD CONTROL SCRIPTS
# ============================================================================
# These scripts provide one-click access to all ALP functionality from your
# Home Assistant dashboard or voice assistants.
#
# Usage:
# - Add to Lovelace dashboard (see lovelace_alp_card.yaml template)
# - Call from automations
# - Trigger via voice (Alexa, Google Assistant)
# - Execute from Developer Tools

script:
  # ========================================
  # SCENE CONTROLS
  # ========================================

  alp_scene_auto:
    alias: "ALP: Return to Auto"
    description: "Clear all scenes and restore automatic adaptive lighting"
    icon: mdi:sync
    sequence:
      # Clear all scenes via Scene.AUTO
      - service: adaptive_lighting_pro.apply_scene
        data:
          scene: auto

      # Notify user
      - service: notify.persistent_notification
        data:
          message: "All scenes cleared. Adaptive Lighting restored to automatic mode."
          title: "ALP: Auto Mode Restored"
          notification_id: "alp_scene_auto"

  alp_scene_all_lights:
    alias: "ALP: All Lights On"
    description: "Turn on all lights at normal adaptive levels"
    icon: mdi:lightbulb-on
    sequence:
      # Apply scene
      - service: adaptive_lighting_pro.apply_scene
        data:
          scene: all_lights

      # Turn on your light groups (customize entity_ids)
      - service: light.turn_on
        target:
          entity_id:
            - light.all_adaptive_lights  # ⚠️ CUSTOMIZE: Your "all lights" group
        data:
          transition: 2

  alp_scene_evening_comfort:
    alias: "ALP: Evening Comfort"
    description: "Dim warm lighting for evening relaxation"
    icon: mdi:weather-sunset
    sequence:
      # Apply scene offsets
      - service: adaptive_lighting_pro.apply_scene
        data:
          scene: evening_comfort

      # Your choreography: Turn off bright ceiling lights
      # ⚠️ CUSTOMIZE: Your bright lights
      - service: light.turn_off
        target:
          entity_id:
            - light.recessed_ceiling_lights
            - light.living_room_hallway_lights
        data:
          transition: 1

      # Your choreography: Turn on ambient lights
      # ⚠️ CUSTOMIZE: Your ambient lights
      - service: light.turn_on
        target:
          entity_id:
            - light.kitchen_island_pendants
            - light.living_room_credenza_light
            - light.living_room_corner_accent
        data:
          transition: 1

  alp_scene_ultra_dim:
    alias: "ALP: Ultra Dim"
    description: "Minimal lighting for movies or late night"
    icon: mdi:movie-open
    sequence:
      # Apply scene offsets
      - service: adaptive_lighting_pro.apply_scene
        data:
          scene: ultra_dim

      # Your choreography: Turn off most lights
      # ⚠️ CUSTOMIZE: Lights to turn off
      - service: light.turn_off
        target:
          entity_id:
            - light.dining_room_spot_lights
            - light.living_room_spot_lights
            - light.kitchen_main_lights
            - light.living_room_hallway_lights
        data:
          transition: 1

      # Your choreography: Minimal accent light
      # ⚠️ CUSTOMIZE: One dim light for safety
      - service: light.turn_on
        target:
          entity_id: light.kitchen_island_pendants
        data:
          brightness_pct: 10
          transition: 2

  # ========================================
  # QUICK ADJUSTMENTS
  # ========================================

  alp_brighter:
    alias: "ALP: Brighter (+20%)"
    description: "Increase brightness globally with smart timeout"
    icon: mdi:brightness-7
    sequence:
      - service: button.press
        target:
          entity_id: button.alp_brighter

  alp_dimmer:
    alias: "ALP: Dimmer (-20%)"
    description: "Decrease brightness globally with smart timeout"
    icon: mdi:brightness-4
    sequence:
      - service: button.press
        target:
          entity_id: button.alp_dimmer

  alp_warmer:
    alias: "ALP: Warmer (+500K)"
    description: "Make lights warmer (more yellow/orange)"
    icon: mdi:fire
    sequence:
      - service: button.press
        target:
          entity_id: button.alp_warmer

  alp_cooler:
    alias: "ALP: Cooler (-500K)"
    description: "Make lights cooler (more blue/white)"
    icon: mdi:snowflake
    sequence:
      - service: button.press
        target:
          entity_id: button.alp_cooler

  # ========================================
  # FINE CONTROL (Custom Adjustments)
  # ========================================

  alp_custom_brightness:
    alias: "ALP: Custom Brightness"
    description: "Set specific brightness adjustment (use with input_number)"
    icon: mdi:tune-vertical
    fields:
      adjustment:
        description: "Brightness adjustment percentage (-100 to 100)"
        example: "20"
        selector:
          number:
            min: -100
            max: 100
            step: 5
            mode: slider
    sequence:
      - service: number.set_value
        target:
          entity_id: number.alp_brightness_adjustment
        data:
          value: "{{ adjustment }}"

  alp_custom_warmth:
    alias: "ALP: Custom Warmth"
    description: "Set specific warmth adjustment (use with input_number)"
    icon: mdi:thermometer
    fields:
      adjustment:
        description: "Warmth adjustment in Kelvin (-2000 to 2000)"
        example: "-500"
        selector:
          number:
            min: -2000
            max: 2000
            step: 100
            mode: slider
    sequence:
      - service: number.set_value
        target:
          entity_id: number.alp_warmth_adjustment
        data:
          value: "{{ adjustment }}"

  # ========================================
  # RESET & RECOVERY
  # ========================================

  alp_reset_all:
    alias: "ALP: Reset Everything"
    description: "Clear all adjustments, timers, and scenes (back to defaults)"
    icon: mdi:restart
    sequence:
      # Step 1: Press reset button (clears adjustments and timers)
      - service: button.press
        target:
          entity_id: button.alp_reset

      # Step 2: Wait for reset to complete
      - delay:
          seconds: 1

      # Step 3: Clear scenes (return to auto)
      - service: adaptive_lighting_pro.apply_scene
        data:
          scene: auto

      # Step 4: Notify user
      - service: notify.persistent_notification
        data:
          message: |
            All adjustments cleared:
            • Brightness: 0%
            • Warmth: 0K
            • Scene: Auto
            • Timers: All cancelled
          title: "ALP: Complete Reset"
          notification_id: "alp_reset_complete"

  alp_overnight_reset:
    alias: "ALP: Overnight Reset"
    description: "Clear all state and restore defaults (run at 3 AM)"
    icon: mdi:sleep
    sequence:
      # Step 1: Clear all timers
      - service: button.press
        target:
          entity_id: button.alp_reset

      # Step 2: Restore auto mode
      - service: adaptive_lighting_pro.apply_scene
        data:
          scene: auto

      # Step 3: Reset all number entities to defaults
      - service: number.set_value
        target:
          entity_id: number.alp_brightness_adjustment
        data:
          value: 0

      - service: number.set_value
        target:
          entity_id: number.alp_warmth_adjustment
        data:
          value: 0

      # Step 4: Unpause if paused
      - service: switch.turn_off
        target:
          entity_id: switch.alp_pause_adaptive_control

      # Step 5: Log completion
      - service: logbook.log
        data:
          name: "ALP Overnight Reset"
          message: "All ALP state cleared and reset to defaults"

  # ========================================
  # STATUS DISPLAY
  # ========================================

  alp_show_status:
    alias: "ALP: Show Current Status"
    description: "Display comprehensive notification with current ALP state"
    icon: mdi:information-outline
    sequence:
      - service: notify.persistent_notification
        data:
          title: "ALP Status Report"
          notification_id: "alp_status_report"
          message: |
            **Current Scene:** {{ states('sensor.alp_current_scene') | title }}
            **Brightness Adjustment:** {{ states('number.alp_brightness_adjustment') }}%
            **Warmth Adjustment:** {{ states('number.alp_warmth_adjustment') }}K

            **Timers:** {{ states('sensor.alp_manual_timer_status') }}
            **Zone Health:** {{ states('sensor.alp_zone_health') }}
            **Wake Sequence:** {{ states('sensor.alp_wake_sequence_status') }}

            **System Health:** {{ states('sensor.alp_health_score') }}%
            **Last Action:** {{ relative_time(states('sensor.alp_last_action')) }} ago

            **Environmental Boost:** {{ states('sensor.alp_environmental_boost') }}%
            **Sunset Boost:** {{ states('sensor.alp_sunset_boost') }}%
```

**Customization Instructions** (add to top of scripts section):

```yaml
# ============================================================================
# CUSTOMIZATION GUIDE FOR DASHBOARD SCRIPTS
# ============================================================================
#
# STEP 1: Update Light Entity IDs
#   Search for "⚠️ CUSTOMIZE" comments in scripts below
#   Replace with your actual light entity IDs
#   Example: light.all_adaptive_lights → light.your_light_group
#
# STEP 2: Customize Scene Choreography
#   Each scene script has "Your choreography" sections
#   Modify which lights turn on/off based on YOUR home layout
#   Example: Add/remove lights from evening_comfort based on your setup
#
# STEP 3: Test Scripts
#   Developer Tools → Services → Select script
#   Run each script to verify behavior
#   Adjust timings/transitions as needed
#
# STEP 4: Add to Dashboard
#   See lovelace_alp_card.yaml for dashboard card template
#   Or use button cards, entity cards, etc.
```

**Benefits**:
- One-click access to all features
- Voice assistant compatible
- Customizable per user's home
- Status reporting built-in

---

#### Task 8.2: Add Overnight Reset Automation

**File**: `implementation_2.yaml`
**Location**: After dashboard scripts

**Action**: ADD automation:

```yaml
# ============================================================================
# OVERNIGHT RESET AUTOMATION (OPTIONAL - COMMENTED BY DEFAULT)
# ============================================================================
# Automatically reset ALP to defaults each night at 3 AM
# Ensures clean slate each day without accumulated state

# UNCOMMENT TO ENABLE:
# - id: alp_overnight_reset_automation
#   alias: "ALP: Overnight Reset (3 AM)"
#   description: "Clear all state and restore defaults each night"
#   mode: single
#
#   trigger:
#     - platform: time
#       at: "03:00:00"
#
#   condition:
#     # Safety: Don't reset if wake sequence scheduled within 2 hours
#     - condition: template
#       value_template: >
#         {% set wake_sensor = states('sensor.alp_wake_sequence_status') %}
#         {% if 'Scheduled for' in wake_sensor %}
#           {# Extract alarm time from sensor state #}
#           {% set alarm_str = wake_sensor.split('Scheduled for ')[1] %}
#           {# This is approximate - sensor provides full timestamp in attributes #}
#           {% set alarm_time = state_attr('sensor.alp_wake_sequence_status', 'next_alarm') %}
#           {% if alarm_time %}
#             {% set hours_until = (as_timestamp(alarm_time) - now().timestamp()) / 3600 %}
#             {{ hours_until > 2 }}
#           {% else %}
#             true
#           {% endif %}
#         {% else %}
#           true
#         {% endif %}
#
#   action:
#     # Call overnight reset script
#     - service: script.alp_overnight_reset
#
#     # Optional: Log to persistent notification
#     # - service: notify.persistent_notification
#     #   data:
#     #     message: "Overnight reset completed at {{ now().strftime('%I:%M %p') }}"
#     #     title: "ALP: Overnight Reset"
#     #     notification_id: "alp_overnight_reset"
```

**Safety Features**:
- Checks wake sequence timing (doesn't reset if alarm < 2 hours away)
- Mode: single (prevents overlapping runs)
- Commented by default (user opts in)

**Benefits**:
- Fresh state each day
- Prevents state accumulation
- Respects wake sequence
- Optional (user choice)

---

#### Task 8.3: Create Lovelace Dashboard Card Template

**File**: Create new file `lovelace_alp_card.yaml` in root directory

**Action**: CREATE comprehensive dashboard template:

```yaml
# ============================================================================
# ALP CONTROL DASHBOARD CARD TEMPLATE
# ============================================================================
# Copy this into your Lovelace dashboard configuration
#
# INSTALLATION:
# 1. Open your Home Assistant dashboard in edit mode
# 2. Add a new "Manual" card
# 3. Copy this YAML into the card configuration
# 4. Save and test
#
# REQUIREMENTS:
# - Adaptive Lighting Pro integration installed
# - Dashboard scripts from implementation_2.yaml added
# - Entity IDs match your configuration

type: vertical-stack
title: "Adaptive Lighting Pro"
cards:
  # ========================================
  # SCENE CONTROLS
  # ========================================
  - type: entities
    title: "⚡ Quick Scenes"
    show_header_toggle: false
    state_color: true
    entities:
      - entity: script.alp_scene_auto
        name: "🔄 Return to Auto"
        secondary_info: none

      - entity: script.alp_scene_all_lights
        name: "💡 All Lights On"
        secondary_info: none

      - entity: script.alp_scene_evening_comfort
        name: "🌅 Evening Comfort"
        secondary_info: none

      - entity: script.alp_scene_ultra_dim
        name: "🌙 Ultra Dim"
        secondary_info: none

  # ========================================
  # QUICK ADJUSTMENTS
  # ========================================
  - type: entities
    title: "🎨 Quick Adjustments"
    show_header_toggle: false
    entities:
      - type: buttons
        entities:
          - entity: script.alp_brighter
            name: "Brighter"
            icon: mdi:brightness-7
            tap_action:
              action: call-service
              service: script.alp_brighter

          - entity: script.alp_dimmer
            name: "Dimmer"
            icon: mdi:brightness-4
            tap_action:
              action: call-service
              service: script.alp_dimmer

          - entity: script.alp_warmer
            name: "Warmer"
            icon: mdi:fire
            tap_action:
              action: call-service
              service: script.alp_warmer

          - entity: script.alp_cooler
            name: "Cooler"
            icon: mdi:snowflake
            tap_action:
              action: call-service
              service: script.alp_cooler

  # ========================================
  # FINE CONTROL SLIDERS
  # ========================================
  - type: entities
    title: "🎛️ Fine Control"
    show_header_toggle: false
    entities:
      - entity: number.alp_brightness_adjustment
        name: "Brightness Adjustment"
        icon: mdi:brightness-6

      - entity: number.alp_warmth_adjustment
        name: "Warmth Adjustment"
        icon: mdi:thermometer

  # ========================================
  # CURRENT STATUS
  # ========================================
  - type: entities
    title: "📊 Current Status"
    show_header_toggle: false
    state_color: true
    entities:
      - entity: sensor.alp_current_scene
        name: "Active Scene"
        icon: mdi:script-text-outline

      - entity: sensor.alp_manual_timer_status
        name: "Manual Timers"
        icon: mdi:timer-sand

      - entity: sensor.alp_wake_sequence_status
        name: "Wake Sequence"
        icon: mdi:alarm

      - entity: sensor.alp_health_score
        name: "System Health"
        icon: mdi:heart-pulse

      - entity: sensor.alp_zone_health
        name: "Zone Health"
        icon: mdi:home-group

      - type: divider

      - entity: sensor.alp_environmental_boost
        name: "Environmental Boost"
        icon: mdi:weather-cloudy

      - entity: sensor.alp_sunset_boost
        name: "Sunset Boost"
        icon: mdi:weather-sunset

  # ========================================
  # SYSTEM CONTROL
  # ========================================
  - type: entities
    title: "⚙️ System Control"
    show_header_toggle: false
    entities:
      - entity: switch.alp_pause_adaptive_control
        name: "Pause Adaptive Lighting"
        icon: mdi:pause

      - type: divider

      - entity: script.alp_reset_all
        name: "🔄 Reset Everything"
        tap_action:
          action: call-service
          service: script.alp_reset_all
          confirmation:
            text: "Reset all adjustments, timers, and scenes?"

      - entity: script.alp_show_status
        name: "ℹ️ Show Status Report"
        tap_action:
          action: call-service
          service: script.alp_show_status

# ============================================================================
# ALTERNATIVE: COMPACT BUTTON CARD (Requires custom:button-card from HACS)
# ============================================================================
# Uncomment if you have button-card installed for a more visual layout
#
# type: vertical-stack
# cards:
#   - type: horizontal-stack
#     cards:
#       - type: custom:button-card
#         entity: script.alp_scene_auto
#         name: "Auto"
#         icon: mdi:sync
#         tap_action:
#           action: call-service
#           service: script.alp_scene_auto
#
#       - type: custom:button-card
#         entity: script.alp_scene_all_lights
#         name: "All On"
#         icon: mdi:lightbulb-on
#         tap_action:
#           action: call-service
#           service: script.alp_scene_all_lights
#
#   - type: horizontal-stack
#     cards:
#       - type: custom:button-card
#         entity: script.alp_brighter
#         name: "Brighter"
#         icon: mdi:brightness-7
#         tap_action:
#           action: call-service
#           service: script.alp_brighter
#
#       - type: custom:button-card
#         entity: script.alp_dimmer
#         name: "Dimmer"
#         icon: mdi:brightness-4
#         tap_action:
#           action: call-service
#           service: script.alp_dimmer
```

**Additional Template**: Mobile-Friendly Compact Version

```yaml
# ============================================================================
# MOBILE-FRIENDLY COMPACT VERSION
# ============================================================================
# Optimized for phone screens

type: vertical-stack
cards:
  # Quick Actions (2x2 grid)
  - type: grid
    columns: 2
    square: false
    cards:
      - type: button
        entity: script.alp_scene_auto
        name: "Auto"
        icon: mdi:sync
        tap_action:
          action: call-service
          service: script.alp_scene_auto

      - type: button
        entity: script.alp_scene_evening_comfort
        name: "Evening"
        icon: mdi:weather-sunset
        tap_action:
          action: call-service
          service: script.alp_scene_evening_comfort

      - type: button
        entity: script.alp_brighter
        name: "Brighter"
        icon: mdi:brightness-7
        tap_action:
          action: call-service
          service: script.alp_brighter

      - type: button
        entity: script.alp_dimmer
        name: "Dimmer"
        icon: mdi:brightness-4
        tap_action:
          action: call-service
          service: script.alp_dimmer

  # Status Glance
  - type: glance
    title: "Status"
    show_name: true
    show_state: true
    entities:
      - entity: sensor.alp_current_scene
        name: "Scene"
      - entity: sensor.alp_manual_timer_status
        name: "Timers"
      - entity: sensor.alp_health_score
        name: "Health"
```

**Benefits**:
- Multiple layout options (entities, buttons, grid, glance)
- Mobile-optimized version included
- Confirmation on destructive actions (reset)
- Status visibility at a glance
- Copy-paste ready

---

## QUALITY ASSURANCE & TESTING

### Pre-Flight Checklist (Run Before Each Phase)

**Architectural Integrity**:
```bash
# Check for coordinator data access violations
grep -r "coordinator\.data\[" custom_components/adaptive_lighting_pro/platforms/
grep -r "coordinator\.data\[" custom_components/adaptive_lighting_pro/services.py

# Expected: 0 matches (or only documented exceptions)

# Check for private attribute access violations
grep -r "coordinator\._" custom_components/adaptive_lighting_pro/platforms/
grep -r "coordinator\._" custom_components/adaptive_lighting_pro/services.py

# Expected: 0 matches (excluding "_coordinator" references)
```

**Code Quality**:
```bash
# Run all tests
.venv/bin/pytest tests/unit/ -v --tb=short

# Expected: >98% pass rate (>207/211 tests)

# Check syntax
python3 -m py_compile custom_components/adaptive_lighting_pro/coordinator.py
python3 -m py_compile custom_components/adaptive_lighting_pro/platforms/*.py

# Expected: No syntax errors
```

**Integration Test** (Development HA Instance):
1. Load integration
2. Verify all entities appear
3. Test each dashboard script
4. Check sensor values update
5. Monitor logs for errors

---

### Post-Implementation Verification (After Each Phase)

**Phase 1 (Foundation)**:
- [ ] `_clear_zone_manual_control()` method added
- [ ] Scene.AUTO in enum and SCENE_CONFIGS
- [ ] Apply Scene.AUTO → verify all zones cleared
- [ ] Apply Scene.EVENING_COMFORT → Scene.AUTO → verify restore

**Phase 2 (Quick Setup)**:
- [ ] Mock 3 AL switches → Quick Setup detects them
- [ ] Quick Setup creates 3 zone configs
- [ ] Config entry persists after HA restart
- [ ] Manual Setup still works if chosen

**Phase 3 (Zone Timeouts)**:
- [ ] Set kitchen timeout to 2hr via number entity
- [ ] Press kitchen button → timer = 2hr
- [ ] Restart HA → timeout setting persists
- [ ] Zone without override uses global

**Phase 4 (Sonos)**:
- [ ] Set wake alarm → event fires
- [ ] Event data populated correctly
- [ ] Automation template copies without errors
- [ ] Chime plays at gentle volume (if uncommented)

**Phase 5 (Smart Timeouts)**:
- [ ] Late night dim → see 2.0x * 1.3x in logs
- [ ] Daytime bright → see 1.0x in logs
- [ ] Smart duration = base * multipliers

**Phase 6 (Wake Sensor)**:
- [ ] No alarm → "Not Scheduled"
- [ ] Set alarm → "Scheduled for X"
- [ ] Wake starts → "Active (X% complete)"
- [ ] Attributes populated

**Phase 7 (Diagnostic Sensors)**:
- [ ] Last action timestamp updates
- [ ] Timer status shows active zones
- [ ] Zone health shows all zones
- [ ] Unhealthy zones listed if any issues

**Phase 8 (Dashboard)**:
- [ ] All scripts copy without errors
- [ ] Scene buttons work
- [ ] Adjustment buttons work
- [ ] Status report shows current state
- [ ] Lovelace card renders correctly

---

## DELIVERY TIMELINE & EFFORT ESTIMATES

**Phase 1: Critical Foundation** - 2-3 hours
- Task 1.1: Add method (30 min)
- Task 1.2: Scene.AUTO (1 hr)
- Task 1.3: Documentation (30 min)
- Testing: 30 min

**Phase 2: Quick Setup** - 2-3 hours
- Task 2.1: Detection logic (1 hr)
- Task 2.2: User step (30 min)
- Task 2.3: Step handlers (1 hr)
- Testing: 30 min

**Phase 3: Zone Timeouts** - 2-3 hours
- Task 3.1: Validation (30 min)
- Task 3.2: Get/Set methods (1 hr)
- Task 3.3: Timer integration (30 min)
- Task 3.4: Number entities (1 hr)
- Testing: 30 min

**Phase 4: Sonos Notifications** - 1 hour
- Task 4.1: Start event (15 min)
- Task 4.2: Complete event (15 min)
- Task 4.3: Automation template (30 min)

**Phase 5: Smart Timeouts** - 1-2 hours
- Task 5.1: Calculation (1 hr)
- Task 5.2: Integration (30 min)
- Testing: 30 min

**Phase 6: Wake Sensor** - 1 hour
- Task 6.1: Sensor class (45 min)
- Testing: 15 min

**Phase 7: Diagnostic Sensors** - 2 hours
- Task 7.1-7.3: Three sensors (1.5 hr)
- Task 7.4: Registration (15 min)
- Testing: 15 min

**Phase 8: Dashboard** - 2-3 hours
- Task 8.1: Scripts (1.5 hr)
- Task 8.2: Automation (30 min)
- Task 8.3: Lovelace (1 hr)

**TOTAL ESTIMATED TIME**: 13-18 hours of focused development

**Recommended Schedule**:
- **Week 1**: Phases 1-2 (foundation + quick setup)
- **Week 2**: Phases 3-4 (timeouts + notifications)
- **Week 3**: Phases 5-7 (smart timeouts + sensors)
- **Week 4**: Phase 8 + final testing (dashboard + QA)

---

## SUCCESS CRITERIA (@claude.md Quality Bar)

**"Would I want to live with this every day?"**

### Functional Completeness
- ✅ All critical fixes implemented
- ✅ Wake sequence locks lights properly
- ✅ Scenes persist until cleared
- ✅ Quick "return to auto" works
- ✅ Dashboard control complete
- ✅ All enhancements functional

### Quality Standards
- ✅ >98% test pass rate maintained
- ✅ 0 architectural violations
- ✅ Comprehensive logging
- ✅ Error handling graceful
- ✅ Documentation complete

### Daily Life Experience
- ✅ Morning wake sequence delightful
- ✅ Manual adjustments respected
- ✅ Scenes intuitive
- ✅ Dashboard one-click control
- ✅ Never fight the system
- ✅ Forget it exists (it just works)

**Bottom Line**: Ship when you'd be proud to show this to the Anthropic team and confident living with it every day.

---

## NOTES & DEPENDENCIES

**User Decisions Required**: None (personal deployment confirmed)

**External Dependencies**:
- Home Assistant 2023.8+ (for modern config flow features)
- Adaptive Lighting integration installed
- Python 3.11+ (for modern type hints)

**Optional Dependencies**:
- Sonos integration (for wake notifications)
- Mobile app (for mobile notifications)
- custom:button-card (for enhanced dashboard cards)

**Configuration Files Modified**:
- `coordinator.py` (coordinator methods, state tracking)
- `const.py` (Scene.AUTO enum, SCENE_CONFIGS)
- `config_flow.py` (Quick Setup flow)
- `platforms/number.py` (zone timeout entities)
- `platforms/sensor.py` (4 new diagnostic sensors)
- `features/zone_manager.py` (smart timeout calculation)
- `implementation_2.yaml` (dashboard scripts, automations)
- New: `lovelace_alp_card.yaml` (dashboard template)

**No Breaking Changes**: All additions are backwards compatible.

---

**END OF PRODUCTION READINESS PLAN**

---

**Remember**: This is YOUR home. Every line of code affects your daily life. Excellence is the baseline.
