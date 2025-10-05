"""Constants for the AL Layer Manager integration."""
from __future__ import annotations

DOMAIN = "al_layer_manager"
DEFAULT_MANUAL_DURATION = 20  # minutes
DEFAULT_MODE_PRIORITY = {
    "focus": 90,
    "relax": 70,
    "movie": 80,
    "late_night": 95,
    "cleaning": 60,
    "guest": 65,
    "vacation": 50,
}

ENVIRONMENT_PROFILES = {
    "foggy": {"brightness": 0.25, "kelvin": -300},
    "cloudy": {"brightness": 0.15, "kelvin": -200},
    "sad": {"brightness": 0.35, "kelvin": -400},
}

MANUAL_DECAY_STEP = 0.1  # brightness per 5 minutes when decaying to adaptive target
MANUAL_DECAY_INTERVAL_MINUTES = 5

SCENE_CONFIGS_KNOWN_ISSUE = (
    "Scene configs rely on user entities and must be scrubbed before HACS submission."
)
