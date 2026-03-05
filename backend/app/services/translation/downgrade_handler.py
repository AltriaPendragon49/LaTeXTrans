"""
Phase 3: Deterministic Downgrade Handler
==========================================
Handles all Phase 2 failure outcomes without any LLM involvement.

Design contract (from OpenSpec accelerate-translation-workflow design.md §1 Phase 3):
  - NO LLM calls. This function MUST be synchronous and deterministic.
  - Source passthrough is the primary strategy (safest, always compilable).
  - All original env fields are preserved.
  - Sets translation_status = DOWNGRADE_STATUS.
  - Sets downgrade_reason to one of the canonical reason constants.

Triggered by:
  - QueueTimeoutError (Phase 2 排队硬超时)
  - RepairRateLimitExceededError (Phase 2 第二次 429 弃权)
  - Any other unexpected Phase 2 exception

CRITICAL: This function MUST NOT be re-entered by the outer Maxtry loop.
The caller is responsible for ensuring that envs with DOWNGRADE_STATUS are
excluded from the _val_fail_parts retry queue.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.app.services.translation.repair_scheduler import QueueTimeoutError
from backend.app.services.agents.controlled_repair_agent import (
    RepairRateLimitExceededError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical status and reason constants
# ---------------------------------------------------------------------------

# The translation_status value for all Phase 3 downgraded envs.
# The outer code must check for this exact string to skip Maxtry re-queuing.
DOWNGRADE_STATUS = "PHASE3_DETERMINISTIC_DOWNGRADE"

# Canonical downgrade_reason values — one per failure origin
DOWNGRADE_REASON_QUEUE_TIMEOUT = "phase2_queue_timeout"
DOWNGRADE_REASON_RATE_LIMIT = "phase2_rate_limit_exceeded"
DOWNGRADE_REASON_REPAIR_FAILED = "phase2_repair_failed_unexpected"

# Safe placeholder comment used when source content is empty
_EMPTY_CONTENT_PLACEHOLDER = "% [LaTeX-Trans: Phase 3 downgrade — original content was empty]"


def deterministic_downgrade(
    env: Dict[str, Any],
    exc: Optional[Exception] = None,
) -> Dict[str, Any]:
    """
    Phase 3 deterministic downgrade: return a compilation-safe version of `env`
    without any LLM involvement.

    Strategy: Source passthrough — `trans_content` is set to the original `content`.
    If `content` is empty, a safe placeholder comment is used instead.

    Args:
        env: The original env dict (must have at least a 'content' key).
        exc: The exception that triggered the downgrade (used to set reason).

    Returns:
        A new dict with all original fields preserved, plus:
          - `trans_content`: safe source passthrough (or placeholder if empty)
          - `translation_status`: DOWNGRADE_STATUS
          - `downgrade_reason`: canonical reason string
    """
    result = dict(env)  # preserve all original fields

    # Determine downgrade reason from exception type
    if isinstance(exc, QueueTimeoutError):
        reason = DOWNGRADE_REASON_QUEUE_TIMEOUT
    elif isinstance(exc, RepairRateLimitExceededError):
        reason = DOWNGRADE_REASON_RATE_LIMIT
    else:
        reason = DOWNGRADE_REASON_REPAIR_FAILED

    # Source passthrough — always compilable (it's the source LaTeX as-is)
    source_content = env.get("content", "")
    if not source_content:
        source_content = _EMPTY_CONTENT_PLACEHOLDER

    result["trans_content"] = source_content
    result["translation_status"] = DOWNGRADE_STATUS
    result["downgrade_reason"] = reason

    logger.info(
        "Phase 3 downgrade: placeholder=%s reason=%s exc=%s",
        env.get("placeholder", "(no placeholder)"),
        reason,
        type(exc).__name__ if exc is not None else "None",
    )

    return result
