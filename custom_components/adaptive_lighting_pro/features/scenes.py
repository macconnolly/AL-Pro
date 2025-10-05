"""Scene management for Adaptive Lighting Pro."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from ..const import EVENT_MANUAL_DETECTED, EVENT_SCENE_CHANGED, SYNC_TRANSITION_SEC
from ..utils.logger import log_debug


@dataclass
class SceneConfig:
    order: List[str]
    force_apply: bool
    debug: bool
    presets: Dict[str, Dict[str, Any]]
    user_offsets: Dict[str, int]
    offsets_callback: Callable[[int, int], None] = field(
        default=lambda _brightness, _warmth: None
    )
    manual_action_callback: Callable[[str], None] = field(default=lambda _action: None)


SCENE_GROUPS = {
    "all_lights": ("turn_on", "group.all_lights"),
    "no_spots": ("turn_off", "group.no_spots"),
}


class SceneManager:
    def __init__(
        self,
        hass,
        event_bus,
        executors,
        zone_manager,
        timer_manager,
        config: SceneConfig,
    ) -> None:
        self._hass = hass
        self._event_bus = event_bus
        self._executors = executors
        self._zone_manager = zone_manager
        self._timer_manager = timer_manager
        self._config = config
        self._order = list(config.order) or ["default"]
        self._scene = self._order[0]
        self._presets: Dict[str, Dict[str, Any]] = {
            key: dict(value) for key, value in config.presets.items()
        }
        self._offsets: Dict[str, int] = {"brightness": 0, "warmth": 0}
        self._user_offsets: Dict[str, int] = {
            "brightness": int(config.user_offsets.get("brightness", 0)),
            "warmth": int(config.user_offsets.get("warmth", 0)),
        }
        active = self._presets.get(self._scene, {})
        offsets = self._combine_offsets(
            active.get("offsets", {}), self._user_offsets
        )
        self.set_offsets(offsets["brightness"], offsets["warmth"])

    @property
    def scene(self) -> str:
        return self._scene

    def available(self) -> List[str]:
        """Return configured scene identifiers in order."""

        return list(self._order)

    def offsets(self) -> Dict[str, int]:
        return dict(self._offsets)

    def update_order(self, order: List[str]) -> None:
        self._order = list(order) or ["default"]
        if self._scene not in self._order:
            self._scene = self._order[0]

    def update_presets(self, presets: Dict[str, Dict[str, Any]]) -> None:
        self._presets = {key: dict(value) for key, value in presets.items()}
        self.update_user_offsets(
            self._user_offsets["brightness"], self._user_offsets["warmth"]
        )

    def set_offsets(self, brightness: int, warmth: int) -> None:
        brightness = int(brightness)
        warmth = int(warmth)
        if (
            self._offsets["brightness"] == brightness
            and self._offsets["warmth"] == warmth
        ):
            return
        self._offsets["brightness"] = brightness
        self._offsets["warmth"] = warmth
        self._config.offsets_callback(brightness, warmth)
        self._dispatch_manual_actions(brightness, warmth)

    def update_user_offsets(self, brightness: int, warmth: int) -> None:
        brightness = int(brightness)
        warmth = int(warmth)
        combined = self._combine_offsets(
            self._presets.get(self._scene, {}).get("offsets", {}),
            {"brightness": brightness, "warmth": warmth},
        )
        if (
            self._user_offsets["brightness"] == brightness
            and self._user_offsets["warmth"] == warmth
            and self._offsets == combined
        ):
            return
        self._user_offsets = {"brightness": brightness, "warmth": warmth}
        self.set_offsets(combined["brightness"], combined["warmth"])

    async def select(self, scene: str) -> None:
        if scene not in self._order:
            raise ValueError(f"Unknown scene {scene}")
        self._scene = scene
        await self._apply(scene)
        self._event_bus.post(EVENT_SCENE_CHANGED, scene=scene)

    async def cycle(self) -> None:
        if not self._order:
            return
        idx = self._order.index(self._scene)
        scene = self._order[(idx + 1) % len(self._order)]
        await self.select(scene)

    async def _apply(self, scene: str) -> None:
        preset = self._presets.get(scene, {})
        combined_offsets = self._combine_offsets(preset.get("offsets", {}))
        self.set_offsets(combined_offsets["brightness"], combined_offsets["warmth"])

        if scene in SCENE_GROUPS:
            service, entity_id = SCENE_GROUPS[scene]
            await self._executors.call_light_service(service, {"entity_id": entity_id})

        await self._execute_actions(preset.get("actions", []))

        for zone in self._zone_manager.enabled_zones():
            if self._zone_manager.manual_active(zone.zone_id):
                log_debug(
                    self._config.debug,
                    "Skipping scene %s for zone %s due to manual override",
                    scene,
                    zone.zone_id,
                )
                continue
            data = {
                "transition": preset.get("transition", SYNC_TRANSITION_SEC),
                "lights": zone.lights,
                "force": self._config.force_apply,
                "turn_on_lights": preset.get("turn_on_lights", True),
                "context": {
                    "source": "alp_scene",
                    "scene": scene,
                    "zone": zone.zone_id,
                    "scene_offsets": dict(self._offsets),
                    "scene_user_offsets": dict(self._user_offsets),
                },
            }
            manual_scene = bool(preset.get("manual", scene != "default"))
            if manual_scene:
                duration = self._timer_manager.compute_duration_seconds(zone.zone_id)
                self._event_bus.post(
                    EVENT_MANUAL_DETECTED,
                    zone=zone.zone_id,
                    duration_s=duration,
                )
                data["context"]["manual_duration_s"] = duration

            brightness = preset.get("brightness_pct")
            if brightness is not None:
                brightness = self._clamp(
                    int(brightness) + self._offsets["brightness"], 1, 100
                )
                data["brightness_pct"] = brightness
                data["adapt_brightness"] = False
                data["context"]["brightness_pct"] = brightness
            else:
                adapt_brightness = bool(preset.get("adapt_brightness", False))
                data["adapt_brightness"] = adapt_brightness or scene == "default"

            color_temp = preset.get("color_temp_kelvin")
            if color_temp is not None:
                color_temp = self._clamp(
                    int(color_temp) + self._offsets["warmth"], 1800, 6500
                )
                data["color_temp_kelvin"] = color_temp
                data["adapt_color_temp"] = False
                data["context"]["color_temp_kelvin"] = color_temp
            else:
                adapt_color = bool(preset.get("adapt_color_temp", False))
                data["adapt_color_temp"] = adapt_color or scene == "default"

            extras = {
                key: value
                for key, value in preset.items()
                if key
                not in {
                    "brightness_pct",
                    "color_temp_kelvin",
                    "adapt_brightness",
                    "adapt_color_temp",
                    "manual",
                    "actions",
                    "offsets",
                    "transition",
                }
            }
            if extras:
                data.update(extras)
            await self._executors.apply(zone.al_switch, data)

    def _combine_offsets(
        self, offsets: Dict[str, Any], user_overrides: Dict[str, int] | None = None
    ) -> Dict[str, int]:
        base_brightness = int(offsets.get("brightness", 0))
        base_warmth = int(offsets.get("warmth", 0))
        user = user_overrides or self._user_offsets
        return {
            "brightness": base_brightness + int(user.get("brightness", 0)),
            "warmth": base_warmth + int(user.get("warmth", 0)),
        }

    async def _execute_actions(self, actions: List[Dict[str, Any]]) -> None:
        for action in actions or []:
            service = action.get("service")
            if not service or "." not in service:
                continue
            domain, _, service_name = service.partition(".")
            if domain != "light":
                log_debug(
                    self._config.debug,
                    "Scene action %s ignored; unsupported domain",
                    service,
                )
                continue
            payload = dict(action.get("data", {}))
            await self._executors.call_light_service(service_name, payload)

    def _dispatch_manual_actions(self, brightness: int, warmth: int) -> None:
        if brightness > 0:
            self._config.manual_action_callback("brighter")
        elif brightness < 0:
            self._config.manual_action_callback("dimmer")
        else:
            self._config.manual_action_callback("clear_brightness")

        if warmth < 0:
            self._config.manual_action_callback("warmer")
        elif warmth > 0:
            self._config.manual_action_callback("cooler")
        else:
            self._config.manual_action_callback("clear_warmth")

    @staticmethod
    def _clamp(value: int, lower: int, upper: int) -> int:
        return max(lower, min(upper, value))
