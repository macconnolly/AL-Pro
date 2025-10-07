"""Zen32 Scene Controller Integration for Adaptive Lighting Pro.

Provides physical button control via Zooz Zen32 Z-Wave scene controller.

Button Mapping (configurable):
- Button 1: Cycle scenes
- Button 2: Brighter (+increment)
- Button 3: Reset manual adjustments (press) / Nuclear reset (hold)
- Button 4: Dimmer (-increment)
- Button 5: Toggle all lights (handled outside ALP, no adaptive control)

Technical Details:
- Listens to event entities (event.scene_controller_scene_001, etc.)
- Event attributes contain event_type: "KeyPressed" or "KeyHeldDown"
- Per-button debouncing (default 0.5s) prevents duplicate triggers
- Calls coordinator services for all actions
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Callable

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from ..const import DOMAIN

if TYPE_CHECKING:
    from ..coordinator import ALPDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class Zen32Integration:
    """Integration for Zooz Zen32 scene controller physical button control.

    Monitors Z-Wave event entities and translates button presses into
    coordinator service calls (brighter, dimmer, cycle_scene, reset).

    Architecture:
    - Each button is an event entity that updates when pressed
    - Event attributes contain event_type (KeyPressed/KeyHeldDown)
    - Per-button debouncing prevents rapid duplicate presses
    - All actions go through coordinator services for consistency
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ALPDataUpdateCoordinator,
    ) -> None:
        """Initialize Zen32 integration.

        Args:
            hass: Home Assistant instance
            coordinator: Coordinator for reading state and calling services
        """
        self.hass = hass
        self._coordinator = coordinator

        # Configuration
        self._enabled = False
        self._button_entities: dict[str, str] = {}  # button_id -> entity_id
        self._button_actions: dict[str, str] = {}  # button_id -> action_name
        self._debounce_duration = 0.5  # seconds

        # State tracking
        self._last_button_press: dict[str, float] = {}  # button_id -> timestamp
        self._listeners: list[Callable] = []

    def configure(
        self,
        enabled: bool,
        button_entities: dict[str, str],
        button_actions: dict[str, str],
        debounce_duration: float = 0.5,
    ) -> None:
        """Configure Zen32 integration.

        Args:
            enabled: Whether integration is enabled
            button_entities: Mapping of button_id to event entity_id
            button_actions: Mapping of button_id to action name
            debounce_duration: Minimum seconds between button presses

        Example:
            button_entities = {
                "button_1": "event.scene_controller_scene_001",
                "button_2": "event.scene_controller_scene_002",
                ...
            }
            button_actions = {
                "button_1": "cycle_scene",
                "button_2": "brighter",
                "button_3": "reset_manual",
                "button_4": "dimmer",
                "button_5": "none",  # Toggle handled elsewhere
            }
        """
        self._enabled = enabled
        self._button_entities = button_entities
        self._button_actions = button_actions
        self._debounce_duration = debounce_duration

        _LOGGER.debug(
            "Zen32 integration configured: enabled=%s, buttons=%d, debounce=%.2fs",
            enabled,
            len(button_entities),
            debounce_duration,
        )

    async def async_setup(self) -> bool:
        """Set up Zen32 event listeners.

        Defers actual listener setup until HA has fully started to ensure
        all event entities are available.

        Returns:
            True if setup initiated, False if disabled or no buttons configured
        """
        if not self._enabled:
            _LOGGER.info("Zen32 integration disabled")
            return False

        if not self._button_entities:
            _LOGGER.warning("Zen32 integration enabled but no buttons configured")
            return False

        _LOGGER.info(
            "Zen32 integration: Waiting for Home Assistant to start before monitoring %d buttons",
            len(self._button_entities),
        )

        # Wait for HA to fully start before setting up listeners
        # Event entities may not be ready during initial integration setup
        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            self._async_setup_listeners,
        )

        return True

    @callback
    async def _async_setup_listeners(self, event: Event) -> None:
        """Set up button event listeners after HA has started.

        Args:
            event: Home Assistant started event
        """
        _LOGGER.info("Zen32 integration: Home Assistant started, setting up button listeners")

        # Verify all button entities exist
        missing_entities = []
        for button_id, entity_id in self._button_entities.items():
            if not self.hass.states.get(entity_id):
                missing_entities.append(entity_id)

        if missing_entities:
            _LOGGER.error(
                "Zen32 integration: %d button entities not found: %s",
                len(missing_entities),
                missing_entities,
            )
            return

        # Register event listeners for each button
        for button_id, entity_id in self._button_entities.items():
            # Create a proper async callback wrapper for each button
            async def async_button_callback(event: Event, button_id: str = button_id) -> None:
                """Async wrapper for button event handler."""
                await self._button_event_handler(event, button_id)

            listener = async_track_state_change_event(
                self.hass,
                [entity_id],
                async_button_callback,
            )
            self._listeners.append(listener)
            _LOGGER.debug("Zen32: Registered listener for %s (%s)", button_id, entity_id)

        _LOGGER.info(
            "Zen32 integration setup complete: monitoring %d buttons",
            len(self._button_entities),
        )


    async def async_shutdown(self) -> None:
        """Shutdown Zen32 integration and remove event listeners."""
        for listener in self._listeners:
            listener()

        self._listeners.clear()
        _LOGGER.info("Zen32 integration shut down")

    def _is_debounced(self, button_id: str) -> bool:
        """Check if button press is debounced (too soon after last press).

        Args:
            button_id: Button identifier

        Returns:
            True if debounced (should ignore), False if OK to process
        """
        now = time.time()
        last_press = self._last_button_press.get(button_id, 0)
        time_since_last = now - last_press

        if time_since_last < self._debounce_duration:
            _LOGGER.debug(
                "Zen32: %s debounced (%.2fs since last press)",
                button_id,
                time_since_last,
            )
            return True

        self._last_button_press[button_id] = now
        return False

    async def _button_event_handler(self, event: Event, button_id: str) -> None:
        """Handle button event from Zen32.

        Args:
            event: State change event from event entity
            button_id: Which button triggered this event
        """
        new_state = event.data.get("new_state")

        if not new_state:
            _LOGGER.debug("Zen32: %s event has no new_state, ignoring", button_id)
            return

        # DEBUG: Log full event structure
        _LOGGER.info(
            "Zen32: %s received event - state=%s, attributes=%s",
            button_id,
            new_state.state,
            new_state.attributes,
        )

        # Check debounce
        if self._is_debounced(button_id):
            return

        # Get event type from attributes
        event_type = new_state.attributes.get("event_type")
        if event_type not in ["KeyPressed", "KeyHeldDown"]:
            _LOGGER.warning(
                "Zen32: %s has unknown event_type '%s' (expected KeyPressed or KeyHeldDown), ignoring",
                button_id,
                event_type,
            )
            return

        _LOGGER.info(
            "Zen32: %s %s detected",
            button_id,
            event_type,
        )

        # Execute button action
        await self._execute_button_action(button_id, event_type)

    async def _execute_button_action(self, button_id: str, event_type: str) -> None:
        """Execute the configured action for a button press.

        Args:
            button_id: Which button was pressed
            event_type: "KeyPressed" or "KeyHeldDown"
        """
        action = self._button_actions.get(button_id)

        # Special handling for button_5 (Center button) - direct light control
        # Press = Turn ON all lights, Hold = Turn OFF all lights
        if button_id == "button_5":
            try:
                if event_type == "KeyPressed":
                    await self._action_lights_on()
                elif event_type == "KeyHeldDown":
                    await self._action_lights_off()
                return
            except Exception as err:
                _LOGGER.error("Zen32: Error controlling lights from button_5: %s", err)
                return

        if not action or action == "none":
            _LOGGER.debug("Zen32: %s has no action configured", button_id)
            return

        try:
            if action == "brighter":
                await self._action_brighter()
            elif action == "dimmer":
                await self._action_dimmer()
            elif action == "cycle_scene":
                await self._action_cycle_scene()
            elif action == "reset_manual":
                # Press = reset manual adjustments, Hold = nuclear reset all
                if event_type == "KeyPressed":
                    await self._action_reset_manual_adjustments()
                elif event_type == "KeyHeldDown":
                    await self._action_reset_all()
            else:
                _LOGGER.warning("Zen32: %s has unknown action '%s'", button_id, action)

        except Exception as err:
            _LOGGER.error(
                "Zen32: Error executing action '%s' for %s: %s",
                action,
                button_id,
                err,
            )

    async def _action_brighter(self) -> None:
        """Execute brighter action (increment brightness adjustment)."""
        current = self._coordinator.get_brightness_adjustment()
        increment = self._coordinator.get_brightness_increment()
        new_value = min(100, current + increment)

        _LOGGER.info(
            "Zen32: Brighter - current=%d, increment=%d, new=%d",
            current,
            increment,
            new_value,
        )

        await self.hass.services.async_call(
            DOMAIN,
            "adjust_brightness",
            {"value": new_value},
        )

    async def _action_dimmer(self) -> None:
        """Execute dimmer action (decrement brightness adjustment)."""
        current = self._coordinator.get_brightness_adjustment()
        increment = self._coordinator.get_brightness_increment()
        new_value = max(-100, current - increment)

        _LOGGER.info(
            "Zen32: Dimmer - current=%d, increment=%d, new=%d",
            current,
            increment,
            new_value,
        )

        await self.hass.services.async_call(
            DOMAIN,
            "adjust_brightness",
            {"value": new_value},
        )

    async def _action_cycle_scene(self) -> None:
        """Execute cycle scene action."""
        _LOGGER.info("Zen32: Cycling scene")

        await self.hass.services.async_call(
            DOMAIN,
            "cycle_scene",
            {},
        )

    async def _action_reset_manual_adjustments(self) -> None:
        """Execute reset manual adjustments action (Button 3 press)."""
        _LOGGER.info("Zen32: Resetting manual adjustments (brightness/warmth to 0)")

        await self.hass.services.async_call(
            DOMAIN,
            "reset_manual_adjustments",
            {},
        )

    async def _action_reset_all(self) -> None:
        """Execute nuclear reset all action (Button 3 hold)."""
        _LOGGER.info("Zen32: Nuclear reset - clearing ALL manual control and timers")

        await self.hass.services.async_call(
            DOMAIN,
            "reset_all",
            {},
        )

    async def _action_lights_on(self) -> None:
        """Turn on all adaptive lights (Button 5 press)."""
        _LOGGER.info("Zen32: Button 5 press - turning ON all lights")

        # Get all light entities from coordinator zones
        all_lights = []
        for zone_config in self._coordinator.zones.values():
            lights = zone_config.get("lights", [])
            all_lights.extend(lights)

        if all_lights:
            await self.hass.services.async_call(
                "light",
                "turn_on",
                {"entity_id": all_lights},
            )
            _LOGGER.debug("Zen32: Turned on %d lights", len(all_lights))

    async def _action_lights_off(self) -> None:
        """Turn off all adaptive lights (Button 5 hold)."""
        _LOGGER.info("Zen32: Button 5 hold - turning OFF all lights")

        # Get all light entities from coordinator zones
        all_lights = []
        for zone_config in self._coordinator.zones.values():
            lights = zone_config.get("lights", [])
            all_lights.extend(lights)

        if all_lights:
            await self.hass.services.async_call(
                "light",
                "turn_off",
                {"entity_id": all_lights},
            )
            _LOGGER.debug("Zen32: Turned off %d lights", len(all_lights))

    def get_status(self) -> dict[str, Any]:
        """Get current Zen32 integration status.

        Returns:
            Status dictionary with configuration and state
        """
        return {
            "enabled": self._enabled,
            "buttons_configured": len(self._button_entities),
            "listeners_active": len(self._listeners),
            "debounce_duration": self._debounce_duration,
            "button_entities": dict(self._button_entities),
            "button_actions": dict(self._button_actions),
        }
