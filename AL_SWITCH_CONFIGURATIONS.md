# Adaptive Lighting Switch Configurations
**Date**: 2025-10-06 (Updated)
**Purpose**: Document exact AL switch configs from implementation_1.yaml for implementation_2 migration
**Status**: ✅ COMPLETE - All configs added to implementation_2.yaml

---

## ✅ UPDATE: All AL Switch Configurations NOW INCLUDED

**Good News**: As of commit b5e8687c, implementation_2.yaml NOW includes all 5 Adaptive Lighting switch configurations from implementation_1.yaml!

**Location in implementation_2.yaml**: Lines 136-240 (adaptive_lighting section)

**Additional File Created**: `adaptive_lighting_pro_zones.yaml` with complete ALP integration zone configs

**What's Included**:
- All 5 AL base integration switches with exact parameters
- `light.all_adaptive_lights` group (13 lights total)
- `group.adaptive_lighting_switches` for tracking
- Complete ALP zone configurations matching AL switches

---

## Required AL Switch Configurations (from implementation_1.yaml)

These switches MUST be configured in Home Assistant UI under:
**Settings → Devices & Services → Adaptive Lighting → Add Entry**

Or included in a `configuration.yaml` package file for persistence.

### Switch 1: recessed_ceiling

```yaml
adaptive_lighting:
  - name: "recessed_ceiling"
    lights:
      - light.kitchen_main_lights
      - light.living_room_hallway_lights

    # Brightness Configuration
    min_brightness: 2
    max_brightness: 23
    sleep_brightness: 1

    # Color Temperature Configuration
    # (Uses AL defaults - not specified in impl_1)

    # Timing Configuration
    initial_transition: 0
    transition: 0
    sleep_transition: 3
    interval: 20
    adapt_delay: 0

    # Control Behavior
    autoreset_control_seconds: 0
    take_over_control: true
    detect_non_ha_changes: true
    skip_redundant_commands: true

    # Advanced
    include_config_in_attributes: true
```

**Purpose**: Overhead ceiling lights - kept very dim (2-23%) for comfort
**Zone Name in ALP Integration**: Should match "recessed_ceiling" or configure mapping

---

### Switch 2: kitchen_island

```yaml
adaptive_lighting:
  - name: "kitchen_island"
    lights:
      - light.kitchen_island_pendants

    # Brightness Configuration
    min_brightness: 30
    max_brightness: 100
    sleep_brightness: 1

    # Color Temperature Configuration
    min_color_temp: 2000
    max_color_temp: 4000

    # Timing Configuration
    initial_transition: 0
    transition: 0
    sleep_transition: 3
    interval: 20
    adapt_delay: 0

    # Control Behavior
    autoreset_control_seconds: 0
    take_over_control: true
    detect_non_ha_changes: true
    skip_redundant_commands: true

    # Advanced
    include_config_in_attributes: true
```

**Purpose**: Task lighting for cooking - bright (30-100%) with warm temps (2000-4000K)
**Zone Name in ALP Integration**: Should match "kitchen_island" or configure mapping

---

### Switch 3: bedroom_primary

```yaml
adaptive_lighting:
  - name: "bedroom_primary"
    lights:
      - light.master_bedroom_table_lamps
      - light.master_bedroom_corner_accent

    # Brightness Configuration
    min_brightness: 20
    max_brightness: 40
    sleep_brightness: 5

    # Color Temperature Configuration
    min_color_temp: 1800
    max_color_temp: 2250

    # Timing Configuration
    initial_transition: 0
    transition: 0
    sleep_transition: 5
    interval: 20
    adapt_delay: 0

    # Control Behavior
    autoreset_control_seconds: 0
    take_over_control: true
    skip_redundant_commands: true
    detect_non_ha_changes: true

    # Advanced
    include_config_in_attributes: true
```

**Purpose**: Sleep-friendly bedroom lighting - very dim (20-40%) with extremely warm temps (1800-2250K)
**Zone Name in ALP Integration**: Should match "bedroom_primary" or configure mapping

---

### Switch 4: accent_spots

```yaml
adaptive_lighting:
  - name: "accent_spots"
    lights:
      - light.dining_room_spot_lights
      - light.living_room_spot_lights

    # Brightness Configuration
    min_brightness: 20
    max_brightness: 50
    sleep_brightness: 1

    # Color Temperature Configuration
    min_color_temp: 2000
    max_color_temp: 6500

    # Timing Configuration
    initial_transition: 0
    transition: 0
    sleep_transition: 5
    interval: 20
    adapt_delay: 0

    # Control Behavior
    autoreset_control_seconds: 0
    take_over_control: true
    send_split_delay: 0
    skip_redundant_commands: true
    detect_non_ha_changes: true

    # Advanced
    include_config_in_attributes: true
```

