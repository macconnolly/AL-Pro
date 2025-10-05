# Adaptive Lighting Pro - Testing Dashboard (UI EDITOR Format)

**IMPORTANT: This is UI EDITOR format, NOT dashboard.yaml format**

These cards are designed to be pasted DIRECTLY into the Home Assistant UI Dashboard Editor.

## How to Use

1. Navigate to your Home Assistant dashboard
2. Click the three dots (⋮) in the top right → **Edit Dashboard**
3. Click **+ ADD CARD** button at the bottom
4. Switch to **YAML** mode (button in bottom left)
5. **Delete** the placeholder YAML
6. **Copy and paste** one of the card YAML blocks below
7. Click **SAVE**

**DO NOT** wrap these cards in `views:` or any other structure. They are standalone card definitions.

---

## Card 1: System Status Overview

**Purpose:** At-a-glance health check and core metrics

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # Adaptive Lighting Pro - System Status

      Real-time monitoring of integration health and core metrics.

  - type: entities
    title: System Health
    entities:
      - entity: sensor.alp_system_health
        name: Overall Health
        icon: mdi:heart-pulse

      - entity: sensor.alp_status
        name: Current State
        icon: mdi:information-outline

      - type: attribute
        entity: sensor.alp_status
        attribute: current_scene
        name: Active Scene
        icon: mdi:palette

      - type: attribute
        entity: sensor.alp_status
        attribute: global_paused
        name: System Paused
        icon: mdi:pause-circle

      - type: divider

      - entity: sensor.alp_brightness_adjustment
        name: Brightness Adjustment
        icon: mdi:brightness-6

      - entity: sensor.alp_warmth_adjustment
        name: Warmth Adjustment
        icon: mdi:thermometer

      - type: divider

      - entity: sensor.alp_environmental_boost
        name: Environmental Boost
        icon: mdi:weather-cloudy

      - entity: sensor.alp_sunset_boost
        name: Sunset Boost
        icon: mdi:weather-sunset-down

    state_color: true
```

---

## Card 2: Quick Controls

**Purpose:** Instant access to brightness/warmth adjustments and scene selection

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # Quick Controls

      Adjust brightness and warmth with one tap.

  - type: horizontal-stack
    cards:
      - type: button
        entity: button.alp_brighter
        name: Brighter
        icon: mdi:brightness-5
        tap_action:
          action: call-service
          service: button.press
          service_data:
            entity_id: button.alp_brighter
        hold_action:
          action: none

      - type: button
        entity: button.alp_dimmer
        name: Dimmer
        icon: mdi:brightness-4
        tap_action:
          action: call-service
          service: button.press
          service_data:
            entity_id: button.alp_dimmer

  - type: horizontal-stack
    cards:
      - type: button
        entity: button.alp_warmer
        name: Warmer
        icon: mdi:thermometer-chevron-up
        tap_action:
          action: call-service
          service: button.press
          service_data:
            entity_id: button.alp_warmer

      - type: button
        entity: button.alp_cooler
        name: Cooler
        icon: mdi:thermometer-chevron-down
        tap_action:
          action: call-service
          service: button.press
          service_data:
            entity_id: button.alp_cooler

  - type: entities
    entities:
      - entity: button.alp_reset
        name: Reset All Adjustments
        icon: mdi:restore
        tap_action:
          action: call-service
          service: button.press
          service_data:
            entity_id: button.alp_reset
```

---

## Card 3: Scene Selector

