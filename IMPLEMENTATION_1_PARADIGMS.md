# Implementation 1 Critical Paradigms - Complete Architecture Guide

## Overview
This document identifies ALL critical paradigms from implementation_1.yaml that Adaptive Lighting Pro (ALP) must follow or build upon. ALP is NOT a separate system - it's an enhancement layer that works WITH Adaptive Lighting.

---

## PARADIGM 1: Asymmetric Boundary Logic with Aggregation

### Core Principle
All adjustment sources are **aggregated first**, then applied with boundary protection to prevent invalid states (min > max).

### Pattern from implementation_1.yaml
```yaml
variables:
  # Aggregate ALL sources
  final_b_adj: "{{ b_adj + env_boost + sunset_fade + scene_b_offset + wake_offset }}"
  final_k_adj: "{{ k_adj + scene_k_offset }}"

  # Apply with boundary protection
  min_brightness: >
    {% set base_min = 45 %}
    {% set base_max = 100 %}
    {% set boost = final_b_adj if final_b_adj > 0 else 0 %}
    {% set proposed_min = base_min + boost %}
    {{ [1, [proposed_min, base_max] | min] | max }}

  max_brightness: >
    {% set base_min = 45 %}
    {% set base_max = 100 %}
    {% set reduction = final_b_adj if final_b_adj < 0 else 0 %}
    {% set proposed_max = base_max + reduction %}
    {{ [[proposed_max, base_min] | max, 100] | min }}
```

### Key Rules
1. **Positive adjustments** only affect minimum boundary
2. **Negative adjustments** only affect maximum boundary
3. **Never allow min > max** - clamp to base_max when raising min
4. **Never allow max < min** - clamp to base_min when lowering max
5. **Aggregate BEFORE applying** - don't apply each source separately

### ALP Implementation
✅ Coordinator already implements this in `apply_adjustment_to_zone()` (coordinator.py lines 467-597)

---

## PARADIGM 2: Manual-Aware Application Engine

### Core Principle
**ALWAYS check manual_control attribute before applying changes** to prevent fighting with user overrides or scenes.

### Pattern from implementation_1.yaml
```yaml
sequence:
  # CRITICAL: Skip zones with manual control
  - condition: template
    value_template: >
      {% set manual_list = state_attr(repeat.item.entity_id, 'manual_control') | default([]) %}
      {{ not (manual_list is iterable and manual_list is not string and manual_list | length > 0) }}

  # Only reached if manual_control is empty
  - service: adaptive_lighting.change_switch_settings
    target:
      entity_id: "{{ repeat.item.entity_id }}"
    data:
      use_defaults: 'configuration'
      min_brightness: ...
```

### Key Rules
1. Check `manual_control` attribute on AL switch **before** applying changes
2. Skip zones where `manual_control` list has any items
3. This prevents the system from fighting AL's own manual detection
4. Scenes rely on this to remain sticky

### ALP Implementation
⚠️ **NEEDS VERIFICATION** - Check if `_apply_adjustments_to_zone()` verifies manual_control before calling AL services

---

## PARADIGM 3: Sophisticated Environmental Boost Calculation

### Core Principle
Multi-factor environmental boost with logarithmic lux scaling, weather mapping, seasonal adjustments, and time-of-day gating.

