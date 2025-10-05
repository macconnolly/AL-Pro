"""Constants for the Adaptive Lighting Pro integration.

All constants extracted from implementation_1.yaml with line number citations.
"""

# Domain and Integration
DOMAIN = "adaptive_lighting_pro"
ADAPTIVE_LIGHTING_DOMAIN = "adaptive_lighting"  # Required dependency

# Platforms
PLATFORMS = ["switch", "number", "select", "sensor", "button", "light"]

# Configuration Keys
CONF_ZONES = "zones"
CONF_ZONE_ID = "zone_id"
CONF_ZONE_NAME = "zone_name"
CONF_ZONE_LIGHTS = "lights"
CONF_ADAPTIVE_LIGHTING_SWITCH = "adaptive_lighting_switch"
CONF_MANUAL_TIMER_DURATION = "manual_timer_duration"
CONF_BRIGHTNESS_RANGE = "brightness_range"
CONF_COLOR_TEMP_RANGE = "color_temp_range"
CONF_BRIGHTNESS_MIN = "brightness_min"
CONF_BRIGHTNESS_MAX = "brightness_max"
CONF_COLOR_TEMP_MIN = "color_temp_min"
CONF_COLOR_TEMP_MAX = "color_temp_max"
CONF_SLEEP_BRIGHTNESS = "sleep_brightness"
CONF_SLEEP_COLOR_TEMP = "sleep_color_temp"
CONF_ADAPT_DELAY = "adapt_delay"
CONF_INTERVAL = "interval"

# Global Settings Keys
CONF_BRIGHTNESS_INCREMENT = "brightness_increment"
CONF_COLOR_TEMP_INCREMENT = "color_temp_increment"
CONF_MANUAL_CONTROL_TIMEOUT = "manual_control_timeout"
CONF_GENERAL_TRANSITION_SPEED = "general_transition_speed"

# Environmental Settings Keys
CONF_ENVIRONMENTAL_ENABLED = "environmental_enabled"
CONF_LUX_SENSOR = "lux_sensor"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_MAX_BOOST = "max_boost"
CONF_SUNSET_FADE_ENABLED = "sunset_fade_enabled"

# Integration Settings Keys
CONF_SONOS_ENABLED = "sonos_enabled"
CONF_SONOS_ALARM_SENSOR = "sonos_alarm_sensor"
CONF_SONOS_BEDROOM_OFFSET = "sonos_bedroom_offset"
CONF_SONOS_KITCHEN_OFFSET = "sonos_kitchen_offset"

# Zen32 Scene Controller Settings Keys (Phase 3.1)
CONF_ZEN32_ENABLED = "zen32_enabled"
CONF_ZEN32_BUTTON_ENTITIES = "zen32_button_entities"
CONF_ZEN32_BUTTON_ACTIONS = "zen32_button_actions"
CONF_ZEN32_DEBOUNCE_DURATION = "zen32_debounce_duration"

# Wake Sequence Settings Keys (Phase 2.1)
CONF_WAKE_SEQUENCE_ENABLED = "wake_sequence_enabled"
CONF_WAKE_SEQUENCE_TARGET_ZONE = "wake_sequence_target_zone"
CONF_WAKE_SEQUENCE_DURATION = "wake_sequence_duration"
CONF_WAKE_SEQUENCE_MAX_BOOST = "wake_sequence_max_boost"

