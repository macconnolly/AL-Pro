"""Synchronization coordinator."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .analytics import AnalyticsSuite
from .environment import EnvironmentManager
from .manual import ManualIntentManager
from .mode import ModeManager
from .models import (
    EnvironmentState,
    LayerUpdate,
    ModeProfile,
    ModeState,
    OverrideState,
    ZoneComputation,
    ZoneModel,
)


ENV_LAYER_PRIORITY = 20
MODE_LAYER_PRIORITY = 30
MANUAL_LAYER_PRIORITY = 40


class SyncCoordinator:
    """Combines manual, environmental, and adaptive targets."""

    def __init__(
        self,
        manual_manager: ManualIntentManager,
        environment_manager: EnvironmentManager,
        mode_manager: ModeManager,
        analytics: Optional[AnalyticsSuite] = None,
    ) -> None:
        self.manual_manager = manual_manager
        self.environment_manager = environment_manager
        self.mode_manager = mode_manager
        self.analytics = analytics or AnalyticsSuite()
        self._last_computations: Dict[str, ZoneComputation] = {}

    def compute(self, zone: ZoneModel, now: datetime) -> ZoneComputation:
        manual_state = self.manual_manager.get_override(zone.zone_id, now)
        env_state = self.environment_manager.get_state(zone.zone_id) or EnvironmentState(zone.zone_id)
        mode_state = self.mode_manager.get_state()

        base_brightness = zone.default_brightness
        base_kelvin = zone.default_kelvin
        details: Dict[str, float] = {
            "base_brightness": base_brightness,
            "base_kelvin": float(base_kelvin),
        }

        layers: list[LayerUpdate] = []
        current_brightness = base_brightness
        current_kelvin = base_kelvin
        transition = 2
        source = "adaptive"

        if env_state.active_profiles:
            current_brightness = zone.clamp(base_brightness + env_state.brightness_offset)
            current_kelvin = zone.environment.apply_bounds(base_kelvin + env_state.kelvin_offset)
            details["environment_brightness"] = env_state.brightness_offset
            details["environment_kelvin"] = float(env_state.kelvin_offset)
            layers.append(
                LayerUpdate(
                    layer_id=f"{zone.zone_id}_environment",
                    priority=ENV_LAYER_PRIORITY,
                    brightness=current_brightness,
                    kelvin=current_kelvin,
                    transition=transition,
                    reason="environment",
                )
            )
            source = "environment"

        if mode_state.active_mode:
            mode_profile = mode_state.profile
            current_brightness = zone.clamp(current_brightness * mode_profile.brightness_multiplier)
            current_kelvin = zone.environment.apply_bounds(current_kelvin + mode_profile.kelvin_adjustment)
            details["mode"] = mode_profile.brightness_multiplier
            details["mode_kelvin"] = float(mode_profile.kelvin_adjustment)
            transition = max(transition, mode_profile.transition_seconds)
            layers.append(
                LayerUpdate(
                    layer_id=f"{zone.zone_id}_mode",
                    priority=MODE_LAYER_PRIORITY,
                    brightness=current_brightness,
                    kelvin=current_kelvin,
                    transition=mode_profile.transition_seconds,
                    reason=mode_state.active_mode,
                )
            )
            source = f"mode:{mode_state.active_mode}"

        if manual_state:
            target_brightness = zone.clamp(manual_state.brightness)
            if manual_state.brightness > current_brightness:
                target_brightness = min(target_brightness, current_brightness + zone.manual.max_extra_brightness)
            current_brightness = target_brightness
            current_kelvin = manual_state.kelvin
            transition = 1
            details["manual_remaining"] = manual_state.remaining_seconds(now)
            layers.append(
                LayerUpdate(
                    layer_id=f"{zone.zone_id}_manual",
                    priority=MANUAL_LAYER_PRIORITY,
                    brightness=current_brightness,
                    kelvin=current_kelvin,
                    transition=transition,
                    reason=manual_state.reason,
                )
            )
            source = f"manual:{manual_state.reason}"
        else:
            transition = max(transition, 2)

        computation = ZoneComputation(
            zone_id=zone.zone_id,
            brightness=round(current_brightness, 3),
            kelvin=int(current_kelvin),
            source=source,
            transition=transition,
            layers=layers,
            details=details,
        )
        self._last_computations[zone.zone_id] = computation
        self.analytics.increment("sync_success")
        return computation

    def last_computation(self, zone_id: str) -> Optional[ZoneComputation]:
        return self._last_computations.get(zone_id)

    def reconcile_manual_decay(self, zone: ZoneModel, now: datetime) -> Optional[OverrideState]:
        target = zone.default_brightness
        env_state = self.environment_manager.get_state(zone.zone_id)
        if env_state:
            target = zone.clamp(target + env_state.brightness_offset)
        return self.manual_manager.decay_brightness(zone.zone_id, now, target)

    def apply_mode(self, mode: str, profile: ModeProfile) -> ZoneComputation:
        state = self.mode_manager.set_mode(mode, profile)
        last = self._last_computations.get(state.active_mode or "")
        if last:
            self.analytics.increment("mode_switch")
        return last if last else ZoneComputation("*", 0.0, 0, "mode", profile.transition_seconds)

    def clear_mode(self, mode: str) -> None:
        self.mode_manager.clear_mode(mode)
        self.analytics.increment("mode_clear")
