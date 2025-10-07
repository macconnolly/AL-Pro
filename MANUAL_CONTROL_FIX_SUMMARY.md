# Adaptive Lighting Pro - Manual Control Architecture Fix

## Critical Understanding
ALP is NOT a separate system from AL - it's an enhancement layer that works WITH Adaptive Lighting's manual_control feature.

## Key Architectural Principles

### 1. Two Different Control Paradigms
- **Brightness/Warmth Adjustments**: Use asymmetric boundaries, AL continues adapting within shifted ranges
- **Scenes**: Use manual_control to lock specific lights at scene-defined levels

### 2. Manual Control Requirements
- AL's `manual_control` requires INDIVIDUAL light entities, NOT groups
- Groups must be expanded to their member lights before passing to AL services

### 3. Timer Purpose
- Timers track when to reset temporary adjustments or release manual control
- Timer expiry has different meanings based on context:
  - For adjustments: Reset brightness/warmth values to 0
  - For scenes: Clear manual_control on individual lights

## Fixes Applied

### 1. Fixed `_mark_zone_lights_as_manual()` in coordinator.py
**Problem**: Was passing light groups to AL's manual_control
**Solution**: Expand groups to individual lights before calling AL service

```python
# CRITICAL: Expand groups to individual lights!
# AL's manual_control requires individual light entities, not groups
individual_lights = []
for light_entity in lights:
    state = self.hass.states.get(light_entity)
    if state and state.attributes.get("entity_id"):
        # It's a group, expand it
        group_members = state.attributes.get("entity_id", [])
        individual_lights.extend(group_members)
    else:
        # It's already an individual light
        individual_lights.append(light_entity)
```

### 2. Fixed `_restore_adaptive_control()` in coordinator.py
**Problem**: Always cleared manual_control regardless of timer type
**Solution**: Check if manual_control exists before trying to clear it

```python
# Check if AL has any manual_control set for this zone
al_state = self.hass.states.get(al_switch)
has_manual_control = False
if al_state and al_state.attributes:
    current_manual = al_state.attributes.get("manual_control", [])
    has_manual_control = bool(current_manual)

# Only clear manual_control if there is any set (scene case)
if has_manual_control:
    # Clear manual control logic...
```

### 3. Verified Brightness/Warmth Adjustments
**Confirmed**: `set_brightness_adjustment()` and `set_warmth_adjustment()` do NOT set manual_control
- They only start timers to track when to reset adjustments
- AL continues adapting within asymmetric boundaries

### 4. Verified Scene Implementation
**Confirmed**: Scenes in const.py correctly set manual_control on individual lights
```python
Scene.ALL_LIGHTS: {
    "actions": [
        {
            "action": "adaptive_lighting.set_manual_control",
            "entity_id": "switch.adaptive_lighting_accent_spots",
            "lights": [
                "light.dining_room_spot_lights",  # Individual lights!
                "light.living_room_spot_lights",
            ],
            "manual_control": True,
        },
    ]
}
```

## Testing Checklist

### Brightness/Warmth Adjustments
- [ ] Press Zen32 brighter button → lights brighten immediately
- [ ] Check AL switch → manual_control should be EMPTY
- [ ] AL continues adapting within new boundaries
- [ ] Timer expires → adjustments reset to 0, lights return to normal

### Scene Application
- [ ] Apply "All Lights" scene → specific lights lock at scene levels
- [ ] Check AL switch → manual_control shows individual light entities
- [ ] AL refresh → scene lights stay at defined levels
- [ ] Timer expires → manual_control cleared, lights return to AL control

### Asymmetric Boundaries
- [ ] Brightness +20% → minimum raised, maximum unchanged
- [ ] Brightness -20% → minimum unchanged, maximum lowered
- [ ] Warmth adjustments work similarly with color temperature

## Files Modified
1. `/custom_components/adaptive_lighting_pro/coordinator.py`
   - `_mark_zone_lights_as_manual()` - Added group expansion
   - `_restore_adaptive_control()` - Added conditional manual_control clearing
   - Comments updated to clarify architecture

## Key Insights from implementation_1.yaml
1. Brighter/dimmer scripts do NOT set manual_control (lines 2600-2630)
2. Scenes set manual_control on individual lights (lines 3105-3111)
3. Timer expiry handlers clear manual_control (lines 1926-1999)
4. AL detects physical changes and sets manual_control automatically (lines 2264-2310)

## Deployment
1. Upload modified coordinator.py to Home Assistant
2. Restart Home Assistant (or reload integration if possible)
3. Test both adjustment and scene scenarios
4. Monitor logs for proper group expansion and manual_control handling