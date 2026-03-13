import asyncio
from typing import Optional

from backend.app.core.config import get_settings

_compile_semaphore: Optional[asyncio.Semaphore] = None


def get_compile_semaphore() -> asyncio.Semaphore:
    global _compile_semaphore
    if _compile_semaphore is None:
        limit = int(get_settings().max_concurrent_compilations or 1)
        if limit < 1:
            limit = 1
        _compile_semaphore = asyncio.Semaphore(limit)
    return _compile_semaphore

