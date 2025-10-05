"""Button platform for Adaptive Lighting Pro.

Provides quick-action buttons for common lighting adjustments.

Following claude.md: "This is YOUR home. You live here."

Button Categories:
- Adjustment: brighter/dimmer/warmer/cooler (±10%, ±500K)
- Reset: Reset adjustments to baseline (the "fix it" button)
- Scenes: One-tap scene triggers (evening comfort, movie mode, etc.)

Design Philosophy:
- Buttons are faster than sliders for common adjustments
- Fixed increments prevent decision paralysis ("a bit brighter" not "23% brighter")
- Idempotent at boundaries (safe to spam buttons)
- Scene buttons layer cleanly with manual adjustments
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import (
    DOMAIN,
    SERVICE_RESET_MANUAL_ADJUSTMENTS,
    Scene,
)
from .entity import ALPEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from ..coordinator import ALPDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ALP button platform from config entry."""
    # Get coordinator from hass.data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]

    # Handle both dict storage (new) and direct coordinator (legacy)
    coordinator = (
        entry_data["coordinator"] if isinstance(entry_data, dict) else entry_data
    )

    buttons = []

    # Adjustment buttons (5 buttons)
    buttons.extend([
        ALPBrighterButton(coordinator, config_entry),
        ALPDimmerButton(coordinator, config_entry),
        ALPWarmerButton(coordinator, config_entry),
        ALPCoolerButton(coordinator, config_entry),
        ALPResetButton(coordinator, config_entry, hass),
    ])

    # Scene buttons (4 buttons)
    scene_buttons = [
        (Scene.ALL_LIGHTS, "All Lights", "mdi:lightbulb-group"),
        (Scene.NO_SPOTLIGHTS, "No Spotlights", "mdi:book-open-variant"),
        (Scene.EVENING_COMFORT, "Evening Comfort", "mdi:weather-sunset-down"),
        (Scene.ULTRA_DIM, "Ultra Dim", "mdi:movie-open"),
    ]

    for scene, name, icon in scene_buttons:
        buttons.append(ALPSceneButton(coordinator, config_entry, scene, name, icon))

    async_add_entities(buttons)


class ALPButton(ALPEntity, ButtonEntity):
    """Base button class for ALP using ALPEntity pattern.

    This is YOUR lighting system. Buttons should be:
    - Instant (no lag)
    - Idempotent (safe to press repeatedly)
    - Predictable (same action every time)
    """

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        config_entry: ConfigEntry,
        button_id: str,
        name: str,
    ) -> None:
        """Initialize ALP button.

        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            button_id: Unique identifier for button (e.g., "brighter")
            name: Human-readable name (e.g., "Brighter")
        """
        super().__init__(
            coordinator,
            config_entry,
            "button",
            button_id,
            name,
        )

    async def async_press(self) -> None:
        """Handle button press - override in subclasses."""
        raise NotImplementedError


# ==================== ADJUSTMENT BUTTONS ====================


class ALPBrighterButton(ALPButton):
    """Increase brightness by configured increment.

    SCENARIO: Video call in 30 seconds, need more light NOW
    WHY: Faster than dragging slider, muscle memory develops
    """

    _attr_icon = "mdi:brightness-plus"

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize brighter button."""
        super().__init__(coordinator, config_entry, "brighter", "Brighter")

    async def async_press(self) -> None:
        """Increase brightness by configured increment, cap at +50%."""
        current = self.coordinator.get_brightness_adjustment()
        increment = self.coordinator.get_brightness_increment()
        new_value = min(current + increment, 50)  # Idempotent at max

        # Buttons are temporary overrides - start manual timers
        await self.coordinator.set_brightness_adjustment(new_value, start_timers=True)


class ALPDimmerButton(ALPButton):
    """Decrease brightness by configured increment.

    SCENARIO: Lights too bright for TV watching
    WHY: Quick tap vs slider drag when hands are full
    """

    _attr_icon = "mdi:brightness-minus"

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize dimmer button."""
        super().__init__(coordinator, config_entry, "dimmer", "Dimmer")

    async def async_press(self) -> None:
        """Decrease brightness by configured increment, cap at -50%."""
        current = self.coordinator.get_brightness_adjustment()
        increment = self.coordinator.get_brightness_increment()
        new_value = max(current - increment, -50)  # Idempotent at min

        # Buttons are temporary overrides - start manual timers
        await self.coordinator.set_brightness_adjustment(new_value, start_timers=True)


