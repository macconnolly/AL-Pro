# Tactical Implementation Plan - Adaptive Lighting Pro Paradigm Parity

## PHASE 1: Critical Verification Tasks (Immediate)

### Task 1.1: Verify Manual Control Checking in Apply Path
**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Line Range**: 560-660 (_apply_adjustments_to_zone method)

**SEARCH FOR**:
```bash
grep -n "manual_control" coordinator.py | grep -A5 -B5 "_apply_adjustments_to_zone"
```

**VERIFY EXISTS**:
```python
# Before line 636 (change_switch_settings call)
al_state = self.hass.states.get(al_switch)
if al_state and al_state.attributes:
    manual_list = al_state.attributes.get("manual_control", [])
    if manual_list:  # Skip if ANY lights are manually controlled
        _LOGGER.debug("Skipping zone %s - has manual control: %s", zone_id, manual_list)
        return
```

**IF MISSING, ADD**:
Insert above check at line 625, before any service calls to AL.

---

### Task 1.2: Verify Service Call Parameters
**File**: `custom_components/adaptive_lighting_pro/coordinator.py`

**SEARCH PATTERN 1** - All change_switch_settings calls:
```bash
grep -n "change_switch_settings" coordinator.py
```

**VERIFY EACH HAS**:
```python
"use_defaults": "configuration"  # MUST be present in EVERY call
```

**SEARCH PATTERN 2** - All apply calls:
```bash
grep -n "adaptive_lighting.apply" coordinator.py
```

**VERIFY EACH HAS**:
```python
"turn_on_lights": False  # MUST be present
"transition": 1  # or 2, MUST be present
# NO "lights" parameter EXCEPT in _restore_adaptive_control after timer expiry
```

**FIX IF WRONG**:
- Line 636-640: Add `"use_defaults": "configuration"` if missing
- Line 646-653: Verify has `"turn_on_lights": False` and NO `"lights"` parameter
- Line 887-895: This is timer expiry - SHOULD have `"lights"` parameter

---

### Task 1.3: Audit Timer Expiry Apply Pattern
**File**: `custom_components/adaptive_lighting_pro/coordinator.py`
**Line**: 887-895

**CURRENT CODE**:
```python
await self.hass.services.async_call(
    ADAPTIVE_LIGHTING_DOMAIN,
    "apply",
    {
        "entity_id": al_switch,
        "turn_on_lights": False,
        "transition": 2,
    },
)
```

**CHANGE TO**:
```python
# Get zone lights for immediate restoration
zone_lights = zone_config.get("lights", [])
if zone_lights:
    await self.hass.services.async_call(
        ADAPTIVE_LIGHTING_DOMAIN,
        "apply",
        {
            "entity_id": al_switch,
            "lights": zone_lights,  # Force immediate restoration
            "turn_on_lights": False,
            "transition": 2,
        },
    )
```

**RATIONALE**: Implementation_1 pattern shows timer expiry uses lights parameter for immediate restoration vs waiting for AL's cycle.

---

## PHASE 2: Environmental Boost Enhancement Tasks

### Task 2.1: Read Current Environmental Implementation
**File**: `custom_components/adaptive_lighting_pro/features/environmental_adapter.py`

**COMMAND**:
```bash
cat -n features/environmental_adapter.py | head -200
```

**DOCUMENT**:
1. Current lux thresholds used
2. Current weather mappings
3. Presence of time-of-day gating
4. Presence of seasonal adjustment
5. Current maximum cap

---

### Task 2.2: Implement Time-of-Day Gating
**File**: `custom_components/adaptive_lighting_pro/features/environmental_adapter.py`
**Method**: `calculate_boost()`

**ADD THIS LOGIC**:
```python
# Time-of-day gating - CRITICAL: Disable at night
hour = dt_util.now(self.hass.config.time_zone).hour
if 22 <= hour or hour <= 6:
    _LOGGER.debug("Environmental boost disabled during night hours (22:00-06:00)")
    return BoostResult(
        value=0,
        source="environmental",
        details={
            "time_gated": True,
            "hour": hour,
            "reason": "Night time suppression (10 PM - 6 AM)"
        }
    )
elif 6 < hour <= 8 or 18 <= hour < 22:
    # Reduce effectiveness during transition periods
    boost_value = int(boost_value * 0.7)
    _LOGGER.debug("Environmental boost reduced to 70%% during transition (dawn/dusk)")
```