# Default Zone Configurations
# Extracted from implementation_1.yaml lines 310-416
DEFAULT_ZONES = {
    "main_living": {
        "name": "Main Living",
        "lights": [
            "light.entryway_lamp",
            "light.living_room_floor_lamp",
            "light.office_desk_lamp",
            "light.living_room_corner_accent",
            "light.living_room_couch_lamp",
            "light.living_room_credenza_light",
        ],
        "min_brightness": 45,
        "max_brightness": 100,
        "sleep_brightness": 25,
        "min_color_temp": 2250,
        "max_color_temp": 2950,
        "sleep_color_temp": 1800,
        "interval": 20,
        "adapt_delay": 5,  # Line 408
        "sonos_offset": -2700,  # -45 minutes
        "sonos_alarm_offset": -1200,  # -20 minutes (Line 1463)
    },
    "kitchen_island": {
        "name": "Kitchen Island",
        "lights": ["light.kitchen_island_pendants"],
        "min_brightness": 30,  # Line 341 (was 15 in original plan)
        "max_brightness": 100,
        "sleep_brightness": 1,
        "min_color_temp": 2000,
        "max_color_temp": 4000,
        "interval": 20,
        "adapt_delay": 0,  # Line 341
        "sonos_offset": -2700,
        "sonos_alarm_offset": -2700,  # Line 1459
    },
    "bedroom_primary": {
        "name": "Bedroom Primary",
        "lights": [
            "light.master_bedroom_table_lamps",
            "light.master_bedroom_corner_accent",
        ],
        "min_brightness": 20,
        "max_brightness": 40,
        "sleep_brightness": 5,
        "min_color_temp": 1800,
        "max_color_temp": 2250,
        "interval": 20,
        "adapt_delay": 0,  # Line 361
        "sonos_offset": -1800,  # -30 minutes
        "sonos_alarm_offset": -1800,  # Line 1455
    },
    "accent_spots": {
        "name": "Accent Spots",
        "lights": [
            "light.dining_room_spot_lights",
            "light.living_room_spot_lights",
        ],
        "min_brightness": 20,
        "max_brightness": 50,
        "sleep_brightness": 1,
        "min_color_temp": 2000,
        "max_color_temp": 6500,
        "interval": 20,
        "adapt_delay": 0,  # Line 381
        "sonos_offset": -2700,
        "sonos_alarm_offset": -1500,  # Line 1447
    },
    "recessed_ceiling": {
        "name": "Recessed Ceiling",
        "lights": [
            "light.kitchen_main_lights",
            "light.living_room_hallway_lights",
        ],
        "min_brightness": 2,
        "max_brightness": 23,
        "sleep_brightness": 1,
        "interval": 20,
        "adapt_delay": 0,  # Line 322
        "sonos_offset": -2700,
        # No color temp for recessed lights (brightness-only)
        "brightness_only": True,
    },
}

# Default Values
# From implementation_1.yaml lines 128-229
DEFAULT_BRIGHTNESS_INCREMENT = 20  # % (Line 136)
DEFAULT_COLOR_TEMP_INCREMENT = 500  # K (Line 144)
DEFAULT_MANUAL_TIMEOUT_HOURS = 2  # hours (Line 172)
DEFAULT_MANUAL_TIMEOUT_SECONDS = 7200  # seconds (2 hours)
DEFAULT_TRANSITION_SPEED = 1  # seconds (Line 180)
DEFAULT_ENVIRONMENTAL_OFFSET = 0  # % (Line 190)
DEFAULT_SUNSET_FADE_OFFSET = 0  # % (Line 200)
DEFAULT_SCENE_BRIGHTNESS_OFFSET = 0  # % (Line 209)
DEFAULT_SCENE_WARMTH_OFFSET = 0  # K (Line 218)
DEFAULT_WAKE_SEQUENCE_OFFSET = 0  # % (Line 227)

# Phase 2.1: Wake Sequence Defaults
DEFAULT_WAKE_SEQUENCE_ENABLED = False
DEFAULT_WAKE_SEQUENCE_TARGET_ZONE = "bedroom"
DEFAULT_WAKE_SEQUENCE_DURATION = 900  # seconds (15 minutes)
DEFAULT_WAKE_SEQUENCE_MAX_BOOST = 20  # percent

# Phase 3.1: Zen32 Scene Controller Defaults
DEFAULT_ZEN32_ENABLED = False
DEFAULT_ZEN32_DEBOUNCE_DURATION = 0.5  # seconds
DEFAULT_ZEN32_BUTTON_ENTITIES = {
    "button_1": "event.scene_controller_scene_001",
    "button_2": "event.scene_controller_scene_002",
    "button_3": "event.scene_controller_scene_003",
    "button_4": "event.scene_controller_scene_004",
    "button_5": "event.scene_controller_scene_005",
}
DEFAULT_ZEN32_BUTTON_ACTIONS = {
    "button_1": "cycle_scene",
    "button_2": "brighter",
    "button_3": "reset_manual",
    "button_4": "dimmer",
    "button_5": "none",  # Toggle lights - handled outside ALP
}

# Adjustment Limits
# From lines 148-228
BRIGHTNESS_ADJUSTMENT_MIN = -100  # % (Line 150)
BRIGHTNESS_ADJUSTMENT_MAX = 100  # % (Line 151)
BRIGHTNESS_ADJUSTMENT_STEP = 5  # % (Line 152)