class ALPWarmerButton(ALPButton):
    """Decrease color temperature by configured increment (warmer).

    SCENARIO: Evening wind-down, lights feel too blue/cool
    WHY: Natural warmth promotes relaxation
    """

    _attr_icon = "mdi:thermometer-minus"

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize warmer button."""
        super().__init__(coordinator, config_entry, "warmer", "Warmer")

    async def async_press(self) -> None:
        """Decrease warmth by configured increment, cap at -3000K."""
        current = self.coordinator.get_warmth_adjustment()
        increment = self.coordinator.get_color_temp_increment()
        new_value = max(current - increment, -3000)  # Lower K = warmer

        # Buttons are temporary overrides - start manual timers
        await self.coordinator.set_warmth_adjustment(new_value, start_timers=True)


class ALPCoolerButton(ALPButton):
    """Increase color temperature by configured increment (cooler).

    SCENARIO: Morning alertness, need crisp white light
    WHY: Cool light promotes focus and energy
    """

    _attr_icon = "mdi:thermometer-plus"

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize cooler button."""
        super().__init__(coordinator, config_entry, "cooler", "Cooler")

    async def async_press(self) -> None:
        """Increase warmth by configured increment, cap at +3000K."""
        current = self.coordinator.get_warmth_adjustment()
        increment = self.coordinator.get_color_temp_increment()
        new_value = min(current + increment, 3000)  # Higher K = cooler

        # Buttons are temporary overrides - start manual timers
        await self.coordinator.set_warmth_adjustment(new_value, start_timers=True)


class ALPResetButton(ALPButton):
    """Reset all manual adjustments to baseline.

    SCENARIO: Kids mashed buttons, lights are chaos - "Just make it normal!"
    WHY: The "I broke it, fix it" button every smart home needs

    This button saves marriages and sanity.
    """

    _attr_icon = "mdi:refresh"

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        config_entry: ConfigEntry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize reset button."""
        super().__init__(coordinator, config_entry, "reset", "Reset")
        self.hass = hass

    async def async_press(self) -> None:
        """Reset adjustments by calling existing service.

        Why use service instead of coordinator methods?
        - Logic already exists in services.py (DRY principle)
        - Properly logged and error-handled
        - Sets both brightness AND warmth to 0
        - Buttons are UI triggers, not logic containers
        """
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_RESET_MANUAL_ADJUSTMENTS,
            blocking=True,
        )


# ==================== SCENE BUTTONS ====================


class ALPSceneButton(ALPButton):
    """Trigger a lighting scene.

    From claude.md: "Relaxation is one button press"

    Scenes are NOT modes - they're convenient shortcuts for common adjustments.
    They apply offsets, execute actions, then get out of the way.
    """

    def __init__(
        self,
        coordinator: ALPDataUpdateCoordinator,
        config_entry: ConfigEntry,
        scene: Scene,
        scene_name: str,
        icon: str,
    ) -> None:
        """Initialize scene button.

        Args:
            coordinator: Data update coordinator
            config_entry: Config entry
            scene: Scene enum value
            scene_name: Human-readable scene name
            icon: MDI icon name
        """
        button_id = f"scene_{scene.value}"
        super().__init__(coordinator, config_entry, button_id, f"Scene: {scene_name}")
        self._scene = scene
        self._attr_icon = icon

    async def async_press(self) -> None:
        """Apply the scene.

        Scene application:
        1. Executes scene actions (turn on/off zones, etc.)
        2. Applies brightness/warmth offsets
        3. Starts manual timers for affected zones
        4. System continues adapting within new boundaries

        This is what makes scenes work WITH adaptation, not against it.
        """
        await self.coordinator.apply_scene(self._scene)