**INSERT LOCATION**: After initial boost calculation, before final return

---

### Task 2.3: Implement Seasonal Adjustments
**File**: `custom_components/adaptive_lighting_pro/features/environmental_adapter.py`
**Method**: `calculate_boost()`

**ADD THIS LOGIC**:
```python
# Seasonal adjustment
month = dt_util.now(self.hass.config.time_zone).month
if month in [12, 1, 2]:  # Winter
    boost_value += 8
    season = "winter"
    _LOGGER.debug("Winter seasonal adjustment: +8%")
elif month in [6, 7, 8]:  # Summer
    boost_value -= 3
    season = "summer"
    _LOGGER.debug("Summer seasonal adjustment: -3%")
else:
    season = "transition"
```

**INSERT LOCATION**: After weather boost calculation, before time-of-day gating

---

### Task 2.4: Implement Logarithmic Lux Thresholds
**File**: `custom_components/adaptive_lighting_pro/features/environmental_adapter.py`
**Method**: `calculate_boost()`

**REPLACE EXISTING LUX LOGIC WITH**:
```python
# Logarithmic lux scaling with specific thresholds
lux_boost = 0
if lux_value < 10:
    lux_boost = 15
elif lux_value < 25:
    lux_boost = 10
elif lux_value < 50:
    lux_boost = 7
elif lux_value < 100:
    lux_boost = 5
elif lux_value < 200:
    lux_boost = 3
elif lux_value < 400:
    lux_boost = 1
else:
    lux_boost = 0

_LOGGER.debug("Lux %d → boost %d%% (logarithmic scale)", lux_value, lux_boost)
```

---

### Task 2.5: Implement Complete Weather Mapping
**File**: `custom_components/adaptive_lighting_pro/features/environmental_adapter.py`
**Method**: `calculate_boost()`

**REPLACE WEATHER DICT WITH**:
```python
WEATHER_BOOST_MAP = {
    "fog": 20,
    "pouring": 18,
    "hail": 18,
    "snowy": 15,
    "snowy-rainy": 15,
    "rainy": 12,
    "lightning-rainy": 12,
    "cloudy": 10,
    "partlycloudy": 5,
    "windy": 2,
    "windy-variant": 2,
    "lightning": 8,
    "sunny": 0,
    "clear-night": 0,
    "clear": 0,
    "exceptional": 15,
}
```

---

## PHASE 3: Architecture Compliance Verification

### Task 3.1: Run Architectural Violation Checks
**COMMANDS TO RUN**:
```bash
# Check for coordinator.data access
grep -r "coordinator\.data\[" custom_components/adaptive_lighting_pro/platforms/
grep -r "coordinator\.data\[" custom_components/adaptive_lighting_pro/integrations/
grep -r "coordinator\.data\[" custom_components/adaptive_lighting_pro/services.py

# Check for private attribute access
grep -r "coordinator\._" custom_components/adaptive_lighting_pro/platforms/
grep -r "coordinator\._" custom_components/adaptive_lighting_pro/integrations/
grep -r "coordinator\._" custom_components/adaptive_lighting_pro/services.py

# Check for direct assignment
grep -r "coordinator\.[a-z_]* =" custom_components/adaptive_lighting_pro/platforms/
grep -r "coordinator\.[a-z_]* =" custom_components/adaptive_lighting_pro/integrations/
```

**EXPECTED**: All commands return 0 matches

**IF VIOLATIONS FOUND**:
1. Note file and line number
2. Identify what data is being accessed
3. Create coordinator method: `get_X()` or `set_X(value)`
4. Replace violation with method call
5. Test the replacement

---

### Task 3.2: Create Missing Coordinator Methods
**File**: `custom_components/adaptive_lighting_pro/coordinator.py`