BRIGHTNESS_INCREMENT_MIN = 5  # % (Line 131)
BRIGHTNESS_INCREMENT_MAX = 50  # % (Line 132)
BRIGHTNESS_INCREMENT_STEP = 5  # % (Line 133)

WARMTH_ADJUSTMENT_MIN = -2500  # K (Line 158)
WARMTH_ADJUSTMENT_MAX = 2500  # K (Line 159)
WARMTH_ADJUSTMENT_STEP = 50  # K (Line 160)

COLOR_TEMP_INCREMENT_MIN = 100  # K (Line 139)
COLOR_TEMP_INCREMENT_MAX = 1000  # K (Line 140)
COLOR_TEMP_INCREMENT_STEP = 50  # K (Line 141)

SCENE_BRIGHTNESS_MIN = -80  # % (Line 204)
SCENE_BRIGHTNESS_MAX = 20  # % (Line 205)
SCENE_BRIGHTNESS_STEP = 5  # % (Line 206)

SCENE_WARMTH_MIN = -1000  # K (Line 213)
SCENE_WARMTH_MAX = 500  # K (Line 214)
SCENE_WARMTH_STEP = 100  # K (Line 215)

WAKE_SEQUENCE_MIN = -50  # % (Line 223)
WAKE_SEQUENCE_MAX = 50  # % (Line 224)
WAKE_SEQUENCE_STEP = 5  # % (Line 225)

# Environmental Settings
# From lines 1467-1600
LUX_THRESHOLD_LOW = 1000  # Trigger boost below this (Line 1471)
LUX_THRESHOLD_HIGH = 2000  # Reset boost above this (Line 1517)
LUX_DELAY_TRIGGER = 300  # 5 minutes in seconds (Line 1471)
LUX_DELAY_RESET = 600  # 10 minutes in seconds (Line 1517)
MAX_ENVIRONMENTAL_BOOST = 25  # % (Line 1557)

# Lux-to-Boost Mapping (logarithmic curve)
# From lines 1550-1573
LUX_BOOST_MAPPING = {
    10: 15,  # < 10 lux: +15%
    25: 10,  # < 25 lux: +10%
    50: 7,  # < 50 lux: +7%
    100: 5,  # < 100 lux: +5%
    200: 3,  # < 200 lux: +3%
    400: 1,  # < 400 lux: +1%
}

# Weather Condition Boost Mapping
# From lines 1521-1538
WEATHER_BOOST_MAPPING = {
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
    "exceptional": 15,
}

# Seasonal Adjustments
# From lines 1542-1546
SEASONAL_ADJUSTMENTS = {
    "winter": 8,  # Dec, Jan, Feb: +8%
    "summer": -3,  # Jun, Jul, Aug: -3%
    "transition": 0,  # Other months: 0%
}

# Time Restrictions (hours)
# From lines 1548-1555
ENV_NIGHT_DISABLE_START = 22  # 10 PM
ENV_NIGHT_DISABLE_END = 6  # 6 AM
ENV_REDUCED_HOURS = [(6, 8), (18, 22)]  # Morning and evening
ENV_REDUCED_MULTIPLIER = 0.7  # 70% during reduced hours

# Sunset Fade Settings
# From lines 2414-2455
SUNSET_FADE_ELEVATION_MIN = -4  # degrees (Line 2425)
SUNSET_FADE_ELEVATION_MAX = 4  # degrees (Line 2425)
SUNSET_FADE_MAX_OFFSET = -25  # % (Line 2437)
SUNSET_FADE_CHECK_INTERVAL = 300  # 5 minutes in seconds (Line 2420)

