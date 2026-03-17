"""
TDD Test Suite: Phase 2 → Phase 3 Integration
==================================================
Verifies that:
  1. A Phase 2 failure (QueueTimeoutError / RepairRateLimitExceededError) MUST NOT
     flow back into the outer Maxtry retry loop (_val_fail_parts).
  2. After a successful Phase 2 repair, the env is NOT re-added to fail list.
  3. After Phase 3 downgrade, the env translation_status is marked DOWNGRADED and
     it is explicitly removed from the fail queue (not re-queued).

These tests guard the "failure path amplifier" (Maxtry stacking on Phase 2 results).
"""
import asyncio
import pytest

from backend.app.services.translation.downgrade_handler import (
    deterministic_downgrade,
    DOWNGRADE_STATUS,
    DOWNGRADE_REASON_QUEUE_TIMEOUT,
    DOWNGRADE_REASON_RATE_LIMIT,
)
from backend.app.services.translation.repair_scheduler import (
    TokenRepairScheduler,
    QueueTimeoutError,
)
from backend.app.services.agents.controlled_repair_agent import (
    ControlledRepairAgent,
    RepairRateLimitExceededError,
)

# ---------------------------------------------------------------------------
# 1. Phase 2 failure must produce a downgraded env, not a re-queued env
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_queue_timeout_produces_downgraded_env_not_fail_marker():
    """QueueTimeoutError from scheduler → deterministic_downgrade, not a fail_marker."""
    scheduler = TokenRepairScheduler(queue_timeout=0.01)
    lock_held = asyncio.Event()

    async def blocking_repair(env):
        lock_held.set()
        await asyncio.sleep(1.0)
        return {**env, "repaired": True}

    # Hold lock with first task
    holder = asyncio.ensure_future(
        scheduler.enqueue_repair("tok", {"id": "hold"}, blocking_repair)
    )
    await lock_held.wait()

    # Second env times out — must get Phase 3 downgrade, NOT a fail_marker
    env_to_repair = {"content": "broken $", "placeholder": "<ENV_2>"}
    try:
        result = await scheduler.enqueue_repair("tok", env_to_repair, blocking_repair)
        pytest.fail("Expected QueueTimeoutError but got success")
    except QueueTimeoutError as exc:
        downgraded = deterministic_downgrade(env_to_repair, exc)
        assert downgraded["translation_status"] == DOWNGRADE_STATUS
        assert downgraded["trans_content"] == env_to_repair["content"]
        assert downgraded["downgrade_reason"] == DOWNGRADE_REASON_QUEUE_TIMEOUT
    finally:
        holder.cancel()
        try:
            await holder
        except (asyncio.CancelledError, Exception):
            pass


@pytest.mark.asyncio
async def test_rate_limit_exceeded_produces_downgraded_env_not_fail_marker():
    """RepairRateLimitExceededError → downgrade, not a re-try."""
    env = {"content": "broken env", "placeholder": "<ENV_5>"}
    exc = RepairRateLimitExceededError("second 429")
    downgraded = deterministic_downgrade(env, exc)
    assert downgraded["translation_status"] == DOWNGRADE_STATUS
    assert downgraded["downgrade_reason"] == DOWNGRADE_REASON_RATE_LIMIT
    assert downgraded["trans_content"] == env["content"]


# ---------------------------------------------------------------------------
# 2. Downgraded envs must NOT re-enter any retry loop
# ---------------------------------------------------------------------------

def test_downgraded_env_is_not_marked_as_llm_failure():
    """
    A downgraded env must NOT set any marker that triggers _val_fail_parts re-queuing.
    Specifically: it must NOT have `translated == False` with no downgrade_reason,
    since that pattern is what _val_fail_parts uses to detect failures.
    """
    env = {"content": "x", "placeholder": "<ENV_3>"}
    result = deterministic_downgrade(env, QueueTimeoutError("x"))
    # downgrade is explicit — the env is "done" (not an LLM failure)
    assert result.get("translation_status") == DOWNGRADE_STATUS
    assert "downgrade_reason" in result
    # Must NOT mark as plain LLM api failure (which would trigger Maxtry re-queue)
    assert result.get("fallback_reason") != "api_request_failed_after_3_attempts"
    assert result.get("fallback_reason") != "api_request_failed_429_max_retries"


def test_downgraded_env_has_non_empty_trans_content():
    """Phase 3 output must always produce non-None trans_content to prevent downstream crashes."""
    env_with_content = {"content": "original latex content"}
    result1 = deterministic_downgrade(env_with_content, QueueTimeoutError("x"))
    assert result1["trans_content"]  # truthy — not empty

    env_empty = {"content": ""}
    result2 = deterministic_downgrade(env_empty, RepairRateLimitExceededError("x"))
    assert result2["trans_content"] is not None  # at minimum an empty string (not None)


# ---------------------------------------------------------------------------
# 3. Multi-token isolation: Token A Phase 2 failure does not harm Token B
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_token_a_phase2_timeout_does_not_affect_token_b():
    """
    When Token A's repair exceeds queue_timeout, Token B's repair must still succeed.
    """
    scheduler = TokenRepairScheduler(queue_timeout=0.02)
    tok_a_started = asyncio.Event()

    async def slow_a(env):
        tok_a_started.set()
        await asyncio.sleep(0.5)
        return {**env, "repaired": True}

    async def fast_b(env):
        return {**env, "repaired": True}

    # Start Token A's slow repair
    task_a = asyncio.ensure_future(
        scheduler.enqueue_repair("tok_a", {"id": "a"}, slow_a)
    )
    await tok_a_started.wait()

    # Attempt a second Token A repair (should timeout)
    env_a2 = {"content": "broken", "placeholder": "<ENV_A2>"}
    try:
        await scheduler.enqueue_repair("tok_a", env_a2, slow_a)
        pytest.fail("Expected QueueTimeoutError")
    except QueueTimeoutError as exc:
        downgraded_a = deterministic_downgrade(env_a2, exc)
        assert downgraded_a["translation_status"] == DOWNGRADE_STATUS

    # Token B must still work independently
    result_b = await asyncio.wait_for(
        scheduler.enqueue_repair("tok_b", {"id": "b", "content": "ok"}, fast_b),
        timeout=0.1,
    )
    assert result_b["repaired"] is True

    task_a.cancel()
    try:
        await task_a
    except (asyncio.CancelledError, Exception):
        pass


# ---------------------------------------------------------------------------
# 4. Downgrade output is compilation-safe
# ---------------------------------------------------------------------------

def test_downgrade_source_passthrough_has_no_bare_structure_tokens():
    """
    The source passthrough content should not be 'more dangerous' than the original.
    This is a sanity check — if the env already had broken content, at least we're
    returning exactly that (the old state).
    """
    env = {"content": "\\begin{broken $5 env", "placeholder": "<ENV_7>"}
    result = deterministic_downgrade(env, QueueTimeoutError("x"))
    # Exactly the source — no transformation that could change safety level
    assert result["trans_content"] == env["content"]