### Pattern from implementation_1.yaml
```yaml
variables:
  sophisticated_environmental_boost: >
    {% set lux = states('sensor.living_room_presence_light_sensor_light_level') | float(300) %}
    {% set weather = states('weather.home') %}
    {% set season = 'winter' if now().month in [12,1,2] else 'summer' if now().month in [6,7,8] else 'transition' %}

    {% set base_boost = 0 %}

    {# Logarithmic lux scaling #}
    {% if lux < 10 %}
      {% set base_boost = base_boost + 15 %}
    {% elif lux < 25 %}
      {% set base_boost = base_boost + 10 %}
    {% elif lux < 50 %}
      {% set base_boost = base_boost + 7 %}
    {% elif lux < 100 %}
      {% set base_boost = base_boost + 5 %}
    {% elif lux < 200 %}
      {% set base_boost = base_boost + 3 %}
    {% elif lux < 400 %}
      {% set base_boost = base_boost + 1 %}
    {% endif %}

    {# Weather modifiers with complete mapping #}
    {% set weather_boost = {
      'fog': 20,
      'pouring': 18,
      'hail': 18,
      'snowy': 15,
      'snowy-rainy': 15,
      'rainy': 12,
      'lightning-rainy': 12,
      'cloudy': 10,
      'partlycloudy': 5,
      'windy': 2,
      'windy-variant': 2,
      'lightning': 8,
      'sunny': 0,
      'clear-night': 0,
      'exceptional': 15
    } %}
    {% set base_boost = base_boost + weather_boost.get(weather, 0) %}

    {# Seasonal adjustment #}
    {% if season == 'winter' %}
      {% set base_boost = base_boost + 8 %}
    {% elif season == 'summer' %}
      {% set base_boost = base_boost - 3 %}
    {% endif %}

    {# Time-of-day scaling - DISABLE at night #}
    {% set hour = now().hour %}
    {% if 22 <= hour or hour <= 6 %}
      {% set base_boost = 0 %}  # Disabled 10 PM - 6 AM
    {% elif 6 < hour <= 8 or 18 <= hour < 22 %}
      {% set base_boost = base_boost * 0.7 %}  # Reduced during transitions
    {% endif %}

    {{ [25, base_boost] | min | round(0) }}  # Capped at 25%
```

### Key Rules
1. **Logarithmic lux thresholds**: 10, 25, 50, 100, 200, 400
2. **Weather mapping**: Each condition has specific boost value
3. **Seasonal modifiers**: Winter +8%, Summer -3%
4. **Night disable**: Completely disabled 10 PM - 6 AM
5. **Transition reduce**: 70% effectiveness during dawn/dusk
6. **Maximum cap**: 25% total boost
7. **Boolean flag**: Track when environmental boost is active
8. **Separate reset**: Clear boost when conditions improve

### ALP Implementation
⚠️ **NEEDS ENHANCEMENT** - Current environmental adapter is simpler. Should match this sophistication.

---

## PARADIGM 4: Sunset Fade with Linear Sun Elevation Mapping

### Core Principle
Progressive dimming as sun approaches horizon using linear sun elevation formula.

### Pattern from implementation_1.yaml
```yaml
trigger:
  - platform: time_pattern
    minutes: "/5"  # Check every 5 minutes

condition:
  - condition: template
    value_template: >
      {% set elevation = state_attr('sun.sun', 'elevation') | float(90) %}
      {{ -4 <= elevation <= 4 }}  # Active window

action:
  - variables:
      elevation: "{{ state_attr('sun.sun', 'elevation') | float(0) }}"
      # Linear mapping: 4° = 0%, 0° = -12.5%, -4° = -25%
      offset: "{{ ((4 - elevation) / 8 * -25) | round(0) }}"
  - service: input_number.set_value
    target:
      entity_id: input_number.al_sunset_fade_brightness_offset
    data:
      value: "{{ offset }}"
```

### Key Rules
1. **Active window**: -4° to +4° sun elevation only
2. **Check frequency**: Every 5 minutes
3. **Linear formula**: `((4 - elevation) / 8 * -25)`
   - At +4°: 0% offset (no change)
   - At 0°: -12.5% offset (moderate dim)
   - At -4°: -25% offset (maximum dim)
4. **Separate reset**: Clear offset when outside window
5. **Reset delay**: 2 minutes after leaving window

### ALP Implementation
✅ Coordinator implements this in `_sunset_adapter.calculate_boost()` (features/sunset_boost.py)

---

## PARADIGM 5: Debouncing via input_datetime Timestamps

### Core Principle
Use input_datetime entity to store last action timestamp, preventing duplicate triggers.

### Pattern from implementation_1.yaml
```yaml
variables:
  # Debouncing check
  last_press: "{{ states('input_datetime.zen32_last_button_press') | as_timestamp(0) }}"
  now_timestamp: "{{ now().timestamp() }}"
  time_since_last: "{{ now_timestamp - last_press }}"

condition:
  # Reject if less than 0.5 seconds since last press
  - condition: template
    value_template: "{{ time_since_last > 0.5 }}"

action:
  # Update timestamp BEFORE executing action
  - service: input_datetime.set_datetime
    target:
      entity_id: input_datetime.zen32_last_button_press
    data:
      timestamp: "{{ now_timestamp }}"

  # Continue with actual action...
```