# Mode Definitions
# From lines 234-244, 1275-1389
MODES = {
    "default": {
        "name": "Default",
        "description": "Standard adaptive behavior",
    },
    "work": {
        "name": "Work",
        "description": "Bright and cool for productivity",
        "zones": ["main_living", "kitchen_island", "accent_spots"],
        "min_brightness": 85,  # Line 1313
        "max_brightness": 100,  # Line 1314
        "min_color_temp": 2700,  # Line 1323
        "max_color_temp": 2900,  # Line 1324
    },
    "late_night": {
        "name": "Late Night",
        "description": "Dim and warm for winding down",
        "zones": ["all"],
        "max_brightness": 25,  # Line 1342
        "max_color_temp": 2500,  # Line 1351
    },
    "movie": {
        "name": "Movie",
        "description": "Accent lighting only",
        "type": "direct_control",  # Line 1275
        "lights_off": [  # Lines 1284-1288
            "light.living_room_couch_lamp",
            "light.living_room_credenza_light",
            "light.living_room_floor_lamp",
            "light.office_desk_lamp",
            "light.entryway_lamp",
        ],
        "lights_on": {  # Lines 1291-1302
            "entities": [
                "light.living_room_corner_accent",
                "light.living_room_spot_lights",
                "light.dining_room_spot_lights",
            ],
            "brightness_pct": 15,
            "color_temp": 454,  # 2200K in mireds
        },
    },
    "bright_focus": {
        "name": "Bright Focus",
        "description": "Temporary brightness boost",
        "adjustment_type": "brightness",  # Line 1248
        "uses_timer": True,
    },
    "dim_relax": {
        "name": "Dim Relax",
        "description": "Temporary brightness reduction",
        "adjustment_type": "brightness",
        "uses_timer": True,
    },
    "warm_evening": {
        "name": "Warm Evening",
        "description": "Temporary warmth increase",
        "adjustment_type": "warmth",
        "uses_timer": True,
    },
    "cool_energy": {
        "name": "Cool Energy",
        "description": "Temporary coolness increase",
        "adjustment_type": "warmth",
        "uses_timer": True,
    },
}

# Scene Definitions
# From lines 3058-3216
SCENES = {
    "all_lights": {
        "name": "All Lights",
        "description": "Everything on with spotlights at 2%",
        "brightness_offset": 0,  # Line 3073
        "warmth_offset": 0,  # Line 3074
        "spotlight_brightness": 2,  # Lines 3087, 3108
    },
    "no_spotlights": {
        "name": "No Spotlights",
        "description": "Spots off, +15% brightness compensation",
        "brightness_offset": 15,  # Line 3127
        "warmth_offset": 0,  # Line 3128
        "lights_off": [  # Lines 3133-3134
            "light.living_room_spot_lights",
            "light.dining_room_spot_lights",
        ],
    },
    "evening_comfort": {
        "name": "Evening Comfort",
        "description": "Warm, pendant lights, minimal overhead",
        "brightness_offset": -5,  # Line 3150
        "warmth_offset": -500,  # Line 3151
        "lights_off": [  # Lines 3156-3157
            "light.kitchen_main_lights",  # recessed_ceiling
            "light.living_room_hallway_lights",
        ],
        "lights_on": [  # Lines 3162-3164
            "light.kitchen_island_pendants",
            "light.living_room_credenza_light",  # Fixed typo from line 3169
            "light.living_room_corner_accent",
        ],
        "dining_spots_brightness": 15,  # Line 3177
    },
    "ultra_dim": {
        "name": "Ultra Dim",
        "description": "Minimal lighting, very warm",
        "brightness_offset": -50,  # Line 3193
        "warmth_offset": -1000,  # Line 3194
        "lights_off": [  # Lines 3199-3202
            "light.dining_room_spot_lights",
            "light.living_room_spot_lights",
            "light.kitchen_main_lights",
            "light.living_room_hallway_lights",
        ],
        "kitchen_island_brightness": 10,  # Line 3210
    },
}

# Zen32 Settings
# From lines 2494-2501
ZEN32_DEBOUNCE_SECONDS = 0.5  # Line 2501

# Coordinator Update Intervals
COORDINATOR_UPDATE_INTERVAL = 30  # seconds (from PROJECT_PLAN.md)

# Entity ID Prefixes
ENTITY_PREFIX = "alp"  # All entities prefixed with "alp_"

# Event Names
EVENT_CALCULATION_COMPLETE = f"{DOMAIN}_calculation_complete"  # Line 1904
EVENT_MANUAL_CONTROL_TRIGGERED = f"{DOMAIN}_manual_control_triggered"

# Service Names
SERVICE_ADJUST_BRIGHTNESS = "adjust_brightness"
SERVICE_ADJUST_COLOR_TEMP = "adjust_color_temp"
SERVICE_SET_MODE = "set_mode"
SERVICE_APPLY_SCENE = "apply_scene"
SERVICE_RESET_MANUAL_ADJUSTMENTS = "reset_manual_adjustments"
SERVICE_RESET_ALL = "reset_all"
SERVICE_CLEAR_MANUAL_CONTROL = "clear_manual_control"
SERVICE_SET_WAKE_ALARM = "set_wake_alarm"  # Phase 2.1: Manual wake alarm trigger
SERVICE_CLEAR_WAKE_ALARM = "clear_wake_alarm"  # Phase 2.1: Clear wake sequence

