"""Tests for sensor platform - comprehensive sensor suite.

Following claude.md standards: "You can't improve what you can't see"

Phase 2.3 tests verify all 7 sensor types:
1. ALPStatusSensor - Primary dashboard with 15+ attributes
2. RealtimeMonitorSensor - Event-driven calculation monitor
3. ZoneManualControlSensor - Per-zone manual control status
4. TotalManualControlSensor - Aggregate manual control count
5. ZonesWithManualControlSensor - Zone list
6. DeviationTrackerSensor - Deviation classification
7. SystemHealthSensor - Health scoring 0-100
"""
from datetime import datetime, UTC
from unittest.mock import MagicMock, AsyncMock, patch, call
from homeassistant.core import Event

import pytest

from custom_components.adaptive_lighting_pro.platforms.sensor import (
    ALPStatusSensor,
    RealtimeMonitorSensor,
    ZoneManualControlSensor,
    TotalManualControlSensor,
    ZonesWithManualControlSensor,
    DeviationTrackerSensor,
    SystemHealthSensor,
)


@pytest.mark.unit
@pytest.mark.sensor
class TestALPStatusSensor:
    """Test primary dashboard sensor with comprehensive attributes."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator with standard data structure."""
        coordinator = MagicMock()
        coordinator.data = {
            "global": {
                "paused": False,
                "total_brightness_adjustment": 0,
                "total_warmth_adjustment": 0,
                "current_scene": "default",
                "health_status": "Excellent",
                "health_score": 95,
            },
            "environmental": {
                "boost_active": False,
                "sunset_boost_active": False,
                "wake_boost_active": False,
                "current_boost_pct": 0,
                "sunset_boost_offset": 0,
                "wake_boost_pct": 0,
                "current_lux": 350,
            },
            "zones": {
                "bedroom": {
                    "adaptive_lighting_active": True,
                    "manual_control_active": False,
                    "computed_brightness_range": {
                        "min": 45,
                        "max": 100,
                        "boundary_collapsed": False,
                    },
                },
                "living_room": {
                    "adaptive_lighting_active": True,
                    "manual_control_active": False,
                    "computed_brightness_range": {
                        "min": 60,
                        "max": 100,
                        "boundary_collapsed": False,
                    },
                },
            },
        }
        coordinator.last_update_success_time = datetime.now(UTC)
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass with sun entity."""
        hass = MagicMock()
        sun_state = MagicMock()
        sun_state.attributes = {"elevation": 25.5}
        hass.states.get.return_value = sun_state
        return hass

    @pytest.fixture
    def status_sensor(self, mock_coordinator, mock_config_entry):
        """Create ALPStatusSensor."""
        sensor = ALPStatusSensor(mock_coordinator, mock_config_entry)
        sensor.hass = MagicMock()
        # Mock sun entity
        sun_state = MagicMock()
        sun_state.attributes = {"elevation": 25.5}
        sensor.hass.states.get.return_value = sun_state
        return sensor

    def test_status_sensor_initialization(self, status_sensor):
        """Test sensor initializes with correct unique_id and name."""
        assert status_sensor.unique_id == "adaptive_lighting_pro_test_entry_sensor_status"
        assert status_sensor.name == "ALP Status"
        assert status_sensor.icon == "mdi:information-outline"

    def test_native_value_adaptive_mode(self, status_sensor):
        """Test native_value shows 'Adaptive' when no modifiers active."""
        assert status_sensor.native_value == "Adaptive"

    def test_native_value_paused_mode(self, status_sensor, mock_coordinator):
        """Test native_value shows 'Paused' when system paused."""
        mock_coordinator.data["global"]["paused"] = True
        assert status_sensor.native_value == "Paused"

    def test_native_value_environmental_boost(self, status_sensor, mock_coordinator):
        """Test native_value shows environmental boost."""
        mock_coordinator.data["environmental"]["boost_active"] = True
        assert status_sensor.native_value == "Active (Environmental)"

    def test_native_value_combined_boosts(self, status_sensor, mock_coordinator):
        """Test native_value shows multiple active boosts."""
        mock_coordinator.data["environmental"]["boost_active"] = True
        mock_coordinator.data["environmental"]["sunset_boost_active"] = True
        mock_coordinator.data["environmental"]["wake_boost_active"] = True

        value = status_sensor.native_value
        assert "Environmental" in value
        assert "Sunset" in value
        assert "Wake" in value

    def test_native_value_manual_adjustment(self, status_sensor, mock_coordinator):
        """Test native_value shows manual adjustment."""
        mock_coordinator.data["global"]["total_brightness_adjustment"] = 15
        assert status_sensor.native_value == "Manual Adjustment (+15%)"

    def test_extra_state_attributes_complete(self, status_sensor):
        """Test all 15+ attributes are present."""
        attrs = status_sensor.extra_state_attributes

        # Verify all required attributes exist
        assert "active_modifiers" in attrs
        assert "last_action" in attrs
        assert "system_health" in attrs
        assert "health_score" in attrs
        assert "brightness_adjustment" in attrs
        assert "warmth_adjustment" in attrs
        assert "current_scene" in attrs
        assert "environmental_boost" in attrs
        assert "sunset_boost" in attrs
        assert "wake_boost" in attrs
        assert "current_lux" in attrs
        assert "sun_elevation" in attrs
        assert "active_switches" in attrs
        assert "managed_zones" in attrs
        assert "computed_ranges" in attrs
        assert "zones_with_timers" in attrs

    def test_active_modifiers_none(self, status_sensor):
        """Test active_modifiers returns ['None'] when nothing active."""
        attrs = status_sensor.extra_state_attributes
        assert attrs["active_modifiers"] == ["None"]

    def test_active_modifiers_environmental(self, status_sensor, mock_coordinator):
        """Test active_modifiers shows environmental boost."""
        mock_coordinator.data["environmental"]["boost_active"] = True
        mock_coordinator.data["environmental"]["current_boost_pct"] = 25

        attrs = status_sensor.extra_state_attributes
        assert "Environmental +25%" in attrs["active_modifiers"]

    def test_computed_ranges_structure(self, status_sensor):
        """Test computed_ranges includes all zones."""
        attrs = status_sensor.extra_state_attributes
        ranges = attrs["computed_ranges"]

        assert "bedroom" in ranges
        assert "living_room" in ranges
        assert ranges["bedroom"]["min"] == 45
        assert ranges["bedroom"]["max"] == 100


@pytest.mark.unit
@pytest.mark.sensor
class TestRealtimeMonitorSensor:
    """Test event-driven realtime monitor sensor."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator."""
        coordinator = MagicMock()
        coordinator.data = {}
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def mock_hass(self):
        """Create mock hass with event bus."""
        hass = MagicMock()
        hass.bus = MagicMock()
        hass.bus.async_listen = MagicMock()
        return hass

    @pytest.fixture
    def realtime_sensor(self, mock_coordinator, mock_config_entry, mock_hass):
        """Create RealtimeMonitorSensor."""
        sensor = RealtimeMonitorSensor(mock_coordinator, mock_config_entry, mock_hass)
        return sensor

    def test_realtime_sensor_initialization(self, realtime_sensor, mock_hass):
        """Test sensor initializes and registers event listener."""
        assert realtime_sensor.unique_id == "adaptive_lighting_pro_test_entry_sensor_realtime_monitor"
        assert realtime_sensor.name == "ALP Realtime Monitor"
        assert realtime_sensor.icon == "mdi:monitor-dashboard"

        # Verify event listener registered
        from custom_components.adaptive_lighting_pro.const import EVENT_CALCULATION_COMPLETE
        mock_hass.bus.async_listen.assert_called_once()

    def test_native_value_waiting_for_calculation(self, realtime_sensor):
        """Test native_value shows waiting state before any calculations."""
        assert realtime_sensor.native_value == "Waiting for calculation"

    def test_native_value_no_adjustment(self, realtime_sensor):
        """Test native_value shows no adjustment when zero."""
        realtime_sensor._last_calculation = {
            "final_brightness_adjustment": 0,
            "final_warmth_adjustment": 0,
        }
        assert realtime_sensor.native_value == "No adjustment"

    def test_native_value_brightness_adjustment(self, realtime_sensor):
        """Test native_value shows brightness adjustment."""
        realtime_sensor._last_calculation = {
            "final_brightness_adjustment": 15,
            "final_warmth_adjustment": 0,
        }
        assert realtime_sensor.native_value == "+15% brightness"

    def test_native_value_combined_adjustment(self, realtime_sensor):
        """Test native_value shows combined brightness and warmth."""
        realtime_sensor._last_calculation = {
            "final_brightness_adjustment": 15,
            "final_warmth_adjustment": -500,
        }
        value = realtime_sensor.native_value
        assert "+15% brightness" in value
        assert "-500K warmth" in value

    def test_calculation_event_updates_state(self, realtime_sensor):
        """Test calculation event handler updates state."""
        # Mock async_write_ha_state to avoid platform requirement
        realtime_sensor.async_write_ha_state = MagicMock()

        event_data = {
            "timestamp": "2025-10-02T06:30:00Z",
            "trigger_source": "coordinator_update",
            "final_brightness_adjustment": 20,
            "final_warmth_adjustment": 0,
        }
        event = MagicMock(data=event_data)

        realtime_sensor._calculation_event(event)

        assert realtime_sensor._last_calculation == event_data
        realtime_sensor.async_write_ha_state.assert_called_once()


