"""
Token-Scoped Repair Scheduler
===============================
Implements the business-level concurrency control for Phase 2 repairs.

Semantic contract (from OpenSpec ControlledRepairWorkflow):
  - One FIFO queue per API token — completely independent.
  - At most 1 active Phase 2 repair per token at any time (strict serial).
  - Queue-WAIT hard timeout: if an env waits longer than `queue_timeout`
    to *acquire* the per-token slot, it raises QueueTimeoutError.
    NOTE: LLM execution time after acquiring the slot does NOT count.
  - Token A's state (busy, 429, failed) MUST NOT affect Token B.
  - Phase 1 gather helper runs independently, never blocked by Phase 2 queues.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List

logger = logging.getLogger(__name__)


class QueueTimeoutError(Exception):
    """Raised when an env waits too long to acquire its token's repair slot."""


class TokenRepairScheduler:
    """
    Manages per-token repair scheduling with queue-wait hard timeouts.

    Usage:
        scheduler = TokenRepairScheduler(queue_timeout=30.0)
        result = await scheduler.enqueue_repair(token, env, repair_fn)
    """

    def __init__(self, queue_timeout: float = 30.0) -> None:
        """
        Args:
            queue_timeout: Maximum seconds an env may wait in the per-token
                           queue before raising QueueTimeoutError.
                           Time starts when enqueue_repair() is called and
                           stops when the repair slot is acquired.
                           LLM execution time is NOT included.
        """
        self._queue_timeout = queue_timeout
        # Per-token asyncio.Lock — ensures strict serial execution per token.
        # Created lazily: a new token gets a fresh Lock on first use.
        self._token_locks: Dict[str, asyncio.Lock] = {}
        self._locks_meta_lock = asyncio.Lock()  # guards _token_locks dict itself

    async def _get_or_create_lock(self, token: str) -> asyncio.Lock:
        """Return (or lazily create) the per-token Lock."""
        async with self._locks_meta_lock:
            if token not in self._token_locks:
                self._token_locks[token] = asyncio.Lock()
            return self._token_locks[token]

    async def enqueue_repair(
        self,
        token: str,
        env: Dict[str, Any],
        repair_fn: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Enqueue `env` for Phase 2 repair under `token`.

        Args:
            token:     API token identifier (used as the isolation key).
            env:       The environment dict to be repaired.
            repair_fn: Async callable (env) -> repaired_env.
                       This is where the actual LLM call happens.

        Returns:
            The repaired env dict as returned by repair_fn.

        Raises:
            QueueTimeoutError: If the env waits longer than `queue_timeout`
                               to acquire the per-token slot.
            Propagates any exception raised by repair_fn.
        """
        lock = await self._get_or_create_lock(token)
        env_id = env.get("id", "<unknown>")

        try:
            # Wait to acquire the per-token lock within the queue timeout.
            await asyncio.wait_for(lock.acquire(), timeout=self._queue_timeout)
        except asyncio.TimeoutError:
            logger.warning(
                "Token %s: env %s timed out waiting for repair slot after %.1fs — downgrading.",
                token, env_id, self._queue_timeout,
            )
            raise QueueTimeoutError(
                f"Token '{token}' repair slot not available within {self._queue_timeout}s "
                f"for env '{env_id}'. Downgrade to Phase 3 required."
            )

        # Slot acquired — LLM execution time is NOT subject to queue_timeout.
        try:
            logger.debug("Token %s: starting Phase 2 repair for env %s", token, env_id)
            result = await repair_fn(env)
            logger.debug("Token %s: repair of env %s succeeded.", token, env_id)
            return result
        finally:
            lock.release()

    async def run_phase1_gather(
        self,
        envs: List[Dict[str, Any]],
        translate_fn: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """
        Run Phase 1 translations concurrently via asyncio.gather.
        This helper is purposefully decoupled from any Phase 2 queue.

        Args:
            envs:         List of safe env dicts to translate.
            translate_fn: Async callable (env) -> translated_env.

        Returns:
            List of translated env dicts (order preserved).
        """
        tasks = [translate_fn(env) for env in envs]
        return list(await asyncio.gather(*tasks))