# Attribute Names
ATTR_BRIGHTNESS_ADJUSTMENT = "brightness_adjustment"
ATTR_WARMTH_ADJUSTMENT = "warmth_adjustment"
ATTR_MANUAL_CONTROL_ACTIVE = "manual_control_active"
ATTR_TIMER_REMAINING = "timer_remaining"
ATTR_CURRENT_MODE = "current_mode"
ATTR_ENVIRONMENTAL_BOOST = "environmental_boost"
ATTR_SUNSET_FADE_OFFSET = "sunset_fade_offset"
ATTR_ZONES = "zones"
ATTR_INCREMENT = "increment"
ATTR_MODE = "mode"
ATTR_SCENE = "scene"

# Phase 2 Additions for Production Coordinator

from enum import Enum

class Mode(Enum):
    """Home lighting modes."""
    ADAPTIVE = "adaptive"
    WORK = "work"
    LATE_NIGHT = "late_night"
    MOVIE = "movie"
    BRIGHT_FOCUS = "bright_focus"
    DIM_RELAX = "dim_relax"
    WARM_EVENING = "warm_evening"
    COOL_ENERGY = "cool_energy"


class Scene(Enum):
    """Lighting scenes."""
    DEFAULT = "default"
    ALL_LIGHTS = "all_lights"
    NO_SPOTLIGHTS = "no_spotlights"
    EVENING_COMFORT = "evening_comfort"
    ULTRA_DIM = "ultra_dim"


# Zone Configurations (from DEFAULT_ZONES)
ZONE_CONFIGS = {
    "main_living": DEFAULT_ZONES["main_living"],
    "kitchen_island": DEFAULT_ZONES["kitchen_island"],
    "bedroom_primary": DEFAULT_ZONES["bedroom_primary"],
    "accent_spots": DEFAULT_ZONES["accent_spots"],
    "recessed_ceiling": DEFAULT_ZONES["recessed_ceiling"],
}

# Default adjustment steps (for coordinator)
DEFAULT_BRIGHTNESS_STEP = 10  # percent
DEFAULT_WARMTH_STEP = 250  # Kelvin
DEFAULT_TRANSITION = 1  # seconds

# Mode Configurations
# From implementation_1.yaml lines 1307-1389
MODE_CONFIGS = {
    Mode.ADAPTIVE: {
        # Default/adaptive mode - no overrides, AL switches use config defaults
        "zones": {}
    },
    Mode.WORK: {
        # Work Mode: Bright, cool lighting (lines 1307-1332)
        "zones": {
            "main_living": {
                "min_brightness": 85,
                "max_brightness": 100,
                "min_color_temp": 2700,
                "max_color_temp": 2900,
            },
            "kitchen_island": {
                "min_brightness": 85,
                "max_brightness": 100,
                "min_color_temp": 2700,
                "max_color_temp": 2900,
            },
            "accent_spots": {
                "min_brightness": 85,
                "max_brightness": 100,
                "min_color_temp": 2700,
                "max_color_temp": 2900,
            },
        }
    },
    Mode.LATE_NIGHT: {
        # Late Night Mode: Dim, warm (lines 1334-1361)
        "zones": {
            "main_living": {
                "max_brightness": 25,
                "max_color_temp": 2500,
            },
            "kitchen_island": {
                "max_brightness": 25,
                "max_color_temp": 2500,
            },
            "bedroom_primary": {
                "max_brightness": 25,
                "max_color_temp": 2500,
            },
            "accent_spots": {
                "max_brightness": 25,
                "max_color_temp": 2500,
            },
            "recessed_ceiling": {
                "max_brightness": 25,
            },
        }
    },
    Mode.MOVIE: {
        # Movie Mode: Accent lighting only (lines 1275-1305)
        # Special handling required - turn off main lights, set accent lights
        "zones": {},
        "actions": [
            {
                "action": "scene.create",
                "scene_id": "before_movie",
                "snapshot_entities": "all_adaptive_lights",
            },
            {
                "action": "light.turn_off",
                "entity_id": [
                    "light.living_room_couch_lamp",
                    "light.living_room_credenza_light",
                    "light.living_room_floor_lamp",
                    "light.office_desk_lamp",
                    "light.entryway_lamp",
                ],
                "transition": 1,
            },
            {
                "action": "light.turn_on",
                "entity_id": [
                    "light.living_room_corner_accent",
                    "light.living_room_spot_lights",
                    "light.dining_room_spot_lights",
                ],
                "brightness_pct": 15,
                "color_temp": 454,  # 2200K
                "transition": 1,
            },
        ]
    },
    # Note: The following modes don't have explicit implementations in the YAML
    # but are defined in the mode enum for future use
    Mode.BRIGHT_FOCUS: {
        "zones": {}
    },
    Mode.DIM_RELAX: {
        "zones": {}
    },
    Mode.WARM_EVENING: {
        "zones": {}
    },
    Mode.COOL_ENERGY: {
        "zones": {}
    },
}

