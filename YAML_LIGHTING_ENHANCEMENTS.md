# YAML-Based Lighting System Enhancement Proposals

## Executive Summary

The current implementation (v7.yaml + implementation_2.yaml) provides a robust event-driven lighting system with 5 zones, environmental adaptation, and scene management. This document proposes 12 enhancement categories to improve flexibility, user experience, and maintainability.

---

## 1. **User-Definable Scene Library via YAML**

### Current State
- Scenes hardcoded in Python (`DEFAULT_SCENE_PRESETS`)
- Limited to 5 presets: default, all_lights, no_spots, evening_comfort, ultra_dim

### Enhancement
Enable custom scene definitions in YAML with rich metadata:

```yaml
adaptive_lighting_pro:
  custom_scenes:
    # Work from Home Scene
    - id: "wfh_focus"
      name: "Work Focus"
      icon: "mdi:briefcase"
      priority: high  # Prevents accidental override
      settings:
        brightness_pct: 85
        color_temp_kelvin: 4500  # Cool white for alertness
        transition_sec: 5
      zone_overrides:
        kitchen_island:
          brightness_pct: 100  # Brighter task lighting
        bedroom_primary:
          action: "off"  # Minimize distractions
      environmental:
        disable_auto_boost: true  # Maintain consistent work lighting
      schedule:
        auto_activate:
          - weekday: ["mon", "tue", "wed", "thu", "fri"]
            time: "09:00:00"
        auto_deactivate:
          - time: "17:00:00"

    # Dinner Party Scene
    - id: "dinner_party"
      name: "Dinner Party"
      icon: "mdi:candelabra"
      settings:
        brightness_pct: 65
        color_temp_kelvin: 2700
        transition_sec: 30  # Gradual, elegant transitions
      zone_overrides:
        kitchen_island:
          brightness_pct: 80  # Functional but not harsh
        accent_spots:
          brightness_pct: 50
          color_temp_kelvin: 2500  # Warm accent
      conditions:
        require_all:
          - state: "input_boolean.guests_present"
            value: "on"
      manual_timeout_multiplier: 2.5  # Longer manual control during parties
```

### Benefits
- User customization without code changes
- Scheduled scene activation
- Conditional logic for context-aware lighting
- Zone-level granularity

---

## 2. **Transition Profiles & Animation Library**

### Current State
- Single transition duration per operation
- Linear transitions only

### Enhancement
Define reusable transition profiles:

```yaml
adaptive_lighting_pro:
  transition_profiles:
    gentle_wake:
      type: "ease_in_sine"
      duration_sec: 300  # 5 minutes
      steps: 60  # Smooth incremental changes
      start_brightness_pct: 1

    instant:
      duration_sec: 0

    cinematic:
      type: "ease_out_cubic"
      duration_sec: 10
      color_temp_first: true  # Shift warmth before dimming

    circadian_adaptive:
      type: "dynamic"  # Uses sun position to vary speed
      duration_range: [30, 120]
      faster_during: ["sunrise", "sunset"]  # Match natural light changes

  # Apply profiles to scenes
  scene_transitions:
    wfh_focus: "instant"
    dinner_party: "cinematic"
    default: "circadian_adaptive"

  # Apply profiles to events
  event_transitions:
    manual_restore: "gentle_wake"
    zone_enable: "circadian_adaptive"
    emergency_override: "instant"
```

### Benefits
- Natural, biological lighting transitions
- Context-appropriate animation speeds
- Reduced jarring changes during sensitive times

---

## 3. **Time-of-Day & Occupancy-Based Defaults**

### Current State
- Static zone defaults (min/max brightness, color temp)
- No occupancy awareness in YAML config

### Enhancement
Dynamic defaults based on context:

```yaml
homeassistant:
  customize:
    switch.adaptive_lighting_main_living:
      # ... existing config ...
      contextual_defaults:
        - conditions:
            time_after: "22:00:00"
            time_before: "06:00:00"
          defaults:
            max_brightness: 30  # Night mode caps
            min_color_temp: 2200
            max_color_temp: 2500
            transition_sec: 15  # Slower at night

        - conditions:
            state: "binary_sensor.main_living_occupancy"
            value: "off"
            duration_min: 10  # Unoccupied for 10+ min
          defaults:
            action: "dim_standby"
            standby_brightness: 10
            restore_on_motion: true

        - conditions:
            state: "sensor.home_mode"
            value: "guest"
          defaults:
            disable_auto_adjust: true  # Let guests control manually
            manual_timeout_multiplier: 5.0

        - conditions:
            state: "sensor.outdoor_lux"
            below: 100
            state: "cover.main_living_blinds"
            value: "open"
          defaults:
            environmental_boost_factor: 1.5  # Compensate for glare
```

### Benefits
- Automatic behavior adaptation
- Reduced manual intervention
- Energy savings through occupancy awareness
- Guest-friendly manual control retention

---

## 4. **Circadian Rhythm Presets**

### Current State
- Fixed color temp ranges
- No biological rhythm optimization

### Enhancement
Science-based circadian templates:

```yaml
adaptive_lighting_pro:
  circadian_profiles:
    standard_adult:
      phase_shift_min: 0  # No jet lag compensation
      melanopic_optimization: true
      stages:
        - name: "Wake"
          sun_elevation_range: [-6, 0]  # Civil twilight
          brightness_curve: "exponential_rise"
          color_temp_range: [3500, 5500]
          blue_light_boost: 1.2  # Suppress melatonin

        - name: "Morning Peak"
          sun_elevation_range: [0, 30]
          brightness_curve: "plateau"
          color_temp_range: [5000, 6500]

        - name: "Afternoon"
          sun_elevation_range: [30, 15]
          brightness_curve: "linear_decline"
          color_temp_range: [4500, 3500]

        - name: "Evening Wind-Down"
          sun_elevation_range: [15, -6]
          brightness_curve: "exponential_decay"
          color_temp_range: [3000, 2200]
          blue_light_reduction: 0.7  # Reduce 480nm wavelengths

        - name: "Night"
          sun_elevation_range: [-6, -90]
          brightness_max: 15
          color_temp_range: [2000, 2200]
          red_shift_mode: true  # Preserve night vision

    shift_worker:
      phase_shift_min: 480  # 8-hour shift
      # ... custom schedule ...

    new_parent:
      night_mode_start: "19:00"
      night_mode_end: "07:00"
      allow_overrides: false  # Strict night mode
      motion_triggers:
        - sensor: "binary_sensor.nursery_motion"
          response: "ultra_dim"
          hold_time_min: 30

  zone_circadian_assignments:
    main_living: "standard_adult"
    bedroom_primary: "new_parent"
    kitchen_island: "standard_adult"
```

### Benefits
- Healthier lighting aligned with human biology
- Better sleep hygiene
- Supports shift workers and special needs
- Reduces eye strain

---

## 5. **Advanced Conditional Logic Engine**

### Current State
- Limited condition checking in automations
- Complex logic requires multiple automations

### Enhancement
Declarative condition system:

```yaml
adaptive_lighting_pro:
  rules:
    - id: "movie_night_auto"
      name: "Automatic Movie Mode"
      conditions:
        operator: "and"
        checks:
          - type: "state"
            entity: "media_player.living_room_tv"
            state: "playing"
          - type: "time"
            after: "18:00"
          - type: "state"
            entity: "sensor.al_current_mode"
            not_state: "movie"
          - operator: "or"
            checks:
              - type: "state"
                entity: "binary_sensor.weekend"
                state: "on"
              - type: "time"
                after: "20:00"
      actions:
        - service: "adaptive_lighting_pro.select_mode"
          data:
            mode: "movie"
        - service: "adaptive_lighting_pro.select_scene"
          data:
            scene: "ultra_dim"
      reset_on:
        - state: "media_player.living_room_tv"
          state: "idle"
          duration_min: 5

    - id: "bright_cooking"
      name: "Cooking Boost"
      conditions:
        - type: "state"
          entity: "binary_sensor.stove_active"
          state: "on"
      actions:
        - service: "adaptive_lighting_pro.adjust"
          target:
            zone_id: "kitchen_island"
          data:
            brightness_offset: 20
            color_temp_kelvin: 4000
      priority: high  # Overrides other rules
```

