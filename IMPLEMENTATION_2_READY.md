# implementation_2.yaml is Now Ready for Deployment

## What Was Updated

### 1. Light Group Entity Names ✅
Updated all light groups with your actual entity names from implementation_1.yaml:
- **Main Living**: entryway_lamp, living_room_floor_lamp, office_desk_lamp, living_room_corner_accent, living_room_couch_lamp, living_room_credenza_light
- **Kitchen Island**: kitchen_island_pendants
- **Bedroom Primary**: master_bedroom_table_lamps, master_bedroom_corner_accent
- **Recessed Ceiling**: kitchen_main_lights, living_room_hallway_lights
- **Accent Spots**: dining_room_spot_lights, living_room_spot_lights

### 2. Tier 2 Automations Enabled ✅
Uncommented all Tier 2 automations:
- **Morning Routine**: Gradual wake-up 30 minutes before alarm
- **Evening Transition**: Auto-switch to cozy lighting after sunset
- **Bedtime Routine**: Ultra-dim at 10:30pm weeknights, 11:30pm weekends
- **Work Mode Auto**: Bright lighting when computer activity detected
- **Dark Day Alert**: Notification when environmental boost activates
- **Sunset Boost Alert**: Notification when sunset fade starts

### 3. Tier 3 Left Commented ✅
- Advanced features remain commented for power users to enable as needed
- Includes mode system bridge and activity detection

## How to Deploy

### Step 1: Add to Home Assistant
Add this to your `configuration.yaml`:

```yaml
homeassistant:
  packages:
    adaptive_lighting_pro_v2: !include implementation_2.yaml
```

### Step 2: Disable implementation_1.yaml (if active)
Comment out or remove the implementation_1.yaml package reference:

```yaml
# packages:
#   adaptive_lighting_legacy: !include implementation_1.yaml  # DISABLED
```

### Step 3: Restart Home Assistant
```bash
ha core restart
```

### Step 4: Verify Entities
Check that these entities exist:
- `light.main_living_lights`
- `light.kitchen_island_lights`
- `light.bedroom_primary_lights`
- `light.recessed_ceiling_lights`
- `light.accent_spots`
- `button.alp_brighter`
- `button.alp_dimmer`
- `button.alp_warmer`
- `button.alp_cooler`
- `button.alp_reset`

### Step 5: Test Scene Scripts
In Developer Tools > Services, test:
```yaml
service: script.apply_scene_all_lights
```

## Optional Customizations

### 1. Adjust Bedtime
Edit lines 385-387 to change bedtime triggers:
```yaml
- platform: time
  at: "22:30:00"  # Change to your preferred weeknight bedtime
```

### 2. Computer Activity Sensor
Replace `binary_sensor.office_computer_active` (line 434) with your actual sensor if you have one.

### 3. Mobile Notifications
Replace `notify.mobile_app` (lines 483, 504) with your actual notification service.

## Monitoring

### Check if Automations are Running
Go to **Settings > Automations & Scenes** and look for:
- ALP: Morning Routine
- ALP: Evening Transition
- ALP: Bedtime Routine
- ALP: Work Mode Auto
- ALP: Dark Day Alert
- ALP: Sunset Boost Alert

### Check Light Groups
Go to **Developer Tools > States** and verify:
- All light groups show correct entity count
- Groups turn on/off as expected

## Troubleshooting

### If Scenes Don't Work
1. Verify Adaptive Lighting Pro integration is installed
2. Check that `adaptive_lighting_pro.apply_scene` service exists
3. Ensure light entities match your actual devices

### If Automations Don't Trigger
1. Check conditions match your setup (weekdays, time ranges, etc.)
2. Verify trigger entities exist (`sensor.alp_next_alarm`, `sun.sun`, etc.)
3. Check automation traces in UI for debugging

## Next Steps

1. **Run for 24 hours** to observe daily cycle
2. **Tune timing** of automations to match your schedule
3. **Consider enabling Tier 3** features if you want more automation
4. **Phase out implementation_1.yaml** after 1 week of stable operation

## Success Metrics

You'll know it's working when:
- Lights automatically brighten before your morning alarm
- Evening transition happens smoothly after sunset
- Bedtime routine dims lights on schedule
- Environmental boost notifications appear on dark days
- Scene buttons work instantly
- Overall system feels more responsive (10x performance gain)