### Key Rules
1. **Store timestamp** in input_datetime entity
2. **Check elapsed time** before processing
3. **Update timestamp** BEFORE action (not after)
4. **Threshold**: 0.5 seconds (configurable)
5. **Reject silently**: Don't log or notify on debounce

### ALP Implementation
✅ Zen32 integration implements debouncing (integrations/zen32.py)

---

## PARADIGM 6: Automation Mode Patterns

### Core Principle
Different automation modes serve different purposes and prevent conflicts.

### Patterns from implementation_1.yaml
```yaml
# For adjustment engines (prevent fighting on rapid changes)
- id: adaptive_lighting_core_engine_v2
  mode: restart  # Cancel previous run, start fresh

# For button presses (drop duplicates silently)
- id: zen32_scene_controller
  mode: single
  max_exceeded: silent

# For timer expiry (process each independently)
- id: adaptive_lighting_timer_expired_main_living
  mode: queued  # Process all events in order
```

### Key Rules
1. **mode: restart** - Adjustment engines that can't fight themselves
2. **mode: single + max_exceeded: silent** - Button handlers
3. **mode: queued** - Timer handlers that must all complete
4. **mode: parallel** - Independent zone operations

### ALP Implementation
✅ Already using appropriate modes

---

## PARADIGM 7: Nuclear Reset Pattern

### Core Principle
Complete system restoration in one comprehensive action.

### Pattern from implementation_1.yaml
```yaml
# Button 3 press = Reset
sequence:
  # Step 1: Reset ALL input_numbers
  - service: input_number.set_value
    target:
      entity_id:
        - input_number.adaptive_lighting_total_brightness_adjustment
        - input_number.adaptive_lighting_total_warmth_adjustment
        - input_number.adaptive_lighting_environmental_brightness_offset
        - input_number.al_sunset_fade_brightness_offset
        - input_number.al_scene_brightness_offset
        - input_number.al_scene_warmth_offset
        - input_number.al_wake_sequence_offset
    data:
      value: 0

  # Step 2: Reset ALL boolean flags
  - service: input_boolean.turn_off
    target:
      entity_id:
        - input_boolean.al_script_brighter_active
        - input_boolean.al_script_dimmer_active
        - input_boolean.al_environmental_boost_active
        # ... etc

  # Step 3: Cancel ALL timers
  - service: timer.cancel
    target:
      entity_id:
        - timer.adaptive_lighting_manual_timer_main_living
        # ... all zones

  # Step 4: Clear manual control from ALL zones
  - service: adaptive_lighting.set_manual_control
    data:
      entity_id:
        - switch.adaptive_lighting_main_living
        # ... all zones
      manual_control: false

  # Step 5: Apply restored settings
  - service: adaptive_lighting.change_switch_settings
    target:
      entity_id: [all zones]
    data:
      use_defaults: 'configuration'

  - service: adaptive_lighting.apply
    target:
      entity_id: [all zones]
    data:
      turn_on_lights: false
      transition: 2
```

### Key Rules
1. **Reset ALL helpers** - leave nothing behind
2. **Cancel ALL timers** - fresh start
3. **Clear ALL manual control** - release all lights
4. **Restore defaults** - use_defaults: 'configuration'
5. **Force apply** - immediate restoration
6. **Use continue_on_error** - robustness over perfection

### ALP Implementation
⚠️ **NEEDS VERIFICATION** - Check if reset_all service does complete nuclear reset

---

## PARADIGM 8: Sonos Wake Sequence Integration

### Core Principle
Modify AL's sunrise_time based on Sonos alarm time to trigger wake sequence.

