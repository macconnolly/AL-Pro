"""Logging utilities for Adaptive Lighting Pro."""
from __future__ import annotations

import logging
from typing import Any, Dict

from ..const import DOMAIN

_LOGGER = logging.getLogger(DOMAIN)


def get_logger() -> logging.Logger:
    """Return integration logger."""
    return _LOGGER


def log_debug(enabled: bool, message: str, *args: Any, **kwargs: Any) -> None:
    """Log debug message when enabled."""
    if enabled:
        _LOGGER.debug(message, *args, **kwargs)


def log_event(enabled: bool, event: str, data: Dict[str, Any]) -> None:
    """Log structured event data."""
    if enabled:
        _LOGGER.debug("event=%s data=%s", event, data)