**FOR EACH VIOLATION FOUND**:
```python
# Add after line 1950 (end of public API section)

def get_[property_name](self) -> [type]:
    """Get [description].

    Returns:
        [type]: [description]
    """
    return self._[property_name]

def set_[property_name](self, value: [type]) -> None:
    """Set [description].

    Args:
        value: [description]

    Raises:
        ValueError: If value is invalid
    """
    # Validate
    if not [validation]:
        raise ValueError(f"Invalid [property]: {value}")

    old_value = self._[property_name]
    self._[property_name] = value

    _LOGGER.debug("[Property] changed: %s → %s", old_value, value)

    # Trigger update if needed
    self.async_update_listeners()
```

---

## PHASE 4: Testing & Validation

### Task 4.1: Create Manual Control Test
**File**: `tests/unit/test_manual_control_paradigm.py`

**CREATE TEST**:
```python
async def test_apply_skips_zones_with_manual_control():
    """Verify _apply_adjustments_to_zone skips when AL has manual_control set."""
    coordinator = await create_test_coordinator()

    # Mock AL switch with manual_control
    mock_state = Mock()
    mock_state.attributes = {"manual_control": ["light.test_light"]}
    coordinator.hass.states.get = Mock(return_value=mock_state)

    # Mock service call
    coordinator.hass.services.async_call = AsyncMock()

    # Apply adjustments
    await coordinator._apply_adjustments_to_zone("test_zone", {"adaptive_lighting_switch": "switch.test"})

    # Verify NO service calls made
    coordinator.hass.services.async_call.assert_not_called()
```

---

### Task 4.2: Create Timer Expiry Test
**File**: `tests/unit/test_timer_expiry_paradigm.py`

**CREATE TEST**:
```python
async def test_timer_expiry_specifies_lights_parameter():
    """Verify timer expiry apply includes lights parameter for immediate restoration."""
    coordinator = await create_test_coordinator()

    # Setup zone with lights
    zone_config = {
        "adaptive_lighting_switch": "switch.test",
        "lights": ["light.test1", "light.test2"]
    }

    # Mock service call
    coordinator.hass.services.async_call = AsyncMock()

    # Restore adaptive control (timer expired)
    await coordinator._restore_adaptive_control("test_zone")

    # Verify apply was called WITH lights parameter
    calls = coordinator.hass.services.async_call.call_args_list
    apply_call = [c for c in calls if c[0][1] == "apply"][0]

    assert "lights" in apply_call[1]["data"]
    assert apply_call[1]["data"]["lights"] == ["light.test1", "light.test2"]
    assert apply_call[1]["data"]["transition"] == 2
    assert apply_call[1]["data"]["turn_on_lights"] == False
```

---

### Task 4.3: Create Environmental Time Gating Test
**File**: `tests/unit/test_environmental_paradigm.py`

**CREATE TEST**:
```python
async def test_environmental_boost_disabled_at_night():
    """Verify environmental boost returns 0 between 10 PM and 6 AM."""
    adapter = EnvironmentalAdapter(hass, coordinator)

    # Mock night time (11 PM)
    with patch("homeassistant.util.dt.now") as mock_now:
        mock_now.return_value = datetime(2024, 1, 1, 23, 0, 0)

        # Set dark and foggy conditions that would normally boost
        mock_lux_sensor(5)  # Very dark
        mock_weather("fog")  # Foggy

        result = adapter.calculate_boost()

        assert result.value == 0
        assert result.details["time_gated"] == True
        assert "Night time suppression" in result.details["reason"]
```

---

## PHASE 5: Integration Testing

### Task 5.1: Manual Scene Stickiness Test
**MANUAL TEST PROCEDURE**:
1. Apply "All Lights" scene via service call
2. Wait 5 seconds
3. Check `switch.adaptive_lighting_accent_spots` attributes
4. Verify `manual_control` contains individual light entities
5. Trigger coordinator refresh: `coordinator.async_request_refresh()`
6. Wait 2 seconds
7. Check lights maintained scene levels (did not change)
8. Wait for timer expiry
9. Verify lights return to adaptive control

**EXPECTED LOG ENTRIES**:
```
"Marked N individual lights in zone X as manually controlled"
"Skipping zone X - has manual control: [list of lights]"
"Timer expired for zone X: Released manual control for N lights"
```

---

