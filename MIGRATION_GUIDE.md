# Migration Guide: implementation_1.yaml → implementation_2.yaml

## Overview

**implementation_1.yaml:** 3,216 lines - Massive YAML automation replicating integration functionality
**implementation_2.yaml:** ~240 lines - Minimal user configuration complementing integration

**Reduction:** 94% fewer lines, zero duplication, cleaner architecture

---

## 🎯 What Changed and Why

### The Problem with implementation_1.yaml

The original YAML package duplicated almost everything the integration already does:
- Input helpers tracking state → Coordinator manages state
- Template sensors → Sensor platform provides 13+ sensors
- Scripts for adjustments → Button platform + services
- Automations for calculations → Coordinator handles in update cycle
- Zen32 automation → Zen32Integration class
- Sonos automation → SonosIntegration class

**Result:** Two places to maintain, two places to break, scattered state, difficult debugging.

### The Solution: implementation_2.yaml

Following architectural principles from claude.md:
- **Integration owns business logic** (calculations, state, coordination)
- **YAML owns user configuration** (which lights, which scenes, choreography)
- **Single source of truth** (coordinator state, not input helpers)
- **Clean separation** (no duplication)

---

## 📋 Entity Mapping: Old → New

### Input Helpers → Integration State (DELETE)

| Old (implementation_1.yaml) | New (Integration) |
|------------------------------|-------------------|
| `input_number.adaptive_lighting_total_brightness_adjustment` | `sensor.alp_brightness_adjustment` (read)<br>`service: adaptive_lighting_pro.adjust_brightness` (write) |
| `input_number.adaptive_lighting_total_warmth_adjustment` | `sensor.alp_warmth_adjustment` (read)<br>`service: adaptive_lighting_pro.adjust_color_temp` (write) |
| `input_number.adaptive_lighting_environmental_brightness_offset` | `sensor.alp_environmental_boost` |
| `input_number.al_sunset_fade_brightness_offset` | `sensor.alp_sunset_boost` |
| `input_number.al_scene_brightness_offset` | `sensor.alp_status` (attribute: scene_brightness_offset) |
| `input_number.al_wake_sequence_offset` | `sensor.alp_wake_sequence_offset` |
| `input_number.adaptive_lighting_brightness_increment` | `number.alp_brightness_increment` |
| `input_number.adaptive_lighting_color_temp_increment` | `number.alp_color_temp_increment` |

### Boolean Flags → Integration State (DELETE)

| Old (implementation_1.yaml) | New (Integration) |
|------------------------------|-------------------|
| `input_boolean.al_environmental_boost_active` | `sensor.alp_environmental_boost` (state > 0) |
| `input_boolean.al_globally_paused` | `switch.alp_pause` (if needed - add to integration) |
| `input_boolean.al_script_brighter_active` | Not needed (buttons are stateless) |
| All mode booleans | `select.alp_scene` |

### Timers → Zone Manager (DELETE)

| Old (implementation_1.yaml) | New (Integration) |
|------------------------------|-------------------|
| `timer.adaptive_lighting_manual_timer_main_living` | Zone manager handles internally |
| `timer.adaptive_lighting_manual_timer_*` (all zones) | Per-zone sensors show timer state |

### Template Sensors → Sensor Platform (DELETE)

| Old (implementation_1.yaml) | New (Integration) |
|------------------------------|-------------------|
| `sensor.adaptive_lighting_realtime_monitor` | `sensor.alp_realtime_monitor` |
| `sensor.adaptive_lighting_status` | `sensor.alp_status` |
| `sensor.adaptive_lighting_manual_control_living` | `sensor.alp_manual_control_main_living` |
| `sensor.adaptive_lighting_total_manual_control` | `sensor.alp_total_manual_control` |
| `sensor.adaptive_lighting_zones_with_manual_control` | `sensor.alp_zones_with_manual_control` |
| `sensor.adaptive_lighting_deviation_tracker` | `sensor.alp_deviation_tracker` |
| `sensor.adaptive_lighting_brightness_status` | `sensor.alp_brightness_adjustment` |
| `sensor.adaptive_lighting_system_health` | `sensor.alp_system_health` |
| `sensor.adaptive_lighting_sunrise_times` | `sensor.alp_next_alarm` |

