"""
Controlled Repair Agent (Phase 2)
===================================
A strictly isolated LLM agent for one-shot structural repair of unsafe envs.

Design contract (from OpenSpec ControlledRepairWorkflow):
  - ONE LLM call per repair attempt (no Phase 1 retranslation).
  - A SINGLE 429 → one wait-and-retry is permitted.
  - A SECOND 429 → raises RepairRateLimitExceededError (must downgrade to Phase 3).
  - The system prompt MUST explicitly forbid translation and semantic rewriting.
  - This module MUST NOT import or reference Phase 1 prompt templates.
  - Separate file, separate tests, separate code-review — absolute isolation.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import aiohttp
from .llm_runtime import build_llm_client_timeout, resolve_llm_timeout

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# REPAIR_SYSTEM_PROMPT — SAFETY BOUNDARY.
# This prompt must NEVER be derived from Phase 1 prompt templates.
# Any change to this constant requires a dedicated code review.
# ---------------------------------------------------------------------------
REPAIR_SYSTEM_PROMPT = (
    "You are a LaTeX structure repair tool. "
    "Your ONLY task is to fix broken LaTeX syntax — specifically: "
    "escape unescaped special characters (e.g. $ → \\$, _ → \\_), "
    "encapsulate or wrap malformed environment delimiters, "
    "and insert placeholder markers for unresolvable tokens. "
    "\n\n"
    "ABSOLUTE PROHIBITIONS — violating these rules is a critical failure:\n"
    "1. You MUST NOT translate any text. Do not translate into any language.\n"
    "2. You MUST NOT rewrite, paraphrase, summarize, or alter the meaning or semantics of any text.\n"
    "3. You MUST NOT change the content or order of words.\n"
    "4. You MUST NOT add or remove information.\n"
    "\n"
    "ONLY perform minimal structural escaping and encapsulation. "
    "Return ONLY the repaired LaTeX content without any explanation."
)

# Maximum seconds to wait on a Retry-After hint from a 429 response.
_MAX_WAIT_SECONDS = 15


class RepairRateLimitExceededError(Exception):
    """
    Raised when Phase 2 repair receives a second consecutive 429.
    The caller MUST immediately route this env to Phase 3 downgrade.
    This is a definitive, non-retryable error.
    """


class ControlledRepairAgent:
    """
    Phase 2 structural repair agent.

    Usage:
        agent = ControlledRepairAgent(config=config)
        async with aiohttp.ClientSession() as session:
            result = await agent.attempt_repair(env=env, session=session)
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        llm_cfg = config.get("llm_config", {}) or {}
        self._config = config
        self._api_key: str = llm_cfg.get("api_key", "")
        self._base_url: str = llm_cfg.get("base_url", "")
        self._model: str = llm_cfg.get("model", "gpt-4o")
        self._timeout_seconds: int = resolve_llm_timeout(config, default=120)

    def _build_payload(self, content: str) -> Dict[str, Any]:
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "temperature": 0.0,  # deterministic — structure repair only
            "max_new_tokens": 4096,
        }

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def attempt_repair(
        self,
        env: Dict[str, Any],
        session: aiohttp.ClientSession,
    ) -> Dict[str, Any]:
        """
        Attempt to repair the structural issues in `env` with a single LLM call.

        - If the first call succeeds: return the repaired env.
        - If the first call returns 429: wait and retry EXACTLY ONCE.
        - If the retry also returns 429: raise RepairRateLimitExceededError.
        - All other HTTP errors are re-raised as-is.

        Args:
            env:     The environment dict (must have a 'content' key).
            session: An active aiohttp.ClientSession.

        Returns:
            A copy of `env` with 'content' replaced by the repaired text.

        Raises:
            RepairRateLimitExceededError: on a second consecutive 429.
            aiohttp.ClientResponseError: on other fatal HTTP errors.
        """
        content = env.get("content", "")
        payload = self._build_payload(content)
        headers = self._build_headers()
        timeout = build_llm_client_timeout(self._config, default=self._timeout_seconds)

        repaired_content = await self._call_once_with_single_retry(
            session=session,
            payload=payload,
            headers=headers,
            timeout=timeout,
        )

        return {**env, "content": repaired_content}

    async def _call_once_with_single_retry(
        self,
        *,
        session: aiohttp.ClientSession,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        timeout: aiohttp.ClientTimeout,
    ) -> str:
        """
        Make ONE LLM call. On a single 429, wait and retry once.
        On a second 429, raise RepairRateLimitExceededError.
        """
        for attempt in range(2):  # attempt 0 = initial, attempt 1 = single retry
            async with session.post(
                self._base_url, json=payload, headers=headers, timeout=timeout
            ) as resp:
                if resp.status == 429:
                    if attempt == 1:
                        # Second consecutive 429 — non-retryable
                        raise RepairRateLimitExceededError(
                            "Phase 2 repair received 429 on both the initial call "
                            "and the single permitted retry. Downgrade required."
                        )
                    # First 429 — wait the Retry-After hint (capped)
                    retry_after_raw = resp.headers.get("Retry-After", "")
                    wait = min(
                        int(retry_after_raw) if retry_after_raw.isdigit() else 5,
                        _MAX_WAIT_SECONDS,
                    )
                    logger.warning(
                        "ControlledRepairAgent: 429 on initial attempt, waiting %ss before single retry.",
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue  # → attempt 1

                resp.raise_for_status()
                result = await resp.json()
                return result["choices"][0]["message"]["content"].strip()

        # Should be unreachable (loop exits via raise or return)
        raise RepairRateLimitExceededError("Unexpected code path in ControlledRepairAgent.")