@pytest.mark.unit
@pytest.mark.sensor
class TestZoneManualControlSensor:
    """Test per-zone manual control status sensor."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator with zone data."""
        coordinator = MagicMock()
        coordinator.data = {
            "zones": {
                "bedroom": {
                    "manual_control_active": True,
                    "lights_on_count": 3,
                },
            },
        }
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def zone_sensor(self, mock_coordinator, mock_config_entry):
        """Create ZoneManualControlSensor for bedroom."""
        sensor = ZoneManualControlSensor(mock_coordinator, mock_config_entry, "bedroom")
        return sensor

    def test_zone_sensor_initialization(self, zone_sensor):
        """Test sensor initializes with zone-specific unique_id and name."""
        assert zone_sensor.unique_id == "adaptive_lighting_pro_test_entry_sensor_manual_control_bedroom"
        assert zone_sensor.name == "Bedroom Manual Control"
        assert zone_sensor.icon == "mdi:hand-back-right"

    def test_native_value_manual_control_active(self, zone_sensor):
        """Test native_value shows light count when manual control active."""
        assert zone_sensor.native_value == "3 lights manually controlled"

    def test_native_value_no_manual_control(self, zone_sensor, mock_coordinator):
        """Test native_value shows no control when inactive."""
        mock_coordinator.data["zones"]["bedroom"]["manual_control_active"] = False
        assert zone_sensor.native_value == "No manual control"


