from __future__ import annotations

from custom_components.al_layer_manager.analytics import AnalyticsSuite, compute_health_score


def test_analytics_counters_increment() -> None:
    suite = AnalyticsSuite()
    suite.increment("overrides")
    suite.increment("overrides", amount=2)
    assert suite.get("overrides") == 3


def test_health_score_penalties() -> None:
    score = compute_health_score(missed_syncs=2, stale_sensors=1, stuck_overrides=1)
    assert score == 100 - (2 * 5 + 1 * 7 + 1 * 10)
