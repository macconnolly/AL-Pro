"""Async timeout helpers."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


@asynccontextmanager
def timeboxed(timeout: float) -> AsyncIterator[None]:
    """Context manager that enforces timeout using asyncio.wait_for."""
    try:
        yield
    except asyncio.TimeoutError:
        raise


async def run_with_timeout(coro, timeout: float):
    """Run coroutine with timeout."""
    return await asyncio.wait_for(coro, timeout=timeout)