@pytest.mark.unit
@pytest.mark.sensor
class TestSystemHealthSensor:
    """Test system health sensor with scoring algorithm."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator with healthy system."""
        coordinator = MagicMock()
        coordinator.data = {
            "zones": {
                "bedroom": {
                    "adaptive_lighting_active": True,
                    "computed_brightness_range": {"boundary_collapsed": False},
                },
                "living_room": {
                    "adaptive_lighting_active": True,
                    "computed_brightness_range": {"boundary_collapsed": False},
                },
            },
            "environmental": {
                "current_lux": 350,
            },
        }
        coordinator.last_update_success_time = datetime.now(UTC)
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def health_sensor(self, mock_coordinator, mock_config_entry):
        """Create SystemHealthSensor."""
        sensor = SystemHealthSensor(mock_coordinator, mock_config_entry)
        return sensor

    def test_health_sensor_initialization(self, health_sensor):
        """Test sensor initializes with correct unique_id and name."""
        assert health_sensor.unique_id == "adaptive_lighting_pro_test_entry_sensor_system_health"
        assert health_sensor.name == "ALP System Health"
        assert health_sensor.icon == "mdi:shield-check"

    def test_health_score_perfect_system(self, health_sensor):
        """Test health score is 100 for perfect system."""
        score = health_sensor._calculate_health_score()
        assert score == 100

    def test_health_score_offline_switch_deduction(self, health_sensor, mock_coordinator):
        """Test health score deducts 15 points per offline switch."""
        mock_coordinator.data["zones"]["bedroom"]["adaptive_lighting_active"] = False
        score = health_sensor._calculate_health_score()
        assert score == 85  # 100 - 15

    def test_health_score_boundary_collapse_deduction(self, health_sensor, mock_coordinator):
        """Test health score deducts 20 points per boundary collapse."""
        mock_coordinator.data["zones"]["bedroom"]["computed_brightness_range"]["boundary_collapsed"] = True
        score = health_sensor._calculate_health_score()
        assert score == 80  # 100 - 20

    def test_health_score_missing_lux_deduction(self, health_sensor, mock_coordinator):
        """Test health score deducts 10 points if lux sensor unavailable."""
        mock_coordinator.data["environmental"]["current_lux"] = 0
        score = health_sensor._calculate_health_score()
        assert score == 90  # 100 - 10

    def test_health_score_combined_deductions(self, health_sensor, mock_coordinator):
        """Test health score handles multiple deductions."""
        # Offline switch (15) + boundary collapse (20) + missing lux (10)
        mock_coordinator.data["zones"]["bedroom"]["adaptive_lighting_active"] = False
        mock_coordinator.data["zones"]["living_room"]["computed_brightness_range"]["boundary_collapsed"] = True
        mock_coordinator.data["environmental"]["current_lux"] = 0

        score = health_sensor._calculate_health_score()
        assert score == 55  # 100 - 15 - 20 - 10

    def test_native_value_excellent(self, health_sensor):
        """Test native_value returns 'Excellent' for score >= 90."""
        assert health_sensor.native_value == "Excellent"

    def test_native_value_good(self, health_sensor, mock_coordinator):
        """Test native_value returns 'Good' for score >= 75."""
        mock_coordinator.data["zones"]["bedroom"]["adaptive_lighting_active"] = False
        assert health_sensor.native_value == "Good"  # Score 85

    def test_native_value_fair(self, health_sensor, mock_coordinator):
        """Test native_value returns 'Fair' for score >= 50."""
        # Create score of 60
        mock_coordinator.data["zones"]["bedroom"]["adaptive_lighting_active"] = False
        mock_coordinator.data["zones"]["living_room"]["computed_brightness_range"]["boundary_collapsed"] = True
        mock_coordinator.data["environmental"]["current_lux"] = 0
        # Score = 100 - 15 - 20 - 10 = 55
        assert health_sensor.native_value == "Fair"

    def test_native_value_poor(self, health_sensor, mock_coordinator):
        """Test native_value returns 'Poor' for score < 50."""
        # Offline both switches + 2 collapses + no lux = 15+15+20+20+10 = 80 deducted
        mock_coordinator.data["zones"]["bedroom"]["adaptive_lighting_active"] = False
        mock_coordinator.data["zones"]["living_room"]["adaptive_lighting_active"] = False
        mock_coordinator.data["zones"]["bedroom"]["computed_brightness_range"]["boundary_collapsed"] = True
        mock_coordinator.data["zones"]["living_room"]["computed_brightness_range"]["boundary_collapsed"] = True
        mock_coordinator.data["environmental"]["current_lux"] = 0
        # Score = 100 - 80 = 20
        assert health_sensor.native_value == "Poor"