**Purpose:** Switch between lighting scenes with scene buttons

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # Scene Selection

      Apply lighting scenes with one tap. Integration handles offsets, YAML scripts handle light choreography.

  - type: entities
    title: Active Scene
    entities:
      - entity: select.alp_scene
        name: Current Scene
        icon: mdi:palette-outline

  - type: grid
    square: false
    columns: 2
    cards:
      - type: button
        entity: button.alp_scene_all_lights
        name: All Lights
        icon: mdi:lightbulb-group
        tap_action:
          action: call-service
          service: button.press
          service_data:
            entity_id: button.alp_scene_all_lights
        show_state: false

      - type: button
        entity: button.alp_scene_no_spotlights
        name: No Spotlights
        icon: mdi:lightbulb-off-outline
        tap_action:
          action: call-service
          service: button.press
          service_data:
            entity_id: button.alp_scene_no_spotlights
        show_state: false

      - type: button
        entity: button.alp_scene_evening_comfort
        name: Evening Comfort
        icon: mdi:weather-sunset
        tap_action:
          action: call-service
          service: button.press
          service_data:
            entity_id: button.alp_scene_evening_comfort
        show_state: false

      - type: button
        entity: button.alp_scene_ultra_dim
        name: Ultra Dim
        icon: mdi:weather-night
        tap_action:
          action: call-service
          service: button.press
          service_data:
            entity_id: button.alp_scene_ultra_dim
        show_state: false
```

---

## Card 4: Manual Control Monitoring

**Purpose:** Track which zones are under manual control and timers

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # Manual Control Tracker

      Displays which zones have manual control active and their timer states.

  - type: entities
    title: Manual Control Summary
    entities:
      - entity: sensor.alp_total_manual_control
        name: Total Zones Under Manual Control
        icon: mdi:hand-back-right

      - entity: sensor.alp_zones_with_manual_control
        name: Zones List
        icon: mdi:format-list-bulleted

  - type: entities
    title: Zone-Specific Manual Control
    entities:
      - entity: sensor.alp_manual_control_main_living
        name: Main Living
        icon: mdi:sofa

      - entity: sensor.alp_manual_control_kitchen_island
        name: Kitchen Island
        icon: mdi:silverware-fork-knife

      - entity: sensor.alp_manual_control_bedroom_primary
        name: Bedroom Primary
        icon: mdi:bed

      - entity: sensor.alp_manual_control_recessed_ceiling
        name: Recessed Ceiling
        icon: mdi:ceiling-light

      - entity: sensor.alp_manual_control_accent_spots
        name: Accent Spots
        icon: mdi:spotlight-beam

    state_color: true
```

---

## Card 5: Real-Time Monitor (Debug)

**Purpose:** Live view of coordinator update cycle and calculations

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # Real-Time Monitor (Debug)

      Shows coordinator update cycle details and calculation results.

  - type: entity
    entity: sensor.alp_realtime_monitor
    name: Coordinator Monitor
    attribute: last_update

  - type: markdown
    content: |
      ### Recent Activity

      ```
      {{ state_attr('sensor.alp_realtime_monitor', 'recent_events') | join('\n') }}
      ```

  - type: entities
    title: Coordinator Stats
    entities:
      - type: attribute
        entity: sensor.alp_realtime_monitor
        attribute: update_count
        name: Total Updates
        icon: mdi:counter

      - type: attribute
        entity: sensor.alp_realtime_monitor
        attribute: last_update
        name: Last Update
        icon: mdi:clock-outline

      - type: attribute
        entity: sensor.alp_realtime_monitor
        attribute: zones_updated
        name: Zones Updated
        icon: mdi:home-group
```

---

## Card 6: Configuration Controls

**Purpose:** Adjust integration settings (increments, timeouts, etc.)

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # Configuration Settings

      Adjust integration behavior and parameters.

  - type: entities
    title: Adjustment Increments
    entities:
      - entity: number.alp_brightness_increment
        name: Brightness Step
        icon: mdi:plus-minus

      - entity: number.alp_color_temp_increment
        name: Color Temp Step
        icon: mdi:plus-minus

  - type: entities
    title: Manual Control Timeout
    entities:
      - entity: number.alp_manual_timeout
        name: Timeout (minutes)
        icon: mdi:timer-outline

  - type: entities
    title: Wake Sequence
    entities:
      - entity: sensor.alp_next_alarm
        name: Next Alarm
        icon: mdi:alarm

      - entity: sensor.alp_wake_sequence_offset
        name: Wake Offset
        icon: mdi:clock-start
```

---

## Card 7: Environmental & Sunset Boost Details