# Scene Configurations - Full System Restored
# From implementation_1.yaml lines 3077-3216
SCENE_CONFIGS = {
    Scene.DEFAULT: {
        "name": "Default",
        "brightness_offset": 0,
        "warmth_offset": 0,
        "actions": []
    },
    Scene.ALL_LIGHTS: {
        "name": "All Lights",
        "brightness_offset": 0,
        "warmth_offset": 0,
        "actions": [
            {
                "action": "light.turn_on",
                "entity_id": ["light.accent_spots_lights"],
                "brightness_pct": 2,
                "transition": 2,
            },
            {
                "action": "adaptive_lighting.set_manual_control",
                "entity_id": "switch.adaptive_lighting_accent_spots",
                "lights": [
                    "light.dining_room_spot_lights",
                    "light.living_room_spot_lights",
                ],
                "manual_control": True,
            },
            {
                "action": "light.turn_on",
                "entity_id": [
                    "light.recessed_ceiling_lights",
                    "light.all_adaptive_lights",
                ],
                "transition": 2,
            },
        ]
    },
    Scene.NO_SPOTLIGHTS: {
        "name": "No Spotlights (Boost)",
        "brightness_offset": 15,
        "warmth_offset": 0,
        "actions": [
            {
                "action": "light.turn_off",
                "entity_id": [
                    "light.living_room_spot_lights",
                    "light.dining_room_spot_lights",
                ],
                "transition": 2,
            },
        ]
    },
    Scene.EVENING_COMFORT: {
        "name": "Evening Comfort",
        "brightness_offset": -5,
        "warmth_offset": -500,
        "actions": [
            {
                "action": "light.turn_off",
                "entity_id": [
                    "light.recessed_ceiling_lights",
                    "light.living_room_hallway_lights",
                ],
                "transition": 1,
            },
            {
                "action": "light.turn_on",
                "entity_id": [
                    "light.kitchen_island_pendants",
                    "light.living_room_credenza_light",
                    "light.living_room_corner_accent",
                ],
                "transition": 1,
            },
            {
                "action": "adaptive_lighting.set_manual_control",
                "entity_id": "switch.adaptive_lighting_accent_spots",
                "lights": ["light.dining_room_spot_lights"],
                "manual_control": True,
            },
            {
                "action": "light.turn_on",
                "entity_id": ["light.dining_room_spot_lights"],
                "brightness_pct": 15,
                "transition": 1,
            },
        ]
    },
    Scene.ULTRA_DIM: {
        "name": "Ultra Dim",
        "brightness_offset": -50,
        "warmth_offset": -1000,
        "actions": [
            {
                "action": "light.turn_off",
                "entity_id": [
                    "light.dining_room_spot_lights",
                    "light.living_room_spot_lights",
                    "light.kitchen_main_lights",
                    "light.living_room_hallway_lights",
                ],
                "transition": 1,
            },
            {
                "action": "light.turn_on",
                "entity_id": ["light.kitchen_island_pendants"],
                "brightness_pct": 10,
                "transition": 2,
            },
        ]
    },
}

# Scene Presets - Offsets only (for simple adjustments without actions)
SCENE_PRESETS = {
    scene: {
        "name": config["name"],
        "brightness_offset": config["brightness_offset"],
        "warmth_offset": config["warmth_offset"],
    }
    for scene, config in SCENE_CONFIGS.items()
}

# Manual timeout configuration
MANUAL_TIMEOUT_MIN = 300  # 5 minutes
MANUAL_TIMEOUT_MAX = 14400  # 4 hours
MANUAL_TIMEOUT_STEP = 300  # 5 minute increments