### Pattern from implementation_1.yaml
```yaml
action:
  - repeat:
      for_each: "{{ al_switches }}"
      sequence:
        # Skip zones with manual control
        - condition: template
          value_template: >
            {% set manual = state_attr(repeat.item, 'manual_control') | default([]) %}
            {{ not (manual is iterable and manual is not string and manual | length > 0) }}

        - service: adaptive_lighting.change_switch_settings
          data:
            entity_id: "{{ repeat.item }}"
            use_defaults: 'configuration'
            sunrise_time: >
              {% set alarm_timestamp = state_attr('sensor.sonos_upcoming_alarms', 'earliest_alarm_timestamp') %}
              {% set natural_sunrise = state_attr('sun.sun', 'next_rising') | as_timestamp(0) %}

              {# Zone-specific offsets #}
              {% if 'recessed_ceiling' in repeat.item %}
                {% set offset_seconds = -2700 %}  # 45 min early
              {% elif 'kitchen_island' in repeat.item %}
                {% set offset_seconds = -2700 %}
              {% elif 'bedroom_primary' in repeat.item %}
                {% set offset_seconds = -1800 %}  # 30 min early
              {% else %}
                {% set offset_seconds = -2700 %}
              {% endif %}

              {% if alarm_timestamp %}
                {{ (alarm_timestamp + offset_seconds) | timestamp_custom('%H:%M:%S') }}
              {% else %}
                {{ natural_sunrise | timestamp_custom('%H:%M:%S') }}
              {% endif %}
```

### Key Rules
1. **Use sensor.sonos_upcoming_alarms** - monitors Sonos alarms
2. **Get earliest_alarm_timestamp** attribute
3. **Zone-specific offsets** - different zones start at different times
4. **Fallback to natural sunrise** - if no alarm set
5. **Skip manual zones** - don't override user control
6. **Disable flag** - input_boolean.al_disable_next_sonos_wakeup
7. **Wake offset aggregated** - with all other adjustments

### ALP Implementation
✅ Sonos integration already implements this pattern (integrations/sonos.py)

---

## PARADIGM 9: Input Helper Structure

### Core Principle
Use input helpers as the single source of truth for all adjustments and state.

### Helper Categories from implementation_1.yaml

#### Configuration Helpers
```yaml
input_number:
  adaptive_lighting_brightness_increment:
    min: 5
    max: 50
    step: 5
    initial: 20
    unit_of_measurement: "%"

  adaptive_lighting_color_temp_increment:
    min: 100
    max: 1000
    step: 50
    initial: 500
    unit_of_measurement: "K"
```

#### Adjustment Tracking
```yaml
input_number:
  adaptive_lighting_total_brightness_adjustment:
    min: -100
    max: 100
    step: 5
    initial: 0

  adaptive_lighting_total_warmth_adjustment:
    min: -2500
    max: 2500
    step: 100
    initial: 0
```

#### Feature-Specific Offsets
```yaml
input_number:
  adaptive_lighting_environmental_brightness_offset:
    min: 0
    max: 50

  al_sunset_fade_brightness_offset:
    min: -50
    max: 0

  al_scene_brightness_offset:
    min: -70
    max: 30

  al_scene_warmth_offset:
    min: -2000
    max: 500

  al_wake_sequence_offset:
    min: -50
    max: 50
```

#### State Flags
```yaml
input_boolean:
  al_script_brighter_active:
  al_script_dimmer_active:
  al_environmental_boost_active:
  al_globally_paused:
  al_disable_next_sonos_wakeup:
```

#### Debouncing
```yaml
input_datetime:
  zen32_last_button_press:
```

#### Mode Selection
```yaml
input_select:
  current_home_mode:
    options:
      - Default
      - Work
      - Late Night
      - Movie

  zen32_lighting_scene:
    options:
      - "Scene 1: All Lights"
      - "Scene 2: No Spotlights"
      - "Scene 3: Evening Comfort"
      - "Scene 4: Ultra Dim"
```

### Key Rules
1. **One helper per concern** - don't overload helpers
2. **Descriptive names** - with al_ or adaptive_lighting_ prefix
3. **Appropriate step values** - match user expectations
4. **Initial values** - sensible defaults
5. **Units** - always specify unit_of_measurement
6. **Range limits** - prevent invalid values
7. **Boolean for flags** - track feature active state
8. **Select for choices** - limited option sets

### ALP Implementation
⚠️ **DIFFERENT ARCHITECTURE** - ALP uses coordinator state instead of input helpers. This is acceptable but means ALP state is not directly exposed to YAML automations.

---

## PARADIGM 10: Timer Expiry Service Call Sequence

### Core Principle
Specific service call pattern when timer expires to restore adaptive control.

