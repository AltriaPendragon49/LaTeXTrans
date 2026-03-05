# Agent services
import asyncio
from typing import Optional

# ── INFRA GUARD (Safety Net) ─────────────────────────────────────────────────
# global_llm_semaphore caps total concurrent outbound LLM API requests.
#
# ROLE: Infrastructure-level protection against system resource exhaustion.
#       It must NEVER be used to make business scheduling decisions.
#
# STRICT PROHIBITION:
#   - MUST NOT influence Phase 2 (ControlledRepairWorkflow) repair scheduling.
#   - MUST NOT trigger Phase 3 downgrade decisions.
#   - MUST NOT act as a token-scoped rate limiter.
#   - MUST NOT consume or count repair opportunities.
#
# For Phase 2 business scheduling, use TokenRepairScheduler instead.
# See: backend/app/services/translation/repair_scheduler.py
#
# The value is read from Settings lazily on first use.

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