### Task 5.2: Environmental Boost Night Test
**MANUAL TEST PROCEDURE**:
1. Set system time to 11 PM
2. Set lux sensor to 5 (very dark)
3. Set weather to "fog"
4. Check sensor.alp_environmental_boost_main_living
5. Verify value is 0%
6. Check logs for "Environmental boost disabled during night hours"
7. Set time to 7 AM
8. Verify boost activates (should be ~25%)

---

### Task 5.3: Instant Update Test
**MANUAL TEST PROCEDURE**:
1. Press Zen32 button 2 (brighter)
2. Measure time until lights change
3. Must be < 100ms
4. Check logs for "Applying adjustments to all zones immediately"
5. Verify AL switches show updated boundaries
6. Verify manual_control remains empty

---

## PHASE 6: Production Deployment

### Task 6.1: Pre-Deployment Checklist
**RUN THESE COMMANDS**:
```bash
# Syntax check
python3 -m py_compile custom_components/adaptive_lighting_pro/*.py
python3 -m py_compile custom_components/adaptive_lighting_pro/features/*.py
python3 -m py_compile custom_components/adaptive_lighting_pro/integrations/*.py

# Run tests
pytest tests/unit/test_manual_control_paradigm.py -v
pytest tests/unit/test_timer_expiry_paradigm.py -v
pytest tests/unit/test_environmental_paradigm.py -v

# Architecture compliance
./check_architecture.sh  # Create this script with all grep commands

# Check for debug logging
grep -r "LOGGER.debug" custom_components/ | wc -l  # Should be > 50
```

---

### Task 6.2: Upload Script
**CREATE FILE**: `upload_paradigm_fixes.py`
```python
#!/usr/bin/env python3
import paramiko
import os

FILES_TO_UPLOAD = [
    "custom_components/adaptive_lighting_pro/coordinator.py",
    "custom_components/adaptive_lighting_pro/features/environmental_adapter.py",
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.0.0.21", username="root", password=os.environ.get("HA_SSH_PASS"))

sftp = ssh.open_sftp()
for file in FILES_TO_UPLOAD:
    remote_path = f"/config/{file}"
    sftp.put(file, remote_path)
    print(f"✓ Uploaded {file}")

# Restart Home Assistant
stdin, stdout, stderr = ssh.exec_command("ha core restart")
print("✓ Restarting Home Assistant...")

ssh.close()
```

---

### Task 6.3: Post-Deployment Verification
**CHECK THESE ENDPOINTS**:
```bash
# Check integration loaded
curl http://10.0.0.21:8123/api/states/switch.alp_pause_main_living

# Check sensors updating
curl http://10.0.0.21:8123/api/states/sensor.alp_calculated_brightness_main_living

# Check environmental boost
curl http://10.0.0.21:8123/api/states/sensor.alp_environmental_boost_main_living

# Check system health
curl http://10.0.0.21:8123/api/states/sensor.alp_system_health
```

**CHECK LOGS**:
```bash
ssh root@10.0.0.21 "grep 'adaptive_lighting_pro' /config/home-assistant.log | tail -50"
```

**EXPECTED**: No errors, see "Coordinator initialized", "Environmental boost disabled during night hours"

---

## Success Criteria

### Immediate (Phase 1-3)
- [ ] Manual control checking verified/added
- [ ] Service call parameters consistent
- [ ] Timer expiry uses lights parameter
- [ ] Environmental has time gating
- [ ] Environmental has seasonal adjustment
- [ ] Environmental has logarithmic lux
- [ ] Architecture violations: 0

### Testing (Phase 4-5)
- [ ] All unit tests pass
- [ ] Scene stickiness verified
- [ ] Night suppression verified
- [ ] Instant updates < 100ms
- [ ] No boundary collapses

### Production (Phase 6)
- [ ] Deployed to Home Assistant
- [ ] No errors in logs
- [ ] All sensors updating
- [ ] Physical buttons responsive
- [ ] Living with it for 24 hours without issues

---

## Emergency Rollback

If issues occur:
```bash
ssh root@10.0.0.21 "cd /config && git checkout custom_components/adaptive_lighting_pro/"
ssh root@10.0.0.21 "ha core restart"
```

---

**REMEMBER**: Every line affects daily life. Test like you live here. Because you do.