@pytest.mark.unit
@pytest.mark.sensor
class TestDeviationTrackerSensor:
    """Test deviation classification sensor."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator."""
        coordinator = MagicMock()
        coordinator.data = {
            "global": {
                "total_brightness_adjustment": 0,
                "total_warmth_adjustment": 0,
            },
        }
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def deviation_sensor(self, mock_coordinator, mock_config_entry):
        """Create DeviationTrackerSensor."""
        from custom_components.adaptive_lighting_pro.platforms.sensor import DeviationTrackerSensor
        sensor = DeviationTrackerSensor(mock_coordinator, mock_config_entry)
        return sensor

    def test_deviation_no_deviation(self, deviation_sensor):
        """Test classification shows 'No deviation' when zero."""
        assert deviation_sensor.native_value == "No deviation"

    def test_deviation_minor(self, deviation_sensor, mock_coordinator):
        """Test classification shows 'Minor' for small deviations."""
        mock_coordinator.data["global"]["total_brightness_adjustment"] = 8
        assert deviation_sensor.native_value == "Minor"

    def test_deviation_moderate(self, deviation_sensor, mock_coordinator):
        """Test classification shows 'Moderate' for medium deviations."""
        mock_coordinator.data["global"]["total_brightness_adjustment"] = 18
        assert deviation_sensor.native_value == "Moderate"

    def test_deviation_significant(self, deviation_sensor, mock_coordinator):
        """Test classification shows 'Significant' for large deviations."""
        mock_coordinator.data["global"]["total_brightness_adjustment"] = 35
        assert deviation_sensor.native_value == "Significant"