### Benefits
- Eliminate complex automation YAML
- Centralized rule management
- Priority-based conflict resolution
- Easier debugging

---

## 6. **Per-Light Capability Mapping**

### Current State
- Assumes all lights support brightness + color temp
- No feature detection

### Enhancement
Explicit capability definitions:

```yaml
adaptive_lighting_pro:
  light_capabilities:
    # RGBWW smart bulbs
    - lights:
        - light.entryway_lamp
        - light.reading_nook_floor
      features:
        brightness: true
        color_temp: true
        rgb_color: true
        effects: ["colorloop", "random"]
      limits:
        min_mireds: 153  # 6500K
        max_mireds: 500  # 2000K
        min_brightness: 1
        max_brightness: 255
      adaptive_strategy: "color_temp_preferred"

    # Dumb bulbs on smart switches
    - lights:
        - light.recessed_ceiling_1
        - light.recessed_ceiling_2
      features:
        brightness: false
        color_temp: false
      adaptive_strategy: "on_off_only"
      on_threshold_lux: 200  # Turn on when < 200 lux

    # Tunable white strips
    - lights:
        - light.under_cabinet_strip
      features:
        brightness: true
        color_temp: true
        rgb_color: false
      limits:
        min_mireds: 250  # 4000K
        max_mireds: 454  # 2200K
      power_limit_watts: 20
      adaptive_strategy: "color_temp_primary"
```

### Benefits
- Graceful degradation for limited lights
- Prevents service call errors
- Optimizes API calls
- Power usage tracking

---

## 7. **Event Logging & Audit Trail**

### Current State
- Basic telemetry counters
- No event replay capability

### Enhancement
Comprehensive event history in YAML:

```yaml
adaptive_lighting_pro:
  audit_config:
    enabled: true
    retention_days: 30
    storage_path: "/config/adaptive_lighting_pro/audit/"
    format: "jsonl"  # JSON Lines for efficient appends

    tracked_events:
      - type: "manual_override"
        log_level: "info"
        include_light_states: true

      - type: "scene_activation"
        log_level: "info"
        include_trigger_source: true

      - type: "adaptive_sync"
        log_level: "debug"
        sample_rate: 0.1  # Log 10% to reduce volume

      - type: "error"
        log_level: "error"
        include_stack_trace: true
        notify: "persistent_notification"

    analytics:
      daily_summary: true
      summary_time: "23:55"
      metrics:
        - "manual_override_count_by_zone"
        - "average_brightness_by_hour"
        - "scene_usage_distribution"
        - "environmental_boost_activation_rate"
```

### Example Audit Entry
```json
{"timestamp": "2025-11-15T19:45:23.123Z", "event": "manual_override", "zone": "main_living", "light": "light.entryway_lamp", "old_state": {"brightness": 180, "color_temp": 370}, "new_state": {"brightness": 80}, "trigger": "wall_switch", "mode": "adaptive", "timer_started": 60, "timer_multipliers": {"mode": 1.0, "zone": 1.0, "env": 0.8}}
```

### Benefits
- Debugging complex behaviors
- User behavior insights
- Performance analysis
- Compliance/security auditing

---

## 8. **Backup & Restore System**

### Current State
- `backup_prefs`/`restore_prefs` services exist
- No YAML-based snapshot management

### Enhancement
Declarative snapshot system:

```yaml
adaptive_lighting_pro:
  snapshots:
    auto_backup:
      enabled: true
      schedule: "daily"
      time: "03:00:00"
      retention_count: 7
      include:
        - "zone_configs"
        - "scene_settings"
        - "mode_preferences"
        - "manual_timers"
        - "environmental_sensors"

    named_snapshots:
      - name: "pre_holiday_lights"
        trigger:
          state: "input_boolean.holiday_mode"
          from: "off"
          to: "on"
        auto_restore_on:
          state: "input_boolean.holiday_mode"
          from: "on"
          to: "off"

      - name: "guest_arrival"
        manual: true
        notify_on_creation: true

    restore_strategy:
      on_startup: "last_known_good"
      on_error: "safe_defaults"
      preserve_manual_overrides: true
```

### Benefits
- Easy experimentation
- Disaster recovery
- Seasonal configuration swaps
- Migration safety

---

## 9. **Multi-Home & Profile Support**

