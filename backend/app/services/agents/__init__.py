# Agent services
import asyncio
from typing import Optional

# Global semaphore to cap total concurrent outbound LLM API requests.
# This single lock spans ALL tasks and ALL users, ensuring the backend
# never exceeds the provider's concurrent-request limit
# (e.g. NVIDIA NIM free-tier: ~40 RPM).
#
# The value is read from Settings lazily on first use to avoid importing
# Settings at module load time (which would require a .env file even in tests).
_global_llm_semaphore: Optional[asyncio.Semaphore] = None


def _get_llm_semaphore() -> asyncio.Semaphore:
    """Return the global LLM semaphore, creating it on first call."""
    global _global_llm_semaphore
    if _global_llm_semaphore is None:
        try:
            from backend.app.core.config import settings
            limit = settings.llm_max_concurrent_requests
        except Exception:
            limit = 30  # safe fallback if settings unavailable (e.g. in tests)
        _global_llm_semaphore = asyncio.Semaphore(limit)
    return _global_llm_semaphore


class _SemaphoreProxy:
    """
    Proxy that forwards `async with` to the lazily-created global semaphore.
    This allows `async with global_llm_semaphore:` to work naturally in code
    while deferring actual Semaphore creation until the event loop is running.
    """
    async def __aenter__(self):
        return await _get_llm_semaphore().__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await _get_llm_semaphore().__aexit__(exc_type, exc_val, exc_tb)


# Public interface used by translator_agent.py
global_llm_semaphore: _SemaphoreProxy = _SemaphoreProxy()