@pytest.mark.unit
@pytest.mark.sensor
class TestTotalManualControlSensor:
    """Test aggregate total manual control sensor."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator with multiple zones."""
        coordinator = MagicMock()
        coordinator.data = {
            "zones": {
                "bedroom": {"manual_control_active": True},
                "living_room": {"manual_control_active": False},
                "kitchen": {"manual_control_active": True},
            },
        }
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def total_sensor(self, mock_coordinator, mock_config_entry):
        """Create TotalManualControlSensor."""
        from custom_components.adaptive_lighting_pro.platforms.sensor import TotalManualControlSensor
        sensor = TotalManualControlSensor(mock_coordinator, mock_config_entry)
        return sensor

    def test_total_manual_control_count(self, total_sensor):
        """Test native_value returns count of zones with manual control."""
        assert total_sensor.native_value == 2  # bedroom and kitchen


@pytest.mark.unit
@pytest.mark.sensor
class TestZonesWithManualControlSensor:
    """Test zone list sensor."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator with multiple zones."""
        coordinator = MagicMock()
        coordinator.data = {
            "zones": {
                "bedroom": {"manual_control_active": True},
                "living_room": {"manual_control_active": False},
                "kitchen": {"manual_control_active": True},
            },
        }
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Create mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def zones_sensor(self, mock_coordinator, mock_config_entry):
        """Create ZonesWithManualControlSensor."""
        from custom_components.adaptive_lighting_pro.platforms.sensor import ZonesWithManualControlSensor
        sensor = ZonesWithManualControlSensor(mock_coordinator, mock_config_entry)
        return sensor

    def test_zones_list_format(self, zones_sensor):
        """Test native_value returns comma-separated zone names."""
        value = zones_sensor.native_value
        assert "Bedroom" in value
        assert "Kitchen" in value
        assert "Living Room" not in value

    def test_zones_list_empty(self, zones_sensor, mock_coordinator):
        """Test native_value returns 'None' when no manual control."""
        mock_coordinator.data["zones"]["bedroom"]["manual_control_active"] = False
        mock_coordinator.data["zones"]["kitchen"]["manual_control_active"] = False
        assert zones_sensor.native_value == "None"
