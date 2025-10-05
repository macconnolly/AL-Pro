from __future__ import annotations

from custom_components.al_layer_manager.mode import ModeManager
from custom_components.al_layer_manager.models import ModeProfile


def test_mode_priority() -> None:
    manager = ModeManager(priorities={"relax": 50, "focus": 90})
    focus_profile = ModeProfile(brightness_multiplier=1.1)
    relax_profile = ModeProfile(brightness_multiplier=0.6)
    state = manager.set_mode("relax", relax_profile)
    assert state.active_mode == "relax"
    state = manager.set_mode("focus", focus_profile)
    assert state.active_mode == "focus"
    cleared = manager.clear_mode("focus")
    assert cleared.active_mode == "relax"
