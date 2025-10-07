"""Tests for number platform - user sliders and config inputs.

Following claude.md standards: "This is YOUR home. You live here."

Test Philosophy:
- Numbers are your control sliders and precise config inputs
- Sliders (brightness/warmth adjustments) are for quick daily changes
- Boxes (increments/timeouts) are for fine-tuning button behavior
- Every test represents real dashboard interactions

Real Scenarios:
- Dashboard slider: Drag brightness from 0% to +25% → Video call ready
- Fine-tune buttons: Set increment to 5% → Smaller, more precise adjustments
- Timeout config: Change from 1 hour to 30 minutes → Faster auto-restore
- Error recovery: Coordinator fails → Entity shows default, doesn't crash dashboard
"""
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from homeassistant.components.number import NumberMode
from homeassistant.const import EntityCategory

from custom_components.adaptive_lighting_pro.number import (
    async_setup_entry,
    ALPBrightnessAdjustmentNumber,
    ALPWarmthAdjustmentNumber,
    ALPBrightnessIncrementNumber,
    ALPColorTempIncrementNumber,
    ALPManualTimeoutNumber,
)
from custom_components.adaptive_lighting_pro.const import (
    DOMAIN,
    BRIGHTNESS_ADJUSTMENT_MIN,
    BRIGHTNESS_ADJUSTMENT_MAX,
    BRIGHTNESS_ADJUSTMENT_STEP,
    WARMTH_ADJUSTMENT_MIN,
    WARMTH_ADJUSTMENT_MAX,
    WARMTH_ADJUSTMENT_STEP,
    BRIGHTNESS_INCREMENT_MIN,
    BRIGHTNESS_INCREMENT_MAX,
    BRIGHTNESS_INCREMENT_STEP,
    COLOR_TEMP_INCREMENT_MIN,
    COLOR_TEMP_INCREMENT_MAX,
    COLOR_TEMP_INCREMENT_STEP,
    MANUAL_TIMEOUT_MIN,
    MANUAL_TIMEOUT_MAX,
    MANUAL_TIMEOUT_STEP,
)


