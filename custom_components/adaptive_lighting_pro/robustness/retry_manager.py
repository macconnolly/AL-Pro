"""Retry helpers."""
from __future__ import annotations

import asyncio
import random
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class RetryManager:
    """Retry helper supporting exponential backoff with jitter."""

    def __init__(self, attempts: int, backoffs: list[int]) -> None:
        self._attempts = attempts
        self._backoffs = backoffs

    async def run(self, coro_factory: Callable[[], Awaitable[T]]) -> T:
        last_exc: Exception | None = None
        for attempt in range(1, self._attempts + 1):
            try:
                return await coro_factory()
            except Exception as exc:  # pragma: no cover - we assert raising in tests
                last_exc = exc
                if attempt == self._attempts:
                    raise
                backoff = self._backoffs[min(attempt - 1, len(self._backoffs) - 1)]
                jitter = random.uniform(0, 0.25)
                await asyncio.sleep(backoff + jitter)
        assert last_exc is not None  # pragma: no cover
        raise last_exc