**Purpose**: Decorative accent lighting - moderate brightness (20-50%) with wide color temp range (2000-6500K)
**Zone Name in ALP Integration**: Should match "accent_spots" or configure mapping

---

### Switch 5: main_living

```yaml
adaptive_lighting:
  - name: "main_living"
    lights:
      - light.entryway_lamp
      - light.living_room_floor_lamp
      - light.office_desk_lamp
      - light.living_room_corner_accent
      - light.living_room_couch_lamp
      - light.living_room_credenza_light
      - light.entryway_lamp  # Note: Duplicate in original

    # Brightness Configuration
    min_brightness: 45
    max_brightness: 100
    sleep_brightness: 25

    # Color Temperature Configuration
    min_color_temp: 2250
    max_color_temp: 2950
    sleep_color_temp: 1800

    # Timing Configuration
    initial_transition: 0
    transition: 0
    sleep_transition: 0
    interval: 20
    adapt_delay: 5  # Note: Only switch with adapt_delay > 0

    # Control Behavior
    autoreset_control_seconds: 0
    take_over_control: true
    detect_non_ha_changes: true
    separate_turn_on_commands: false
    send_split_delay: 0
    skip_redundant_commands: true

    # Advanced
    include_config_in_attributes: true
```

**Purpose**: Primary living area lighting - bright (45-100%) with neutral-warm temps (2250-2950K)
**Zone Name in ALP Integration**: Should match "main_living" or configure mapping
**UNIQUE**: Only switch with `adapt_delay: 5` for manual override grace period

---

## Configuration Summary Table

| Switch Name | Lights | Brightness Range | Color Temp Range | adapt_delay | Purpose |
|-------------|--------|------------------|------------------|-------------|---------|
| recessed_ceiling | 2 | 2-23% | Default | 0 | Overhead (very dim) |
| kitchen_island | 1 | 30-100% | 2000-4000K | 0 | Task lighting |
| bedroom_primary | 2 | 20-40% | 1800-2250K | 0 | Sleep-friendly |
| accent_spots | 2 | 20-50% | 2000-6500K | 0 | Decorative |
| main_living | 7* | 45-100% | 2250-2950K | 5 | Primary living |

*Note: main_living has duplicate `light.entryway_lamp` in original config

---

## Common Parameters Across All Switches

All switches share these settings:
```yaml
initial_transition: 0          # Instant on (no fade-in)
transition: 0                  # Instant updates
interval: 20                   # Update every 20 seconds
autoreset_control_seconds: 0   # Never auto-reset manual control
take_over_control: true        # AL takes control on light turn-on
detect_non_ha_changes: true    # Detect external changes (physical switches, etc)
skip_redundant_commands: true  # Don't send duplicate commands
include_config_in_attributes: true  # Include config in switch attributes for debugging
```

---

## Migration Options

### Option 1: UI Configuration (Recommended for Most Users)

**Pros**:
- Survives HA restarts without YAML dependency
- Easy to modify via UI
- No YAML syntax errors

**Cons**:
- Must manually enter each switch via UI
- No version control
- Harder to backup/restore

**Steps**:
1. Go to Settings → Devices & Services
2. Click "+ ADD INTEGRATION"
3. Search "Adaptive Lighting"
4. For each of the 5 switches above, click "ADD ENTRY"
5. Fill in parameters from tables above
6. Verify switch appears as `switch.adaptive_lighting_{name}`

### Option 2: YAML Configuration (Recommended for Power Users)

**Pros**:
- Version controlled
- Easy to backup/restore
- Can copy-paste exact config

**Cons**:
- Requires YAML reload on changes
- Must validate YAML syntax

**Steps**:
1. Add to `configuration.yaml` or create `adaptive_lighting.yaml` package:
   ```yaml
   adaptive_lighting: !include adaptive_lighting.yaml
   ```

2. Create `adaptive_lighting.yaml` with all 5 switch configs above

3. Restart Home Assistant

4. Verify switches appear as `switch.adaptive_lighting_{name}`

### Option 3: Hybrid (Recommended for implementation_2 Migration)

**Best of both worlds**:

1. **For production stability**: Use UI configuration (Option 1)
2. **For documentation**: Keep this file (`AL_SWITCH_CONFIGURATIONS.md`) in repo
3. **For backup**: Export switch configs periodically using Developer Tools → States