**Purpose:** Deep dive into boost calculations and conditions

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # Boost Calculations

      Detailed view of environmental and sunset boost logic.

  - type: entities
    title: Environmental Boost
    entities:
      - entity: sensor.alp_environmental_boost
        name: Current Boost
        icon: mdi:weather-cloudy

      - type: attribute
        entity: sensor.alp_environmental_boost
        attribute: lux_value
        name: Lux Reading
        icon: mdi:brightness-5

      - type: attribute
        entity: sensor.alp_environmental_boost
        attribute: weather_condition
        name: Weather
        icon: mdi:weather-partly-cloudy

      - type: attribute
        entity: sensor.alp_environmental_boost
        attribute: calculation_reason
        name: Boost Reason
        icon: mdi:information

  - type: entities
    title: Sunset Boost
    entities:
      - entity: sensor.alp_sunset_boost
        name: Current Boost
        icon: mdi:weather-sunset-down

      - type: attribute
        entity: sensor.alp_sunset_boost
        attribute: sun_elevation
        name: Sun Elevation
        icon: mdi:weather-sunset

      - type: attribute
        entity: sensor.alp_sunset_boost
        attribute: active_window
        name: Active Window
        icon: mdi:clock-time-eight

      - type: attribute
        entity: sensor.alp_sunset_boost
        attribute: lux_threshold_met
        name: Lux Threshold Met
        icon: mdi:check-circle

    state_color: true
```

---

## Card 8: System Health Diagnostic

**Purpose:** Complete diagnostic view for troubleshooting

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # System Diagnostics

      Complete health check and troubleshooting information.

  - type: entity
    entity: sensor.alp_system_health
    name: Overall System Health
    icon: mdi:stethoscope

  - type: markdown
    content: |
      ### Health Attributes

      **AL Switches Status:**
      ```
      {{ state_attr('sensor.alp_system_health', 'al_switches_status') }}
      ```

      **Coordinator Status:**
      ```
      {{ state_attr('sensor.alp_system_health', 'coordinator_status') }}
      ```

      **Issues Detected:**
      ```
      {{ state_attr('sensor.alp_system_health', 'issues') | join(', ') if state_attr('sensor.alp_system_health', 'issues') else 'None' }}
      ```

  - type: entities
    title: Deviation Tracker
    entities:
      - entity: sensor.alp_deviation_tracker
        name: Deviation Summary
        icon: mdi:chart-line-variant

      - type: attribute
        entity: sensor.alp_deviation_tracker
        attribute: total_deviations
        name: Total Deviations
        icon: mdi:counter

      - type: attribute
        entity: sensor.alp_deviation_tracker
        attribute: zones_with_deviations
        name: Zones With Deviations
        icon: mdi:home-alert

  - type: entities
    title: Integration Info
    entities:
      - type: attribute
        entity: sensor.alp_status
        attribute: version
        name: Integration Version
        icon: mdi:tag

      - type: attribute
        entity: sensor.alp_status
        attribute: coordinator_update_interval
        name: Update Interval
        icon: mdi:timer-sand
```

---

## Testing Checklist

After adding all cards to your dashboard, verify:

- [ ] **Card 1 (System Status)** - Shows health as "Excellent" or "Good"
- [ ] **Card 2 (Quick Controls)** - Buttons respond instantly, adjustments apply
- [ ] **Card 3 (Scene Selector)** - Scenes apply light choreography correctly
- [ ] **Card 4 (Manual Control)** - Zones show manual control when lights touched
- [ ] **Card 5 (Real-Time Monitor)** - Updates every 30 seconds
- [ ] **Card 6 (Configuration)** - Number entities accept value changes
- [ ] **Card 7 (Boost Details)** - Environmental/sunset boost calculates correctly
- [ ] **Card 8 (Diagnostics)** - No issues detected, all switches online

---

## Troubleshooting

### Issue: Entities show "Entity not available"

**Cause:** Integration not loaded or config flow not completed

**Fix:**
1. Go to Configuration → Integrations
2. Find "Adaptive Lighting Pro"
3. If not present, add it via "Add Integration" button
4. Complete config flow with required sensors

### Issue: Buttons don't respond

**Cause:** Coordinator not running or service not registered