### Scripts → Services + Buttons (DELETE)

| Old (implementation_1.yaml) | New (Integration) |
|------------------------------|-------------------|
| `script.adaptive_lighting_brighter` | `button.alp_brighter` or<br>`service: adaptive_lighting_pro.adjust_brightness` with `value: 10` |
| `script.adaptive_lighting_dimmer` | `button.alp_dimmer` or<br>`service: adaptive_lighting_pro.adjust_brightness` with `value: -10` |
| `script.adaptive_lighting_warmer` | `button.alp_warmer` or<br>`service: adaptive_lighting_pro.adjust_color_temp` with `value: -250` |
| `script.adaptive_lighting_cooler` | `button.alp_cooler` or<br>`service: adaptive_lighting_pro.adjust_color_temp` with `value: 250` |
| `script.adaptive_lighting_reset_manual_adjustments` | `button.alp_reset` or<br>`service: adaptive_lighting_pro.reset_manual_adjustments` |
| `script.adaptive_lighting_reset_all_adjustments` | `service: adaptive_lighting_pro.reset_all` |

### Scene Scripts → Button + Choreography (KEEP CHOREOGRAPHY)

| Old (implementation_1.yaml) | New (implementation_2.yaml) |
|------------------------------|------------------------------|
| `script.apply_lighting_scene` | `button.alp_scene_all_lights` (integration)<br>+ `script.apply_scene_all_lights` (choreography in YAML) |

### Automations → Coordinator (DELETE)

| Old (implementation_1.yaml) | New (Integration) |
|------------------------------|-------------------|
| `automation.al_startup_cleanup` | `coordinator.async_initialize()` |
| `automation.al_core_adjustment_engine_v2` | `coordinator._async_update_data()` |
| `automation.adaptive_lighting_low_light_boost` | `EnvironmentalAdapter.calculate_boost()` |
| `automation.adaptive_lighting_sunset_fade` | `SunsetBoostCalculator.calculate_boost()` |
| `automation.al_manual_timer_expired_*` | `ZoneManager.async_update_timers()` |
| `automation.zen32_scene_controller` | `Zen32Integration.async_setup()` |
| `automation.adaptive_lighting_dynamic_sunrise_all` | `SonosIntegration.async_setup()` |

---

## 🚀 Migration Steps

### Step 1: Backup Current Configuration

```bash
cp /config/packages/implementation_1.yaml /config/packages/implementation_1.yaml.backup
```

### Step 2: Install/Update Integration

Ensure you have the latest Adaptive Lighting Pro integration installed:
- Place in `custom_components/adaptive_lighting_pro/`
- Restart Home Assistant
- Configure via UI (Config Flow)

### Step 3: Replace YAML Configuration

```bash
# Remove old package
rm /config/packages/implementation_1.yaml

# Add new minimal package
cp implementation_2.yaml /config/packages/adaptive_lighting_pro.yaml
```

### Step 4: Update Dashboard References

**Old Dashboard YAML:**
```yaml
type: entities
entities:
  - entity: input_number.adaptive_lighting_total_brightness_adjustment
  - entity: input_select.current_home_mode
  - entity: sensor.adaptive_lighting_status
```

**New Dashboard YAML:**
```yaml
type: entities
entities:
  - entity: sensor.alp_brightness_adjustment
  - entity: select.alp_scene
  - entity: sensor.alp_status
```

### Step 5: Update Automations/Scripts

**Old Automation:**
```yaml
automation:
  - trigger:
      platform: numeric_state
      entity_id: sensor.living_room_lux
      below: 500
    action:
      - service: script.adaptive_lighting_brighter
```

**New Automation:**
```yaml
automation:
  - trigger:
      platform: numeric_state
      entity_id: sensor.living_room_lux
      below: 500
    action:
      - service: adaptive_lighting_pro.adjust_brightness
        data:
          value: 20
```

Or simply:
```yaml
    action:
      - service: button.press
        target:
          entity_id: button.alp_brighter
```

### Step 6: Restart and Verify

1. Restart Home Assistant
2. Check integration entities are available (Developer Tools → States)
3. Test buttons and services
4. Verify sensors updating
5. Test scene application

---