### Pattern from implementation_1.yaml
```yaml
trigger:
  - platform: event
    event_type: timer.finished
    event_data:
      entity_id: timer.adaptive_lighting_manual_timer_main_living

action:
  # Step 1: Clear manual control flag
  - service: adaptive_lighting.set_manual_control
    target:
      entity_id: switch.adaptive_lighting_main_living
    data:
      manual_control: false

  # Step 2: Force apply WITH lights parameter
  - service: adaptive_lighting.apply
    data:
      entity_id: switch.adaptive_lighting_main_living
      lights: light.main_living_lights  # CRITICAL: Specify lights for immediate restoration
      transition: 2
      turn_on_lights: false
```

### Key Rules
1. **Trigger on timer.finished event** - not state change
2. **Clear manual_control first** - release the lights
3. **Force apply WITH lights** - immediate restoration (don't wait for AL's cycle)
4. **Transition: 2s** - smooth restoration
5. **turn_on_lights: false** - don't turn on off lights

### ALP Implementation
⚠️ **DIFFERENT PATTERN** - ALP's `_restore_adaptive_control()` calls apply WITHOUT lights parameter. Should this be changed to match implementation_1?

**CRITICAL QUESTION**: Does implementation_1's pattern of specifying `lights` parameter on timer expiry contradict the general rule of NOT specifying lights?

**ANSWER**: This is a SPECIAL CASE. When clearing manual_control after timer expiry, specifying lights forces AL to immediately restore those specific lights instead of waiting for its next update cycle.

---

## PARADIGM 11: Service Call Patterns

### Core Principle
Consistent patterns for calling AL services in different contexts.

### Patterns from implementation_1.yaml

#### Normal Boundary Adjustments
```yaml
# Pattern: change_switch_settings WITHOUT apply
- service: adaptive_lighting.change_switch_settings
  target:
    entity_id: switch.adaptive_lighting_main_living
  data:
    use_defaults: 'configuration'
    min_brightness: 55
    max_brightness: 100
    min_color_temp: 2250
    max_color_temp: 2950

# AL's normal update cycle will apply these changes
```

#### Immediate Application Required
```yaml
# Pattern: change_switch_settings FOLLOWED BY apply
- service: adaptive_lighting.change_switch_settings
  # ... settings ...

- service: adaptive_lighting.apply
  data:
    entity_id: switch.adaptive_lighting_main_living
    turn_on_lights: false  # Don't turn on lights
    transition: 1
    # NO lights parameter - let AL decide based on manual_control
```

#### Timer Expiry Restoration
```yaml
# Pattern: clear manual_control THEN apply WITH lights
- service: adaptive_lighting.set_manual_control
  data:
    entity_id: switch.adaptive_lighting_main_living
    manual_control: false

- service: adaptive_lighting.apply
  data:
    entity_id: switch.adaptive_lighting_main_living
    lights: light.main_living_lights  # Force immediate restoration
    transition: 2
    turn_on_lights: false
```

#### System Reset
```yaml
# Pattern: use_defaults to restore configuration
- service: adaptive_lighting.change_switch_settings
  target:
    entity_id:
      - switch.adaptive_lighting_main_living
      - switch.adaptive_lighting_kitchen_island
  data:
    use_defaults: 'configuration'  # Restore config values
  continue_on_error: true
```

### Key Rules
1. **use_defaults: 'configuration'** - always specify this
2. **turn_on_lights: false** - default, prevents turning on lights
3. **transition: 1-2** - smooth changes, not jarring
4. **continue_on_error: true** - robustness in reset operations
5. **lights parameter**: Only for timer expiry restoration
6. **NO lights parameter**: For normal adjustments (let AL use manual_control)

### ALP Implementation
⚠️ **NEEDS REVIEW** - Verify all AL service calls follow these patterns

---

## PARADIGM 12: Automation Trigger Patterns

### Core Principle
Specific trigger patterns for different automation types.

### Patterns from implementation_1.yaml

#### Adjustment Application
```yaml
trigger:
  - platform: state
    entity_id:
      - input_number.adaptive_lighting_total_brightness_adjustment
      - input_number.adaptive_lighting_total_warmth_adjustment
      # ... all adjustment sources
    for: "00:00:01"  # 1-second debounce

  - platform: time_pattern
    minutes: "/15"  # Periodic reapplication
```