---

## Verification Checklist

After configuring all 5 switches, verify:

- [ ] `switch.adaptive_lighting_recessed_ceiling` exists
- [ ] `switch.adaptive_lighting_kitchen_island` exists
- [ ] `switch.adaptive_lighting_bedroom_primary` exists
- [ ] `switch.adaptive_lighting_accent_spots` exists
- [ ] `switch.adaptive_lighting_main_living` exists

For each switch, verify attributes match:
- [ ] `min_brightness` / `max_brightness` correct
- [ ] `min_color_temp` / `max_color_temp` correct (if specified)
- [ ] `lights` list matches
- [ ] `interval: 20` (all switches)
- [ ] `take_over_control: true` (all switches)

---

## ALP Integration Configuration

✅ **COMPLETE CONFIGURATION PROVIDED**: See `adaptive_lighting_pro_zones.yaml` for full zone configs.

The Adaptive Lighting Pro integration MUST be configured to reference these switch names.

**Option 1: Use the provided config file** (Recommended):
```yaml
# In configuration.yaml:
adaptive_lighting_pro: !include adaptive_lighting_pro_zones.yaml
```

**Option 2: Configure via UI**:
Settings → Integrations → Adaptive Lighting Pro → Configure

**Complete zone configuration example** (all 5 zones provided in adaptive_lighting_pro_zones.yaml):

```yaml
adaptive_lighting_pro:
  # Global sensors
  lux_sensor: sensor.outdoor_illuminance
  weather_entity: weather.home

  # Features
  environmental_enabled: true
  sunset_boost_enabled: true
  wake_sequence_enabled: true
  wake_target_zone: bedroom_primary

  zones:
    - zone_id: "recessed_ceiling"
      adaptive_lighting_switch: "switch.adaptive_lighting_recessed_ceiling"
      lights:
        - light.kitchen_main_lights
        - light.living_room_hallway_lights
      brightness_min: 2
      brightness_max: 23
      enabled: true
      environmental_enabled: true
      sunset_enabled: true

    - zone_id: "kitchen_island"
      adaptive_lighting_switch: "switch.adaptive_lighting_kitchen_island"
      lights:
        - light.kitchen_island_pendants
      brightness_min: 30
      brightness_max: 100
      color_temp_min: 2000
      color_temp_max: 4000
      enabled: true
      environmental_enabled: true
      sunset_enabled: true

    # ... (all 5 zones in adaptive_lighting_pro_zones.yaml)
```

**CRITICAL**: Zone brightness/color_temp ranges in ALP integration MUST match the AL switch configurations above, or ALP will send invalid values to AL.

**Verification**: The provided `adaptive_lighting_pro_zones.yaml` has been validated to match all AL switch configs exactly.

---

## Known Issues

### Issue 1: Duplicate light.entryway_lamp in main_living

**Problem**: implementation_1.yaml line 397 duplicates `light.entryway_lamp` (already on line 391)
**Impact**: Minimal - AL handles duplicates gracefully
**Fix**: Remove duplicate when configuring UI or YAML

### Issue 2: adapt_delay Inconsistency

**Problem**: Only `main_living` has `adapt_delay: 5`, all others have `0`
**Reason**: Original implementation added 5s grace period for main living room where user frequently makes manual adjustments
**Recommendation**: Keep this difference - it's intentional UX tuning

---

## Conclusion

**Status**: ✅ **COMPLETE**

implementation_2.yaml NOW includes all Adaptive Lighting switch configurations from implementation_1.yaml.

**What's Provided**:
1. ✅ `implementation_2.yaml` lines 136-240: All 5 AL switch configs
2. ✅ `adaptive_lighting_pro_zones.yaml`: Complete ALP integration zone configs
3. ✅ `AL_SWITCH_CONFIGURATIONS.md`: This documentation file

**Migration Path**:
1. Copy `implementation_2.yaml` to `packages/adaptive_lighting.yaml`
2. Copy `adaptive_lighting_pro_zones.yaml` to your config directory
3. In `configuration.yaml`, add:
   ```yaml
   packages: !include_dir_named packages/
   adaptive_lighting_pro: !include adaptive_lighting_pro_zones.yaml
   ```
4. Restart Home Assistant
5. Verify all switches appear: `switch.adaptive_lighting_*`

**Estimated Time**: 5 minutes to copy files + 1 restart (vs 30-60 min manual config)

**No Manual Configuration Needed** - Everything is in code and version controlled!