@pytest.mark.unit
@pytest.mark.number
class TestNumberPlatformSetup:
    """Test number platform setup and entity creation."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator for number entities."""
        coordinator = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.entry_id = "test_entry"
        coordinator.get_brightness_adjustment = MagicMock(return_value=0)
        coordinator.get_warmth_adjustment = MagicMock(return_value=0)
        coordinator.get_brightness_increment = MagicMock(return_value=10)
        coordinator.get_color_temp_increment = MagicMock(return_value=500)
        coordinator.get_manual_control_timeout = MagicMock(return_value=3600)
        return coordinator

    @pytest.fixture
    def mock_hass(self, mock_coordinator):
        """Mock Home Assistant instance."""
        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                "test_entry": {"coordinator": mock_coordinator}
            }
        }
        return hass

    @pytest.fixture
    def mock_config_entry(self):
        """Mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.mark.asyncio
    async def test_setup_creates_five_number_entities(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """SCENARIO: Integration loads, needs dashboard number controls

        EXPECTED: Creates 5 number entities (2 sliders + 3 config boxes)
        WHY: User needs sliders for adjustments and boxes for fine-tuning
        """
        async_add_entities = MagicMock()

        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

        # Verify 5 entities created
        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 5

        # Verify entity types
        assert isinstance(entities[0], ALPBrightnessAdjustmentNumber)
        assert isinstance(entities[1], ALPWarmthAdjustmentNumber)
        assert isinstance(entities[2], ALPBrightnessIncrementNumber)
        assert isinstance(entities[3], ALPColorTempIncrementNumber)
        assert isinstance(entities[4], ALPManualTimeoutNumber)

    @pytest.mark.asyncio
    async def test_setup_handles_legacy_storage_pattern(self, mock_hass, mock_config_entry):
        """SCENARIO: Integration uses legacy direct coordinator storage

        EXPECTED: Setup extracts coordinator correctly
        WHY: Backward compatibility with old storage pattern
        """
        # Setup legacy direct storage (coordinator directly, not in dict)
        legacy_coordinator = MagicMock()
        legacy_coordinator.config_entry = MagicMock()
        legacy_coordinator.config_entry.entry_id = "test_entry"
        legacy_coordinator.get_brightness_adjustment = MagicMock(return_value=0)
        legacy_coordinator.get_warmth_adjustment = MagicMock(return_value=0)
        legacy_coordinator.get_brightness_increment = MagicMock(return_value=10)
        legacy_coordinator.get_color_temp_increment = MagicMock(return_value=500)
        legacy_coordinator.get_manual_control_timeout = MagicMock(return_value=3600)

        mock_hass.data = {DOMAIN: {"test_entry": legacy_coordinator}}

        async_add_entities = MagicMock()

        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

        # Should still create entities successfully
        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 5


@pytest.mark.unit
@pytest.mark.number
class TestBrightnessAdjustmentNumber:
    """Test brightness adjustment slider entity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with brightness methods."""
        coordinator = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.entry_id = "test_entry"
        coordinator.get_brightness_adjustment = MagicMock(return_value=0)
        coordinator.set_brightness_adjustment = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def entity(self, mock_coordinator, mock_config_entry):
        """Create brightness adjustment entity."""
        return ALPBrightnessAdjustmentNumber(mock_coordinator, mock_config_entry)

    def test_entity_attributes_configured_correctly(self, entity):
        """SCENARIO: Entity created, dashboard needs proper configuration

        EXPECTED: Slider mode, correct range (-100 to +100), % unit
        WHY: Dashboard renders based on these attributes
        """
        assert entity._attr_entity_category == EntityCategory.CONFIG
        assert entity._attr_native_min_value == BRIGHTNESS_ADJUSTMENT_MIN
        assert entity._attr_native_max_value == BRIGHTNESS_ADJUSTMENT_MAX
        assert entity._attr_native_step == BRIGHTNESS_ADJUSTMENT_STEP
        assert entity._attr_native_unit_of_measurement == "%"
        assert entity._attr_icon == "mdi:brightness-6"
        assert entity._attr_mode == NumberMode.SLIDER
        assert entity._attr_name == "Brightness Adjustment"
        assert entity._attr_unique_id == "adaptive_lighting_pro_test_entry_number_brightness_adjustment"

    def test_native_value_reads_from_coordinator(self, entity, mock_coordinator):
        """SCENARIO: Dashboard loads, needs current brightness adjustment

        EXPECTED: Reads from coordinator API (not internal state)
        WHY: Architectural principle - no direct coordinator access
        """
        mock_coordinator.get_brightness_adjustment.return_value = 25

        value = entity.native_value

        assert value == 25
        mock_coordinator.get_brightness_adjustment.assert_called_once()

    def test_native_value_handles_coordinator_error(self, entity, mock_coordinator):
        """SCENARIO: Coordinator raises error during get

        EXPECTED: Returns 0 default, logs error, doesn't crash dashboard
        WHY: Dashboard must stay responsive even if coordinator fails
        """
        mock_coordinator.get_brightness_adjustment.side_effect = AttributeError("Test error")

        value = entity.native_value

        # Should return default, not crash
        assert value == 0.0

    @pytest.mark.asyncio
    async def test_dashboard_slider_video_call_boost(self, entity, mock_coordinator):
        """SCENARIO: Video call in 30 seconds, drag slider from 0% to +25%

        EXPECTED: Sets brightness via coordinator WITHOUT timers (permanent preference)
        WHY: Sliders are persistent config, not temporary button presses
        """
        await entity.async_set_native_value(25.0)

        # Verify coordinator called correctly (no timers for slider)
        mock_coordinator.set_brightness_adjustment.assert_called_once_with(25, start_timers=False)

    @pytest.mark.asyncio
    async def test_dashboard_slider_dim_for_evening(self, entity, mock_coordinator):
        """SCENARIO: Evening wind-down, drag slider from 0% to -15%

        EXPECTED: Sets negative adjustment without starting timers
        WHY: User wants permanent dimmer setting, not temporary
        """
        await entity.async_set_native_value(-15.0)

        mock_coordinator.set_brightness_adjustment.assert_called_once_with(-15, start_timers=False)

    @pytest.mark.asyncio
    async def test_slider_set_handles_coordinator_error(self, entity, mock_coordinator):
        """SCENARIO: Coordinator fails during set operation

        EXPECTED: Re-raises exception so dashboard shows error
        WHY: User needs to know their slider change failed
        """
        mock_coordinator.set_brightness_adjustment.side_effect = RuntimeError("Test error")

        with pytest.raises(RuntimeError):
            await entity.async_set_native_value(30.0)

    @pytest.mark.asyncio
    async def test_slider_converts_float_to_int(self, entity, mock_coordinator):
        """SCENARIO: Dashboard sends float (25.5%), need int for coordinator

        EXPECTED: Converts to int before calling coordinator
        WHY: Coordinator expects int, dashboard sends float
        """
        await entity.async_set_native_value(25.5)

        # Should call with int, not float
        mock_coordinator.set_brightness_adjustment.assert_called_once_with(25, start_timers=False)


@pytest.mark.unit
@pytest.mark.number
class TestWarmthAdjustmentNumber:
    """Test warmth adjustment slider entity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with warmth methods."""
        coordinator = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.entry_id = "test_entry"
        coordinator.get_warmth_adjustment = MagicMock(return_value=0)
        coordinator.set_warmth_adjustment = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def entity(self, mock_coordinator, mock_config_entry):
        """Create warmth adjustment entity."""
        return ALPWarmthAdjustmentNumber(mock_coordinator, mock_config_entry)

    def test_entity_attributes_configured_correctly(self, entity):
        """SCENARIO: Entity created for color temperature control

        EXPECTED: Slider mode, correct range (-2500K to +2500K), K unit
        WHY: Dashboard renders warmth slider based on these attributes
        """
        assert entity._attr_entity_category == EntityCategory.CONFIG
        assert entity._attr_native_min_value == WARMTH_ADJUSTMENT_MIN
        assert entity._attr_native_max_value == WARMTH_ADJUSTMENT_MAX
        assert entity._attr_native_step == WARMTH_ADJUSTMENT_STEP
        assert entity._attr_native_unit_of_measurement == "K"
        assert entity._attr_icon == "mdi:thermometer"
        assert entity._attr_mode == NumberMode.SLIDER
        assert entity._attr_name == "Warmth Adjustment"
        assert entity._attr_unique_id == "adaptive_lighting_pro_test_entry_number_warmth_adjustment"

    def test_native_value_reads_from_coordinator(self, entity, mock_coordinator):
        """SCENARIO: Dashboard loads, needs current warmth adjustment

        EXPECTED: Reads from coordinator API
        WHY: Follow architectural pattern - coordinator methods only
        """
        mock_coordinator.get_warmth_adjustment.return_value = -800

        value = entity.native_value

        assert value == -800
        mock_coordinator.get_warmth_adjustment.assert_called_once()

    @pytest.mark.asyncio
    async def test_dashboard_slider_cooler_for_focus(self, entity, mock_coordinator):
        """SCENARIO: Focus work, want cooler (bluer) light, drag to +1000K

        EXPECTED: Sets warmth adjustment without starting timers
        WHY: Slider is persistent preference, not temporary override
        """
        await entity.async_set_native_value(1000.0)

        mock_coordinator.set_warmth_adjustment.assert_called_once_with(1000, start_timers=False)

    @pytest.mark.asyncio
    async def test_dashboard_slider_warmer_for_evening(self, entity, mock_coordinator):
        """SCENARIO: Evening relaxation, want warmer (yellower) light, drag to -1500K

        EXPECTED: Sets negative warmth adjustment
        WHY: User wants permanently warmer lights for evening
        """
        await entity.async_set_native_value(-1500.0)

        mock_coordinator.set_warmth_adjustment.assert_called_once_with(-1500, start_timers=False)

    def test_native_value_handles_coordinator_error(self, entity, mock_coordinator):
        """SCENARIO: Coordinator fails during value read

        EXPECTED: Returns 0 default, doesn't crash dashboard
        WHY: Dashboard must stay responsive
        """
        mock_coordinator.get_warmth_adjustment.side_effect = KeyError("Test error")

        value = entity.native_value

        assert value == 0.0


@pytest.mark.unit
@pytest.mark.number
class TestBrightnessIncrementNumber:
    """Test brightness increment config entity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with increment methods."""
        coordinator = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.entry_id = "test_entry"
        coordinator.get_brightness_increment = MagicMock(return_value=10)
        coordinator.set_brightness_increment = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def entity(self, mock_coordinator, mock_config_entry):
        """Create brightness increment entity."""
        return ALPBrightnessIncrementNumber(mock_coordinator, mock_config_entry)

    def test_entity_attributes_configured_correctly(self, entity):
        """SCENARIO: Entity created for button increment config

        EXPECTED: Box mode (not slider), range 1-50%, % unit
        WHY: Precise numeric input for button step size
        """
        assert entity._attr_entity_category == EntityCategory.CONFIG
        assert entity._attr_native_min_value == BRIGHTNESS_INCREMENT_MIN
        assert entity._attr_native_max_value == BRIGHTNESS_INCREMENT_MAX
        assert entity._attr_native_step == BRIGHTNESS_INCREMENT_STEP
        assert entity._attr_native_unit_of_measurement == "%"
        assert entity._attr_icon == "mdi:format-line-spacing"
        assert entity._attr_mode == NumberMode.BOX  # Box input, not slider
        assert entity._attr_name == "Brightness Increment"
        assert entity._attr_unique_id == "adaptive_lighting_pro_test_entry_number_brightness_increment"

    def test_native_value_reads_from_coordinator(self, entity, mock_coordinator):
        """SCENARIO: Dashboard loads, needs current button increment

        EXPECTED: Reads from coordinator API, converts to float
        WHY: NumberEntity expects float return type
        """
        mock_coordinator.get_brightness_increment.return_value = 15

        value = entity.native_value

        assert value == 15.0
        assert isinstance(value, float)
        mock_coordinator.get_brightness_increment.assert_called_once()

    @pytest.mark.asyncio
    async def test_fine_tune_button_increment_to_5_percent(self, entity, mock_coordinator):
        """SCENARIO: User wants smaller button steps for precise control

        EXPECTED: Sets increment to 5%, updates coordinator config
        WHY: Smaller increments = more granular brightness control
        """
        await entity.async_set_native_value(5.0)

        # Verify coordinator config updated
        mock_coordinator.set_brightness_increment.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_increase_button_increment_to_20_percent(self, entity, mock_coordinator):
        """SCENARIO: User wants faster brightness changes, bigger steps

        EXPECTED: Sets increment to 20%, updates coordinator
        WHY: Larger increments = fewer button presses needed
        """
        await entity.async_set_native_value(20.0)

        mock_coordinator.set_brightness_increment.assert_called_once_with(20)

    def test_native_value_handles_coordinator_error(self, entity, mock_coordinator):
        """SCENARIO: Coordinator fails during get

        EXPECTED: Returns 10.0 default (standard 10% increment)
        WHY: Dashboard needs sensible default
        """
        mock_coordinator.get_brightness_increment.side_effect = AttributeError("Test error")

        value = entity.native_value

        assert value == 10.0


@pytest.mark.unit
@pytest.mark.number
class TestColorTempIncrementNumber:
    """Test color temperature increment config entity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with color temp increment methods."""
        coordinator = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.entry_id = "test_entry"
        coordinator.get_color_temp_increment = MagicMock(return_value=500)
        coordinator.set_color_temp_increment = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def entity(self, mock_coordinator, mock_config_entry):
        """Create color temperature increment entity."""
        return ALPColorTempIncrementNumber(mock_coordinator, mock_config_entry)

    def test_entity_attributes_configured_correctly(self, entity):
        """SCENARIO: Entity created for warmth button config

        EXPECTED: Box mode, range 100-1000K, K unit
        WHY: Precise config for color temperature button steps
        """
        assert entity._attr_entity_category == EntityCategory.CONFIG
        assert entity._attr_native_min_value == COLOR_TEMP_INCREMENT_MIN
        assert entity._attr_native_max_value == COLOR_TEMP_INCREMENT_MAX
        assert entity._attr_native_step == COLOR_TEMP_INCREMENT_STEP
        assert entity._attr_native_unit_of_measurement == "K"
        assert entity._attr_icon == "mdi:format-line-spacing"
        assert entity._attr_mode == NumberMode.BOX
        assert entity._attr_name == "Color Temperature Increment"
        assert entity._attr_unique_id == "adaptive_lighting_pro_test_entry_number_color_temp_increment"

    def test_native_value_reads_from_coordinator(self, entity, mock_coordinator):
        """SCENARIO: Dashboard loads, needs current warmth button increment

        EXPECTED: Reads from coordinator API, converts to float
        WHY: NumberEntity expects float return type
        """
        mock_coordinator.get_color_temp_increment.return_value = 750

        value = entity.native_value

        assert value == 750.0
        assert isinstance(value, float)
        mock_coordinator.get_color_temp_increment.assert_called_once()

    @pytest.mark.asyncio
    async def test_fine_tune_warmth_increment_to_250K(self, entity, mock_coordinator):
        """SCENARIO: User wants subtle warmth changes, smaller steps

        EXPECTED: Sets increment to 250K, updates coordinator
        WHY: Smaller steps for more precise color control
        """
        await entity.async_set_native_value(250.0)

        mock_coordinator.set_color_temp_increment.assert_called_once_with(250)

    @pytest.mark.asyncio
    async def test_increase_warmth_increment_to_1000K(self, entity, mock_coordinator):
        """SCENARIO: User wants dramatic warmth changes, bigger steps

        EXPECTED: Sets increment to 1000K (max)
        WHY: Large steps for quick transitions between warm/cool
        """
        await entity.async_set_native_value(1000.0)

        mock_coordinator.set_color_temp_increment.assert_called_once_with(1000)

    def test_native_value_handles_coordinator_error(self, entity, mock_coordinator):
        """SCENARIO: Coordinator fails during get

        EXPECTED: Returns 500.0 default (standard 500K increment)
        WHY: Dashboard needs sensible default
        """
        mock_coordinator.get_color_temp_increment.side_effect = KeyError("Test error")

        value = entity.native_value

        assert value == 500.0


@pytest.mark.unit
@pytest.mark.number
class TestManualTimeoutNumber:
    """Test manual control timeout config entity."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator with timeout methods."""
        coordinator = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.entry_id = "test_entry"
        coordinator.get_manual_control_timeout = MagicMock(return_value=3600)
        coordinator.set_manual_control_timeout = AsyncMock()
        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    @pytest.fixture
    def entity(self, mock_coordinator, mock_config_entry):
        """Create manual timeout entity."""
        return ALPManualTimeoutNumber(mock_coordinator, mock_config_entry)

    def test_entity_attributes_configured_correctly(self, entity):
        """SCENARIO: Entity created for timer duration config

        EXPECTED: Box mode, range 300-14400s (5min to 4hr), seconds unit
        WHY: Precise config for auto-restore timer
        """
        assert entity._attr_entity_category == EntityCategory.CONFIG
        assert entity._attr_native_min_value == MANUAL_TIMEOUT_MIN
        assert entity._attr_native_max_value == MANUAL_TIMEOUT_MAX
        assert entity._attr_native_step == MANUAL_TIMEOUT_STEP
        assert entity._attr_native_unit_of_measurement == "s"
        assert entity._attr_icon == "mdi:timer-outline"
        assert entity._attr_mode == NumberMode.BOX
        assert entity._attr_name == "Manual Control Timeout"
        assert entity._attr_unique_id == "adaptive_lighting_pro_test_entry_number_manual_timeout"

    def test_native_value_reads_from_coordinator(self, entity, mock_coordinator):
        """SCENARIO: Dashboard loads, needs current timeout setting

        EXPECTED: Reads from coordinator API, converts to float
        WHY: NumberEntity expects float return type
        """
        mock_coordinator.get_manual_control_timeout.return_value = 1800

        value = entity.native_value

        assert value == 1800.0
        assert isinstance(value, float)
        mock_coordinator.get_manual_control_timeout.assert_called_once()

    @pytest.mark.asyncio
    async def test_quick_restore_30_minute_timeout(self, entity, mock_coordinator):
        """SCENARIO: User wants faster auto-restore after manual changes

        EXPECTED: Sets timeout to 1800s (30 minutes)
        WHY: Shorter timeout = AL resumes control sooner
        """
        await entity.async_set_native_value(1800.0)  # 30 minutes

        mock_coordinator.set_manual_control_timeout.assert_called_once_with(1800)

    @pytest.mark.asyncio
    async def test_long_manual_period_4_hour_timeout(self, entity, mock_coordinator):
        """SCENARIO: User wants manual changes to last longer (party mode)

        EXPECTED: Sets timeout to 14400s (4 hours, max)
        WHY: Longer timeout = manual control stays active longer
        """
        await entity.async_set_native_value(14400.0)  # 4 hours

        mock_coordinator.set_manual_control_timeout.assert_called_once_with(14400)

    @pytest.mark.asyncio
    async def test_minimum_timeout_5_minutes(self, entity, mock_coordinator):
        """SCENARIO: User wants very fast auto-restore (bathroom break timeout)

        EXPECTED: Sets timeout to 300s (5 minutes, min)
        WHY: Minimum timeout for quick bathroom trips
        """
        await entity.async_set_native_value(300.0)  # 5 minutes

        mock_coordinator.set_manual_control_timeout.assert_called_once_with(300)

    def test_native_value_handles_coordinator_error(self, entity, mock_coordinator):
        """SCENARIO: Coordinator fails during get

        EXPECTED: Returns 3600.0 default (1 hour)
        WHY: Dashboard needs sensible default timeout
        """
        mock_coordinator.get_manual_control_timeout.side_effect = AttributeError("Test error")

        value = entity.native_value

        assert value == 3600.0