#### Environmental Boost
```yaml
trigger:
  - platform: numeric_state
    entity_id: sensor.living_room_presence_light_sensor_light_level
    below: 400
    for: "00:03:00"  # Require sustained low lux

  - platform: state
    entity_id: weather.home
    to: ['cloudy', 'rainy', 'fog']
    for: "00:05:00"  # Require sustained bad weather
```

#### Sunset Fade
```yaml
trigger:
  - platform: time_pattern
    minutes: "/5"  # Check every 5 minutes during active window
```

#### Button Press
```yaml
trigger:
  - platform: state
    entity_id: event.scene_controller_scene_002
    # Event entities fire on state change (new event)
```

#### Timer Expiry
```yaml
trigger:
  - platform: event
    event_type: timer.finished
    event_data:
      entity_id: timer.adaptive_lighting_manual_timer_main_living
```

### Key Rules
1. **State changes with delay** - prevent rapid fire triggers
2. **1s delay for adjustments** - smooth out slider movements
3. **3-5 minute delays for environmental** - prevent flickering
4. **Time patterns for periodic checks** - maintenance operations
5. **Event triggers for timers** - more reliable than state
6. **Event entities for Z-Wave** - native HA event entities

### ALP Implementation
✅ Coordinator uses 30s refresh cycle which handles periodic application

---

## Critical Differences Between Implementation_1 and ALP

### 1. State Storage
- **Implementation_1**: Uses input helpers (exposed to YAML)
- **ALP**: Uses coordinator state (Python only)
- **Impact**: ALP state not accessible to YAML automations

### 2. Application Trigger
- **Implementation_1**: Automation watches input helpers, applies on change
- **ALP**: Coordinator refresh cycle (30s) applies changes
- **Impact**: ALP already handles immediate apply via `_apply_all_zones_immediate()`

### 3. Manual Control Detection
- **Implementation_1**: Checks manual_control before each apply
- **ALP**: Should verify this pattern is followed

### 4. Timer Expiry
- **Implementation_1**: Calls apply WITH lights parameter
- **ALP**: Calls apply WITHOUT lights parameter
- **Question**: Should ALP match implementation_1 pattern?

---

## Action Items for ALP

### CRITICAL (Fix Immediately)
1. ✅ **DONE**: Expand groups to individual lights for manual_control
2. ✅ **DONE**: Separate timer expiry logic (adjustments vs manual_control)
3. ⚠️ **VERIFY**: Check manual_control before applying adjustments
4. ⚠️ **REVIEW**: Timer expiry apply - should it specify lights parameter?

### HIGH PRIORITY (Enhance Soon)
1. ⚠️ **ENHANCE**: Environmental boost calculation (match sophistication)
2. ⚠️ **VERIFY**: Service call patterns (use_defaults, turn_on_lights, transition)
3. ⚠️ **TEST**: Nuclear reset completeness

### MEDIUM PRIORITY (Future Improvements)
1. Consider exposing coordinator state to input helpers for YAML interoperability
2. Add template sensors to expose current adjustments
3. Document architectural differences in user docs

---

## Summary

Implementation_1.yaml demonstrates 12 critical paradigms:

1. **Asymmetric Boundary Logic** - Aggregate then apply with protection
2. **Manual-Aware Application** - Check manual_control before applying
3. **Sophisticated Environmental** - Multi-factor with time gating
4. **Sunset Fade** - Linear sun elevation mapping
5. **Debouncing** - input_datetime timestamp comparison
6. **Automation Modes** - restart/single/queued appropriately
7. **Nuclear Reset** - Comprehensive system restoration
8. **Sonos Wake Integration** - sunrise_time modification
9. **Input Helper Structure** - Single source of truth
10. **Timer Expiry Pattern** - Specific service call sequence
11. **Service Call Patterns** - Consistent AL service usage
12. **Trigger Patterns** - Appropriate for each automation type

ALP already implements most patterns correctly. Key areas needing attention:
- Manual control checking before applying
- Timer expiry apply pattern (lights parameter)
- Environmental boost sophistication
- Service call consistency