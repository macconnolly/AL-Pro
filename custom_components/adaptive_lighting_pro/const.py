"""Constants for Adaptive Lighting Pro integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "adaptive_lighting_pro"
PLATFORMS: Final = [
    "switch",
    "sensor",
    "binary_sensor",
    "number",
    "select",
    "button",
]

CONF_ZONES: Final = "zones"
CONF_SENSORS: Final = "sensors"
CONF_CONTROLLERS: Final = "controllers"
CONF_INSTALLATION_ID: Final = "installation_id"

CONF_LUX_SENSOR: Final = "lux_entity"
CONF_WEATHER_ENTITY: Final = "weather_entity"
CONF_SONOS_SENSOR: Final = "sonos_alarm_sensor"
CONF_ZEN32_DEVICE: Final = "zen32_device_id"

CONF_TIMEOUTS: Final = "timeouts"
CONF_OPTIONS_MODE_MULTIPLIERS: Final = "mode_multipliers"
CONF_ENV_BOOST: Final = "env_multiplier_boost"
CONF_RATE_LIMIT: Final = "rate_limit"
CONF_NIGHTLY_SWEEP: Final = "nightly_sweep"
CONF_WATCHDOG: Final = "watchdog"
CONF_SCENES: Final = "scenes"
CONF_DEBUG: Final = "debug"
CONF_FORCE_APPLY: Final = "force_apply"
CONF_PER_ZONE_OVERRIDES: Final = "per_zone_overrides"

EVENT_STARTUP_COMPLETE: Final = "alp_startup_complete"
EVENT_SYNC_REQUIRED: Final = "alp_sync_required"
EVENT_MANUAL_DETECTED: Final = "alp_manual_detected"
EVENT_TIMER_EXPIRED: Final = "alp_timer_expired"
EVENT_ENVIRONMENTAL_CHANGED: Final = "alp_environmental_changed"
EVENT_MODE_CHANGED: Final = "alp_mode_changed"
EVENT_SCENE_CHANGED: Final = "alp_scene_changed"
EVENT_RESET_REQUESTED: Final = "alp_reset_requested"
EVENT_BUTTON_PRESSED: Final = "alp_button_pressed"

DEFAULT_BASE_DAY_MIN: Final = 60
DEFAULT_BASE_NIGHT_MIN: Final = 180
DEFAULT_MODE_MULTIPLIERS: Final = {
    "adaptive": 1.0,
    "work": 0.5,
    "focus": 0.75,
    "relax": 1.25,
    "movie": 2.0,
    "late_night": 3.0,
}
DEFAULT_ENV_MULTIPLIER_BOOST: Final = 0.8
DEFAULT_BRIGHTNESS_STEP: Final = 20
DEFAULT_COLOR_TEMP_STEP: Final = 500
DEFAULT_RATE_LIMIT_MAX_EVENTS: Final = 10
DEFAULT_RATE_LIMIT_WINDOW: Final = 30
DEFAULT_NIGHTLY_SWEEP_TIME: Final = "03:30"
DEFAULT_WATCHDOG_INTERVAL_MIN: Final = 5
DEFAULT_SCENE_ORDER: Final = [
    "default",
    "all_lights",
    "no_spots",
    "evening_comfort",
    "ultra_dim",
]
MODE_ALIASES: Final = {
    "Bright Focus": "focus",
    "Dim Relax": "relax",
    "Warm Evening": "movie",
    "Cool Energy": "work",
}
DEFAULT_SCENE_PRESETS: Final = {
    "default": {
        "adapt_brightness": True,
        "adapt_color_temp": True,
        "manual": False,
        "actions": [],
        "offsets": {"brightness": 0, "warmth": 0},
    },
    "all_lights": {
        "brightness_pct": 92,
        "color_temp_kelvin": 3300,
        "manual": True,
        "actions": [
            {
                "service": "light.turn_on",
                "data": {
                    "entity_id": [
                        "light.accent_spots_lights",
                        "light.all_adaptive_lights",
                    ],
                    "transition": 2,
                },
            },
            {
                "service": "light.turn_on",
                "data": {
                    "entity_id": "light.accent_spots_lights",
                    "brightness_pct": 2,
                    "transition": 2,
                },
            },
        ],
        "offsets": {"brightness": 0, "warmth": 0},
    },
    "no_spots": {
        "brightness_pct": 70,
        "color_temp_kelvin": 3000,
        "manual": True,
        "actions": [
            {
                "service": "light.turn_off",
                "data": {
                    "entity_id": [
                        "light.living_room_spot_lights",
                        "light.dining_room_spot_lights",
                    ],
                    "transition": 2,
                },
            }
        ],
        "offsets": {"brightness": 15, "warmth": 0},
    },
    "evening_comfort": {
        "brightness_pct": 55,
        "color_temp_kelvin": 2800,
        "manual": True,
        "actions": [
            {
                "service": "light.turn_off",
                "data": {
                    "entity_id": [
                        "light.recessed_ceiling_lights",
                        "light.living_room_hallway_lights",
                    ],
                    "transition": 1,
                },
            },
            {
                "service": "light.turn_on",
                "data": {
                    "entity_id": [
                        "light.kitchen_island_pendants",
                        "light.living_room_credenza_light",
                        "light.living_room_corner_accent",
                    ],
                    "transition": 1,
                },
            },
            {
                "service": "light.turn_on",
                "data": {
                    "entity_id": "light.dining_room_spot_lights",
                    "brightness_pct": 15,
                    "transition": 1,
                },
            },
        ],
        "offsets": {"brightness": -5, "warmth": -500},
    },
    "ultra_dim": {
        "brightness_pct": 12,
        "color_temp_kelvin": 2200,
        "manual": True,
        "actions": [],
        "offsets": {"brightness": -50, "warmth": -1000},
    },
}
DEFAULT_DEBUG_CONFIG: Final = {"debug_log": False, "trace_logbook": False}
DEFAULT_FORCE_APPLY: Final = False

MANUAL_DEBOUNCE_MS: Final = 500
ZEN32_DEBOUNCE_MS: Final = 250
SONOS_SYNC_WINDOW: Final = timedelta(seconds=60)
SUNSET_ELEVATION_DEG: Final = 6.0
SYNC_TRANSITION_SEC: Final = 1
SYNC_TIMEOUT: Final = 30
SCENE_TIMEOUT: Final = 60

ATTR_MANUAL_ACTIVE: Final = "manual_active"
ATTR_LAST_SYNC_MS: Final = "last_sync_ms"
ATTR_LAST_ERROR: Final = "last_error"
ATTR_ZONE_ID: Final = "zone_id"
ATTR_SUNRISE_OFFSET: Final = "sunrise_offset"
ATTR_LOCK: Final = "lock"

SERVICE_FORCE_SYNC: Final = "force_sync"
SERVICE_RESET_ZONE: Final = "reset_zone"
SERVICE_ENABLE_ZONE: Final = "enable_zone"
SERVICE_DISABLE_ZONE: Final = "disable_zone"
SERVICE_SELECT_MODE: Final = "select_mode"
SERVICE_SELECT_SCENE: Final = "select_scene"
SERVICE_ADJUST: Final = "adjust"
SERVICE_BACKUP_PREFS: Final = "backup_prefs"
SERVICE_RESTORE_PREFS: Final = "restore_prefs"

RATE_LIMIT_ENTITY_ID: Final = "binary_sensor.alp_rate_limit_reached"

TELEMETRY_SENSOR_ID: Final = "sensor.alp_system_snapshot"

HEALTH_SENSOR_ID: Final = "sensor.alp_health_score"
ANALYTICS_SENSOR_ID: Final = "sensor.alp_analytics_summary"
MODE_SELECT_ID: Final = "select.alp_mode"
SCENE_SELECT_ID: Final = "select.alp_scene"

WATCHDOG_EVENT: Final = "alp_watchdog_tick"
SWEEP_EVENT: Final = "alp_nightly_sweep"

RETRY_ATTEMPTS: Final = 3
RETRY_BACKOFFS: Final = [1, 2, 4]
