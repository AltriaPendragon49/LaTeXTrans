from __future__ import annotations

import asyncio
from typing import Callable, Optional, TypeVar

from backend.app.core.config import get_settings

T = TypeVar("T")


def _wrappers_enabled() -> bool:
    return bool(get_settings().async_blocking_wrappers_enabled)


def _db_mode() -> str:
    mode = str(get_settings().db_execution_mode or "per_call_client").strip().lower()
    if mode not in {"per_call_client", "shared_client"}:
        return "per_call_client"
    return mode


async def run_blocking(func: Callable[[], T]) -> T:
    """
    Run a blocking callable without pinning the event loop.
    """
    if not _wrappers_enabled():
        return func()
    return await asyncio.to_thread(func)


async def run_db_blocking(
    shared_call: Callable[[], T],
    *,
    per_call_client_call: Optional[Callable[[], T]] = None,
) -> T:
    """
    Execute blocking DB SDK call with execution-mode policy.

    - per_call_client (default): create short-lived client per threaded call.
    - shared_client: reuse existing client object in threaded call.
    """
    if not _wrappers_enabled():
        return shared_call()

    mode = _db_mode()
    if mode == "per_call_client" and per_call_client_call is not None:
        return await asyncio.to_thread(per_call_client_call)

    return await asyncio.to_thread(shared_call)