**Fix:**
1. Check Developer Tools → Services → Filter "adaptive_lighting_pro"
2. Should see 10 services listed
3. If not, restart Home Assistant
4. Check logs for errors: Settings → System → Logs → "adaptive_lighting_pro"

### Issue: Scene buttons don't apply light choreography

**Cause:** implementation_2.yaml scripts not loaded

**Fix:**
1. Verify implementation_2.yaml in /config/packages/ directory
2. Check Configuration → Server Controls → Check Configuration
3. Should show "Configuration valid"
4. Restart Home Assistant
5. Check Developer Tools → Services → Filter "apply_scene"

### Issue: Manual control sensors always show "Inactive"

**Cause:** Manual control detection not working

**Fix:**
1. Verify Adaptive Lighting (base) integration installed
2. Check that AL switches exist: `switch.adaptive_lighting_*`
3. Verify AL switches have `manual_control` attribute
4. Try physically changing a light and check if attribute updates
5. Check coordinator logs for manual control detection messages

---

## Advanced: Customizing Cards

All cards use standard Lovelace card types:
- `vertical-stack` - Stack cards vertically
- `horizontal-stack` - Stack cards horizontally
- `entities` - List of entities with controls
- `button` - Clickable button card
- `markdown` - Rich text content
- `grid` - Grid layout for buttons

**Customization Examples:**

### Change Card Colors

Add `card_mod` theme styling (requires card-mod custom card):

```yaml
card_mod:
  style: |
    ha-card {
      background-color: rgba(0, 100, 200, 0.1);
      border: 1px solid rgba(0, 100, 200, 0.3);
    }
```

### Add Icons to Markdown Headers

Replace markdown content:

```yaml
type: markdown
content: |
  # 💡 Adaptive Lighting Pro - System Status
```

### Reorder Entities

Simply move entity definitions up/down in the `entities:` list.

### Remove Unwanted Cards

Skip pasting cards you don't need. Each card is standalone.

---

## Dashboard Layout Recommendations

**Minimal Layout (Mobile-Friendly):**
- Card 1 (System Status)
- Card 2 (Quick Controls)
- Card 3 (Scene Selector)

**Standard Layout (Desktop):**
- Card 1 (System Status)
- Card 2 (Quick Controls)
- Card 3 (Scene Selector)
- Card 4 (Manual Control)
- Card 8 (Diagnostics)

**Power User Layout (All Cards):**
- All 8 cards for complete visibility

**Testing/Debug Layout:**
- Card 5 (Real-Time Monitor)
- Card 7 (Boost Details)
- Card 8 (Diagnostics)

---

## Integration with Voice Assistants

The voice control scripts in implementation_2.yaml can be exposed to Alexa/Google:

1. Go to Configuration → Alexa/Google Assistant
2. Enable "Expose" for these scripts:
   - `script.voice_all_lights`
   - `script.voice_evening_mode`
   - `script.voice_night_mode`
   - `script.voice_brighter`
   - `script.voice_dimmer`
   - `script.voice_warmer`
   - `script.voice_cooler`
   - `script.voice_reset_lights`
3. Say "Alexa, discover devices" or sync Google Home app
4. Voice commands will now work:
   - "Alexa, turn on all the lights"
   - "Alexa, turn on evening mode"
   - "Alexa, make it brighter"

---

## Performance Notes

- Cards update automatically when entity states change
- No polling required - event-driven updates from integration
- Coordinator updates every 30 seconds (configurable)
- Button presses are instant (<100ms response time)
- Scene application triggers YAML scripts (1-2 second execution)

---

## See Also

- [YAML_MIGRATION_COMPLETE.md](YAML_MIGRATION_COMPLETE.md) - Comprehensive migration guide
- [implementation_2.yaml](implementation_2.yaml) - User configuration YAML
- [TODO.md](TODO.md) - Project status and known issues
- [claude.md](claude.md) - Architectural principles and quality standards

---

**Last Updated:** 2025-10-05
**Integration Version:** Adaptive Lighting Pro (Python)
**Format:** UI EDITOR (NOT dashboard.yaml)
