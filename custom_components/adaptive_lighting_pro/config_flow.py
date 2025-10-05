"""Config flow for Adaptive Lighting Pro."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

import voluptuous as vol

from homeassistant import config_entries

try:  # pragma: no cover - compatibility shim for tests without HA selector helper
    from homeassistant.helpers import selector
except ImportError:  # pragma: no cover - fallback for lightweight test harness
    class _SelectorModule:
        class EntitySelectorConfig(dict):
            def __init__(self, **kwargs) -> None:
                super().__init__(**kwargs)

        class EntitySelector:
            def __init__(self, config: dict | None = None) -> None:
                self.config = config or {}

            def __call__(self, value: Any) -> Any:
                return value

        class DeviceSelectorConfig(dict):
            def __init__(self, **kwargs) -> None:
                super().__init__(**kwargs)

        class DeviceSelector:
            def __init__(self, config: dict | None = None) -> None:
                self.config = config or {}

            def __call__(self, value: Any) -> Any:
                return value

    selector = _SelectorModule()

from .const import (
    CONF_CONTROLLERS,
    CONF_DEBUG,
    CONF_ENV_BOOST,
    CONF_INSTALLATION_ID,
    CONF_LUX_SENSOR,
    CONF_NIGHTLY_SWEEP,
    CONF_RATE_LIMIT,
    CONF_SENSORS,
    CONF_SONOS_SENSOR,
    CONF_TIMEOUTS,
    CONF_WEATHER_ENTITY,
    CONF_WATCHDOG,
    CONF_ZEN32_DEVICE,
    CONF_ZONES,
    DEFAULT_DEBUG_CONFIG,
    DEFAULT_ENV_MULTIPLIER_BOOST,
    DEFAULT_NIGHTLY_SWEEP_TIME,
    DEFAULT_RATE_LIMIT_MAX_EVENTS,
    DEFAULT_RATE_LIMIT_WINDOW,
    DEFAULT_WATCHDOG_INTERVAL_MIN,
    DOMAIN,
)
from .utils.validators import ValidationError, validate_zone_config

ZONES_SCHEMA = vol.Schema(
    {
        vol.Required("zone_id"): str,
        vol.Required("al_switch"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="switch")
        ),
        vol.Required("lights"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="light", multiple=True)
        ),
        vol.Optional("enabled", default=True): bool,
        vol.Optional("zone_multiplier", default=1.0): float,
        vol.Optional("sunrise_offset_min", default=0): int,
        vol.Optional("environmental_boost_enabled", default=True): bool,
        vol.Optional("sunset_boost_enabled", default=True): bool,
    }
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONES): [ZONES_SCHEMA],
        vol.Optional(CONF_LUX_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="weather")
        ),
        vol.Optional(CONF_SONOS_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_ZEN32_DEVICE): selector.DeviceSelector(
            selector.DeviceSelectorConfig(integration="zwave_js")
        ),
    }
)


class AdaptiveLightingProConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        try:
            validated_zones = self._validate_zones(user_input[CONF_ZONES])
        except ValidationError as err:
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA,
                errors={err.field: err.message},
            )
        data = {
            CONF_INSTALLATION_ID: str(uuid.uuid4()),
            CONF_ZONES: validated_zones,
            CONF_SENSORS: self._build_sensors(user_input),
            CONF_CONTROLLERS: self._build_controllers(user_input),
        }
        return self.async_create_entry(title="Adaptive Lighting Pro", data=data)

    def _validate_zones(self, zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        validated: List[Dict[str, Any]] = []
        existing: List[str] = []
        for zone in zones:
            validated_zone = validate_zone_config(self.hass, zone, existing)
            existing.append(validated_zone["zone_id"])
            validated.append(validated_zone)
        return validated

    @staticmethod
    def _build_sensors(user_input: Dict[str, Any]) -> Dict[str, Any]:
        sensors: Dict[str, Any] = {}
        for key in (CONF_LUX_SENSOR, CONF_WEATHER_ENTITY, CONF_SONOS_SENSOR):
            value = user_input.get(key)
            if value:
                sensors[key] = value
        return sensors

    @staticmethod
    def _build_controllers(user_input: Dict[str, Any]) -> Dict[str, Any]:
        controllers: Dict[str, Any] = {}
        device_id = user_input.get(CONF_ZEN32_DEVICE)
        if device_id:
            controllers[CONF_ZEN32_DEVICE] = device_id
        return controllers

    async def async_step_import(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        return await self.async_step_user(user_input)

    @staticmethod
    async def async_get_options_flow(entry: config_entries.ConfigEntry):
        return AdaptiveLightingProOptionsFlowHandler(entry)


class AdaptiveLightingProOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: Dict[str, Any] | None = None):
        options = dict(self._entry.options)
        defaults = {
            CONF_TIMEOUTS: options.get(
                CONF_TIMEOUTS, {"base_day_min": 60, "base_night_min": 180}
            ),
            CONF_RATE_LIMIT: options.get(
                CONF_RATE_LIMIT,
                {
                    "max_events": DEFAULT_RATE_LIMIT_MAX_EVENTS,
                    "window_sec": DEFAULT_RATE_LIMIT_WINDOW,
                },
            ),
            CONF_NIGHTLY_SWEEP: options.get(
                CONF_NIGHTLY_SWEEP, {"time": DEFAULT_NIGHTLY_SWEEP_TIME}
            ),
            CONF_WATCHDOG: options.get(
                CONF_WATCHDOG, {"interval_min": DEFAULT_WATCHDOG_INTERVAL_MIN}
            ),
            CONF_DEBUG: options.get(CONF_DEBUG, DEFAULT_DEBUG_CONFIG),
            CONF_ENV_BOOST: options.get(CONF_ENV_BOOST, DEFAULT_ENV_MULTIPLIER_BOOST),
        }
        schema = vol.Schema(
            {
                vol.Required("base_day_min", default=defaults[CONF_TIMEOUTS]["base_day_min"]): int,
                vol.Required("base_night_min", default=defaults[CONF_TIMEOUTS]["base_night_min"]): int,
                vol.Required("rate_max", default=defaults[CONF_RATE_LIMIT]["max_events"]): int,
                vol.Required("rate_window", default=defaults[CONF_RATE_LIMIT]["window_sec"]): int,
                vol.Required("nightly_time", default=defaults[CONF_NIGHTLY_SWEEP]["time"]): str,
                vol.Required("watchdog_interval", default=defaults[CONF_WATCHDOG]["interval_min"]): int,
                vol.Required("debug_log", default=defaults[CONF_DEBUG]["debug_log"]): bool,
                vol.Required("trace_logbook", default=defaults[CONF_DEBUG]["trace_logbook"]): bool,
                vol.Required("env_boost", default=defaults[CONF_ENV_BOOST]): float,
            }
        )
        if user_input is None:
            return self.async_show_form(step_id="init", data_schema=schema)
        options[CONF_TIMEOUTS] = {
            "base_day_min": user_input["base_day_min"],
            "base_night_min": user_input["base_night_min"],
        }
        options[CONF_RATE_LIMIT] = {
            "max_events": user_input["rate_max"],
            "window_sec": user_input["rate_window"],
        }
        options[CONF_NIGHTLY_SWEEP] = {"time": user_input["nightly_time"]}
        options[CONF_WATCHDOG] = {"interval_min": user_input["watchdog_interval"]}
        options[CONF_DEBUG] = {
            "debug_log": user_input["debug_log"],
            "trace_logbook": user_input["trace_logbook"],
        }
        options[CONF_ENV_BOOST] = float(user_input["env_boost"])
        return self.async_create_entry(title="Options", data=options)