## 🔍 Testing Checklist

After migration, verify:

- [ ] All integration entities appear (13+ sensors, 9+ buttons, 2 numbers, 1 select, 1+ switches)
- [ ] Brightness adjustment buttons work
- [ ] Color temperature adjustment buttons work
- [ ] Scene selection works (select.alp_scene)
- [ ] Scene buttons trigger choreography scripts
- [ ] Environmental boost activates on dark days
- [ ] Sunset boost activates during sunset
- [ ] Manual control detection works (touch light physically, see sensor update)
- [ ] Zone timers expire and restore adaptive control
- [ ] Zen32 buttons work (if configured)
- [ ] Sonos wake sequence works (if configured)
- [ ] System health sensor shows "Excellent" or "Good"

---

## 🐛 Troubleshooting

### Issue: Entities not appearing

**Cause:** Integration not loaded or config flow not completed
**Fix:** Check Configuration → Integrations → Add Integration → "Adaptive Lighting Pro"

### Issue: Buttons don't do anything

**Cause:** Coordinator not running or AL integration switches offline
**Fix:** Check `sensor.alp_system_health` - should show AL switches online

### Issue: Scenes not applying light patterns

**Cause:** Choreography scripts not loaded from implementation_2.yaml
**Fix:** Verify YAML in packages folder, check Configuration → Server Controls → Check Configuration

### Issue: Environmental boost not working

**Cause:** Lux sensor or weather entity not configured
**Fix:** Check integration config, verify entities exist

### Issue: Sensors show "unknown" or "unavailable"

**Cause:** Coordinator not updating or AL integration not available
**Fix:**
1. Check `sensor.alp_system_health`
2. Verify AL integration running: `switch.adaptive_lighting_*` entities exist
3. Check logs: Settings → System → Logs, filter "adaptive_lighting_pro"

---

## 📚 Key Concepts

### Integration Owns State

The coordinator maintains ALL state internally:
- Current brightness/warmth adjustments
- Environmental boost values
- Scene offsets
- Zone timer states
- Manual control flags

**DO NOT** create input helpers to track these. Use integration sensors instead.

### Services for Actions

All actions go through integration services:
```yaml
# Adjust brightness
service: adaptive_lighting_pro.adjust_brightness
data:
  value: 20

# Apply scene
service: adaptive_lighting_pro.apply_scene
data:
  scene: evening_comfort

# Reset everything
service: adaptive_lighting_pro.reset_all
```

### Sensors for Visibility

All state is exposed via sensors:
```yaml
# Current brightness adjustment
sensor.alp_brightness_adjustment

# Current scene
sensor.alp_status
  attributes:
    current_scene: "evening_comfort"

# System health
sensor.alp_system_health
  state: "Excellent"
```

### YAML for User Configuration

Only user-specific configuration belongs in YAML:
- Light groups (your physical lights)
- Scene choreography (which lights for which scenes)
- Dashboard helpers (optional, if you prefer input_select)

---

## 🎓 Architecture Philosophy

From claude.md:

> **Integration owns business logic** - Calculations, state management, coordination
> **YAML owns user configuration** - Which lights, which scenes, personal preferences
> **Single source of truth** - Coordinator state, not scattered input helpers
> **Clean boundaries** - No duplication between integration and YAML

This migration brings your setup in line with these principles:
- ✅ One place to update (integration)
- ✅ One place to test (coordinator)
- ✅ One source of truth (coordinator state)
- ✅ Clear separation (business logic vs user config)

---

## 📞 Support

If you encounter issues after migration:

1. Check logs: Settings → System → Logs → Filter "adaptive_lighting_pro"
2. Verify config: Developer Tools → States → Filter "alp_"
3. Check health: `sensor.alp_system_health`
4. Review TODO.md for known issues
5. Open issue on GitHub with logs and configuration

---

## ✅ Success Metrics

After successful migration, you should have:

- **~240 lines** of YAML (vs 3,216)
- **Zero duplication** between integration and YAML
- **13+ sensors** providing complete visibility
- **9+ buttons** for quick actions
- **All functionality** preserved and working
- **Easier maintenance** - update integration, not YAML
- **Better testability** - coordinator has unit tests
- **Cleaner logs** - single namespace, clear errors
