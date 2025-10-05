"""Executor tests for retry and rate limiting."""
from __future__ import annotations

import asyncio

import pytest

from custom_components.adaptive_lighting_pro.core.executors import ExecutorManager
from custom_components.adaptive_lighting_pro.robustness.rate_limiter import RateLimitConfig, RateLimiter
from custom_components.adaptive_lighting_pro.robustness.retry_manager import RetryManager
from tests.conftest import HomeAssistant


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_executor_retries(hass: HomeAssistant, monkeypatch) -> None:
    attempts = 0

    async def failing_call(domain: str, service: str, data: dict, blocking: bool = False) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("boom")

    monkeypatch.setattr(hass.services, "async_call", failing_call)
    rate_limiter = RateLimiter(RateLimitConfig(max_events=10, window_sec=30))
    retry_manager = RetryManager(3, [0, 0, 0])
    executor = ExecutorManager(hass, rate_limiter=rate_limiter, retry_manager=retry_manager, debug=False)
    result = run(executor.apply("switch.zone", {"lights": []}))
    assert result["status"] == "ok"
    assert attempts == 3


def test_executor_rate_limit(hass: HomeAssistant) -> None:
    calls = []

    async def record_call(domain: str, service: str, data: dict, blocking: bool = False) -> None:
        calls.append((domain, service))

    hass.services.async_call = record_call  # type: ignore[assignment]
    rate_limiter = RateLimiter(RateLimitConfig(max_events=1, window_sec=60))
    retry_manager = RetryManager(1, [0])
    executor = ExecutorManager(hass, rate_limiter=rate_limiter, retry_manager=retry_manager, debug=False)
    run(executor.apply("switch.zone", {"lights": []}))
    result = run(executor.apply("switch.zone", {"lights": []}))
    assert result["error_code"] == "RATE_LIMITED"
    assert len(calls) == 1
