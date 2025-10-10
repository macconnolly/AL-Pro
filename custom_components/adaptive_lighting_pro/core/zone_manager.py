"""Zone management for Adaptive Lighting Pro."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Dict, Iterable, List


@dataclass
class ZoneConfig:
    zone_id: str
    al_switch: str
    lights: List[str]
    enabled: bool
    zone_multiplier: float
    sunrise_offset_min: int
    environmental_boost_enabled: bool
    sunset_boost_enabled: bool


@dataclass
class ZoneState:
    manual_active: bool = False
    manual_duration: int = 0
    manual_started: datetime | None = None
    manual_expires: datetime | None = None
    last_sync_ms: int = 0
    last_error: str | None = None


class ZoneManager:
    """Manage zone configs and runtime state."""

    def __init__(self, timer_manager) -> None:
        self._timer_manager = timer_manager
        self._zones: Dict[str, ZoneConfig] = {}
        self._states: Dict[str, ZoneState] = {}

    def load_zones(self, zones: Iterable[dict]) -> None:
        self._zones.clear()
        self._states.clear()
        for zone in zones:
            config = ZoneConfig(
                zone_id=zone["zone_id"],
                al_switch=zone["al_switch"],
                lights=list(zone["lights"]),
                enabled=bool(zone.get("enabled", True)),
                zone_multiplier=float(zone.get("zone_multiplier", 1.0)),
                sunrise_offset_min=int(zone.get("sunrise_offset_min", 0)),
                environmental_boost_enabled=bool(
                    zone.get("environmental_boost_enabled", True)
                ),
                sunset_boost_enabled=bool(zone.get("sunset_boost_enabled", True)),
            )
            self._zones[config.zone_id] = config
            self._states[config.zone_id] = ZoneState()
            self._timer_manager.configure_zone(
                config.zone_id,
                config.zone_multiplier,
                env_enabled=config.environmental_boost_enabled,
            )

    def update_zone(self, zone_id: str, **changes) -> None:
        config = self._zones[zone_id]
        for key, value in changes.items():
            setattr(config, key, value)
        self._timer_manager.configure_zone(
            zone_id,
            config.zone_multiplier,
            env_enabled=config.environmental_boost_enabled,
        )

    def set_enabled(self, zone_id: str, enabled: bool) -> None:
        self._zones[zone_id].enabled = enabled

    def get_zone(self, zone_id: str) -> ZoneConfig:
        return self._zones[zone_id]

    def zones(self) -> List[ZoneConfig]:
        return list(self._zones.values())

    def enabled_zones(self) -> List[ZoneConfig]:
        return [zone for zone in self._zones.values() if zone.enabled]

    def set_manual(
        self,
        zone_id: str,
        active: bool,
        duration: int = 0,
        *,
        started_at: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        state = self._states[zone_id]
        state.manual_active = active
        state.manual_duration = duration
        if active:
            state.manual_started = started_at or datetime.now(UTC)
            if expires_at is None:
                expires_at = state.manual_started + timedelta(seconds=max(duration, 0))
            state.manual_expires = expires_at
        else:
            state.manual_started = None
            state.manual_expires = None
        if not active:
            self._timer_manager.cancel(zone_id)

    def clear_all_manuals(self) -> List[str]:
        cleared: List[str] = []
        for zone_id, state in self._states.items():
            if state.manual_active:
                state.manual_active = False
                state.manual_duration = 0
                state.manual_started = None
                state.manual_expires = None
                self._timer_manager.cancel(zone_id)
                cleared.append(zone_id)
        return cleared

    def manual_active(self, zone_id: str) -> bool:
        return self._states[zone_id].manual_active

    def manual_remaining(self, zone_id: str) -> int:
        expires = self._states[zone_id].manual_expires
        if not expires:
            return 0
        delta = expires - datetime.now(UTC)
        return max(0, int(delta.total_seconds()))

    def update_sync_result(self, zone_id: str, duration_ms: int, error: str | None) -> None:
        state = self._states[zone_id]
        state.last_sync_ms = duration_ms
        state.last_error = error

    def sunrise_offset(self, zone_id: str) -> int:
        return self._zones[zone_id].sunrise_offset_min

    def zone_multiplier(self, zone_id: str) -> float:
        return self._zones[zone_id].zone_multiplier

    def restore_manual_state(
        self,
        zone_id: str,
        *,
        started_at: datetime | None,
        expires_at: datetime | None,
        duration: int,
    ) -> None:
        state = self._states[zone_id]
        state.manual_active = True
        state.manual_duration = duration
        state.manual_started = started_at
        state.manual_expires = expires_at

    def apply_overrides(self, overrides: Dict[str, dict]) -> None:
        for zone_id, override in overrides.items():
            if zone_id not in self._zones:
                continue
            config = self._zones[zone_id]
            if "enabled" in override:
                config.enabled = bool(override["enabled"])
            if "zone_multiplier" in override:
                config.zone_multiplier = float(override["zone_multiplier"])
            if "sunrise_offset_min" in override:
                config.sunrise_offset_min = int(override["sunrise_offset_min"])
            if "environmental_boost_enabled" in override:
                config.environmental_boost_enabled = bool(
                    override["environmental_boost_enabled"]
                )
            if "sunset_boost_enabled" in override:
                config.sunset_boost_enabled = bool(override["sunset_boost_enabled"])
            self._timer_manager.configure_zone(
                zone_id,
                config.zone_multiplier,
                env_enabled=config.environmental_boost_enabled,
            )

    def set_environmental_boost_enabled(self, zone_id: str, enabled: bool) -> bool:
        config = self._zones[zone_id]
        if config.environmental_boost_enabled == enabled:
            return False
        config.environmental_boost_enabled = enabled
        self._timer_manager.configure_zone(
            zone_id,
            config.zone_multiplier,
            env_enabled=config.environmental_boost_enabled,
        )
        return True

    def set_sunset_boost_enabled(self, zone_id: str, enabled: bool) -> bool:
        config = self._zones[zone_id]
        if config.sunset_boost_enabled == enabled:
            return False
        config.sunset_boost_enabled = enabled
        return True

    def manual_state_snapshot(self) -> Dict[str, dict]:
        snapshot: Dict[str, dict] = {}
        for zone_id, config in self._zones.items():
            state = self._states[zone_id]
            snapshot[zone_id] = {
                "manual_active": state.manual_active,
                "manual_duration": state.manual_duration,
                "manual_started": state.manual_started.isoformat()
                if state.manual_started
                else None,
                "manual_expires": state.manual_expires.isoformat()
                if state.manual_expires
                else None,
                "timer_remaining": self.manual_remaining(zone_id),
                "environmental_boost_enabled": config.environmental_boost_enabled,
                "sunset_boost_enabled": config.sunset_boost_enabled,
            }
        return snapshot

    def as_dict(self) -> Dict[str, dict]:
        result: Dict[str, dict] = {}
        for zone in self._zones.values():
            state = self._states[zone.zone_id]
            result[zone.zone_id] = {
                "al_switch": zone.al_switch,
                "lights": list(zone.lights),
                "enabled": zone.enabled,
                "zone_multiplier": zone.zone_multiplier,
                "sunrise_offset_min": zone.sunrise_offset_min,
                "environmental_boost_enabled": zone.environmental_boost_enabled,
                "sunset_boost_enabled": zone.sunset_boost_enabled,
                "manual_active": state.manual_active,
                "manual_duration": state.manual_duration,
                "manual_started": state.manual_started,
                "manual_expires": state.manual_expires,
                "timer_remaining": self.manual_remaining(zone.zone_id),
                "last_sync_ms": state.last_sync_ms,
                "last_error": state.last_error,
            }
        return result