### Current State
- Single configuration per instance
- No user-specific preferences

### Enhancement
Per-user and per-location profiles:

```yaml
adaptive_lighting_pro:
  profiles:
    - name: "Alex"
      preferred_mode: "focus"
      manual_timeout_multiplier: 0.8  # Shorter overrides
      zones:
        bedroom_primary:
          night_brightness_max: 5  # Very sensitive to light
        kitchen_island:
          morning_brightness_boost: 15
      circadian_profile: "shift_worker"

    - name: "Jordan"
      preferred_mode: "relax"
      manual_timeout_multiplier: 1.5
      zones:
        bedroom_primary:
          night_brightness_max: 20
      circadian_profile: "standard_adult"

  profile_detection:
    method: "person_home"
    mappings:
      - person: "person.alex"
        profile: "Alex"
      - person: "person.jordan"
        profile: "Jordan"
    conflict_resolution: "merge_conservative"  # Use lowest brightness when both home

  locations:
    - name: "Main Home"
      config_file: "v7.yaml"

    - name: "Vacation Cabin"
      config_file: "cabin_lighting.yaml"
      sync_scenes: true  # Copy custom scenes between locations
      active_when:
        state: "input_select.current_location"
        value: "Cabin"
```

### Benefits
- Personalized experiences
- Multi-residence support
- Reduced conflicts between household members
- WAF (Wife Acceptance Factor) improvement

---

## 10. **Integration Webhooks & External Control**

### Current State
- Services callable from HA only
- No external API

### Enhancement
YAML-defined webhook endpoints:

```yaml
adaptive_lighting_pro:
  webhooks:
    - id: "alexa_scene_trigger"
      url_path: "/api/alp/alexa/scene"
      method: "POST"
      authentication: "bearer_token"
      allowed_actions:
        - "select_scene"
        - "select_mode"
      rate_limit:
        requests: 30
        period_sec: 60
      payload_mapping:
        scene: "$.directive.payload.scene_name"

    - id: "lutron_keypad"
      url_path: "/api/alp/lutron/button"
      method: "POST"
      authentication: "api_key"
      allowed_actions:
        - "select_scene"
        - "adjust"
      payload_mapping:
        button_id: "$.button"
      button_scene_map:
        1: "all_lights"
        2: "evening_comfort"
        3: "ultra_dim"
        4: "default"

    - id: "dashboard_status"
      url_path: "/api/alp/status"
      method: "GET"
      authentication: "none"
      rate_limit:
        requests: 60
        period_sec: 60
      response:
        format: "json"
        include:
          - "active_zones"
          - "current_mode"
          - "active_scene"
          - "manual_timers"
```

### Benefits
- Voice assistant integration
- Third-party controller support
- External dashboard creation
- Home automation platform bridges

---

## 11. **YAML Schema Validation & Linting**

### Current State
- No validation until runtime
- Errors discovered during use

### Enhancement
Pre-deployment validation:

```yaml
# .adaptive_lighting_pro_schema.yaml
schema_version: "1.0"

validation_rules:
  zones:
    required_fields: ["zone_id", "al_switch", "lights"]
    zone_id_pattern: "^[a-z][a-z0-9_]*$"
    max_zones: 20

  scenes:
    max_custom_scenes: 50
    brightness_range: [0, 100]
    color_temp_range: [1000, 10000]
    transition_max_sec: 3600

  automations:
    max_per_zone: 10
    require_unique_ids: true
    warn_on_missing_entities: true

  performance:
    max_lights_per_zone: 30
    warn_script_execution_time_ms: 500

  security:
    forbid_shell_commands: true
    require_https_webhooks: true

# CLI tool integration
# hass --config /config --script alp_validate --file v7.yaml
```

### Benefits
- Catch errors before deployment
- IDE autocomplete support (via JSON Schema export)
- Documentation generation
- CI/CD integration

---

## 12. **Performance Optimization Directives**

### Current State
- All events processed immediately
- No batching or throttling config

### Enhancement
YAML-based performance tuning:

```yaml
adaptive_lighting_pro:
  performance:
    batching:
      enabled: true
      max_batch_size: 10
      max_wait_ms: 100
      events:
        - "adaptive_sync"
        - "environmental_update"

    throttling:
      - event: "manual_detected"
        min_interval_ms: 500
      - event: "lux_change"
        min_interval_ms: 5000
        deduplicate_by: "zone_id"

    caching:
      sun_calculations:
        ttl_sec: 300  # Recalculate every 5 min
      weather_data:
        ttl_sec: 600
      zone_states:
        ttl_sec: 10

    async_operations:
      - operation: "audit_log_write"
        priority: "low"
      - operation: "telemetry_update"
        priority: "low"
      - operation: "light_state_apply"
        priority: "high"
        timeout_ms: 2000

    rate_limiting:
      per_zone:
        max_commands: 20
        window_sec: 60
        backoff_strategy: "exponential"
      global:
        max_events: 100
        window_sec: 60
```

### Benefits
- Reduced HA load
- Faster response times
- Prevents event storms
- Configurable trade-offs (responsiveness vs. efficiency)

---

## Implementation Priorities

### Phase 1: Foundation (High Value, Low Complexity)
1. **User-Definable Scene Library** - Immediate user benefit
2. **Backup & Restore System** - Risk mitigation
3. **YAML Schema Validation** - Development quality

### Phase 2: Intelligence (High Value, Medium Complexity)
4. **Time-of-Day & Occupancy Defaults** - Smart automation
5. **Advanced Conditional Logic Engine** - Simplify complex setups
6. **Circadian Rhythm Presets** - Health & wellness

### Phase 3: Scale (Medium Value, Medium Complexity)
7. **Transition Profiles** - Polish & refinement
8. **Per-Light Capability Mapping** - Robustness
9. **Performance Optimization** - Large deployment support

### Phase 4: Ecosystem (High Value, High Complexity)
10. **Multi-Home & Profile Support** - Advanced users
11. **Integration Webhooks** - Platform expansion
12. **Event Logging & Audit Trail** - Enterprise features

---

## Migration Strategy

### Backward Compatibility
- All enhancements opt-in via new YAML keys
- Existing v7.yaml continues to work without changes
- Deprecated features warn but don't break

### Example: Adding Scene Library to Existing Config
```yaml
# Existing v7.yaml (unchanged)
adaptive_lighting_adaptive:
  # ... existing config ...

# New additions in v7_enhanced.yaml
adaptive_lighting_pro:
  custom_scenes:  # NEW
    - id: "wfh_focus"
      # ... scene definition ...

packages:
  core_system: !include v7.yaml
  enhancements: !include v7_enhanced.yaml
```

---

## Developer Experience Improvements

### 1. Configuration Generator UI
Web-based tool to generate YAML snippets:
- Drag-drop zone creation
- Visual scene designer
- Condition builder
- Export to clipboard

### 2. Testing Framework
```yaml
adaptive_lighting_pro:
  tests:
    - name: "Movie mode activates on TV play"
      setup:
        - service: "media_player.turn_on"
          entity: "media_player.living_room_tv"
      assertions:
        - entity: "sensor.al_current_mode"
          state: "movie"
          timeout_sec: 5
```

### 3. Documentation Auto-Generation
Parse YAML and generate:
- Entity relationship diagrams
- Event flow visualizations
- Configuration reference docs

---

## Conclusion

These 12 enhancement categories transform the YAML lighting system from a functional automation platform into a **comprehensive, user-customizable, biologically-optimized lighting orchestration framework**.

**Key Principles:**
- **Declarative over Imperative**: YAML describes desired state, not steps
- **Composable**: Small, reusable building blocks
- **Observable**: Rich telemetry and audit trails
- **Forgiving**: Validation, defaults, and graceful degradation
- **Extensible**: Webhooks, profiles, and plugin architecture

**Next Steps:**
1. Review with stakeholders
2. Prioritize enhancements
3. Create technical design docs for selected items
4. Implement in phases with user testing

---

**Document Version:** 1.0
**Date:** 2025-11-15
**Related Files:**
- `/home/user/AL-Pro/v7.yaml` - Current implementation
- `/home/user/AL-Pro/implementation_2.yaml` - Simplified companion
- `/home/user/AL-Pro/IMPLEMENTATION_2_PLAN.md` - Migration guide