@pytest.mark.unit
@pytest.mark.number
class TestNumberEntityErrorHandling:
    """Test error handling across all number entities."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock coordinator that raises various errors."""
        coordinator = MagicMock()
        coordinator.config_entry = MagicMock()
        coordinator.config_entry.entry_id = "test_entry"

        # All getters raise errors (only AttributeError and KeyError are caught)
        coordinator.get_brightness_adjustment = MagicMock(side_effect=AttributeError("Test error"))
        coordinator.get_warmth_adjustment = MagicMock(side_effect=KeyError("Test error"))
        coordinator.get_brightness_increment = MagicMock(side_effect=AttributeError("Test error"))
        coordinator.get_color_temp_increment = MagicMock(side_effect=KeyError("Test error"))
        coordinator.get_manual_control_timeout = MagicMock(side_effect=AttributeError("Test error"))

        # All setters raise errors
        coordinator.set_brightness_adjustment = AsyncMock(side_effect=RuntimeError("Set error"))
        coordinator.set_warmth_adjustment = AsyncMock(side_effect=RuntimeError("Set error"))
        coordinator.set_brightness_increment = AsyncMock(side_effect=RuntimeError("Set error"))
        coordinator.set_color_temp_increment = AsyncMock(side_effect=RuntimeError("Set error"))
        coordinator.set_manual_control_timeout = AsyncMock(side_effect=RuntimeError("Set error"))

        return coordinator

    @pytest.fixture
    def mock_config_entry(self):
        """Mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        return entry

    def test_all_entities_handle_get_errors_gracefully(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Coordinator fails for all getters

        EXPECTED: All entities return sensible defaults, no crashes
        WHY: Dashboard must stay responsive even if coordinator broken
        """
        brightness_adj = ALPBrightnessAdjustmentNumber(mock_coordinator, mock_config_entry)
        warmth_adj = ALPWarmthAdjustmentNumber(mock_coordinator, mock_config_entry)
        brightness_inc = ALPBrightnessIncrementNumber(mock_coordinator, mock_config_entry)
        color_temp_inc = ALPColorTempIncrementNumber(mock_coordinator, mock_config_entry)
        manual_timeout = ALPManualTimeoutNumber(mock_coordinator, mock_config_entry)

        # All should return defaults, not raise
        assert brightness_adj.native_value == 0.0
        assert warmth_adj.native_value == 0.0
        assert brightness_inc.native_value == 10.0
        assert color_temp_inc.native_value == 500.0
        assert manual_timeout.native_value == 3600.0

    @pytest.mark.asyncio
    async def test_all_entities_propagate_set_errors(self, mock_coordinator, mock_config_entry):
        """SCENARIO: Coordinator fails for all setters

        EXPECTED: All entities re-raise errors (user needs to know change failed)
        WHY: Silent failures are worse than visible errors
        """
        brightness_adj = ALPBrightnessAdjustmentNumber(mock_coordinator, mock_config_entry)
        warmth_adj = ALPWarmthAdjustmentNumber(mock_coordinator, mock_config_entry)
        brightness_inc = ALPBrightnessIncrementNumber(mock_coordinator, mock_config_entry)
        color_temp_inc = ALPColorTempIncrementNumber(mock_coordinator, mock_config_entry)
        manual_timeout = ALPManualTimeoutNumber(mock_coordinator, mock_config_entry)

        # All should raise errors
        with pytest.raises(RuntimeError):
            await brightness_adj.async_set_native_value(25.0)

        with pytest.raises(RuntimeError):
            await warmth_adj.async_set_native_value(-500.0)

        with pytest.raises(RuntimeError):
            await brightness_inc.async_set_native_value(15.0)

        with pytest.raises(RuntimeError):
            await color_temp_inc.async_set_native_value(750.0)

        with pytest.raises(RuntimeError):
            await manual_timeout.async_set_native_value(1800.0)
