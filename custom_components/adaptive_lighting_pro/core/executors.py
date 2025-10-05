"""Service executors for Adaptive Lighting Pro."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict

from homeassistant.core import HomeAssistant

from ..const import SCENE_TIMEOUT, SYNC_TIMEOUT
from ..robustness.rate_limiter import RateLimiter
from ..robustness.retry_manager import RetryManager
from ..utils.logger import log_debug
from ..utils.timebox import run_with_timeout


class ExecutorManager:
    """Centralized executor responsible for service calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        rate_limiter: RateLimiter,
        retry_manager: RetryManager,
        debug: bool,
    ) -> None:
        self._hass = hass
        self._sem = asyncio.Semaphore(4)
        self._rate_limiter = rate_limiter
        self._retry = retry_manager
        self._debug = debug

    async def _execute(
        self,
        domain: str,
        service: str,
        data: Dict[str, Any],
        *,
        timeout: int,
    ) -> Dict[str, Any]:
        if not self._rate_limiter.allow():
            log_debug(self._debug, "Rate limit exceeded for %s.%s", domain, service)
            return {"status": "error", "error_code": "RATE_LIMITED", "duration_ms": 0}

        async with self._sem:
            start = time.perf_counter()

            async def _call() -> Any:
                await self._hass.services.async_call(
                    domain,
                    service,
                    data,
                    blocking=True,
                )

            try:
                await self._retry.run(lambda: run_with_timeout(_call(), timeout))
                duration_ms = int((time.perf_counter() - start) * 1000)
                return {"status": "ok", "duration_ms": duration_ms}
            except Exception as exc:  # pragma: no cover - failure path
                duration_ms = int((time.perf_counter() - start) * 1000)
                log_debug(self._debug, "Service call failed %s", exc)
                return {
                    "status": "error",
                    "duration_ms": duration_ms,
                    "error_code": exc.__class__.__name__,
                    "details": str(exc),
                }

    async def apply(self, entity_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"entity_id": entity_id, **data}
        return await self._execute(
            "adaptive_lighting", "apply", payload, timeout=SYNC_TIMEOUT
        )

    async def set_manual_control(self, entity_id: str, manual: bool) -> Dict[str, Any]:
        payload = {"entity_id": entity_id, "manual_control": manual}
        return await self._execute(
            "adaptive_lighting", "set_manual_control", payload, timeout=SYNC_TIMEOUT
        )

    async def change_switch_settings(
        self, entity_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        payload = {"entity_id": entity_id, **data}
        return await self._execute(
            "adaptive_lighting",
            "change_switch_settings",
            payload,
            timeout=SYNC_TIMEOUT,
        )

    async def call_light_service(self, service: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._execute("light", service, data, timeout=SCENE_TIMEOUT)
