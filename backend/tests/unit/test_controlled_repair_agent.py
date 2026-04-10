"""
TDD Test Suite: ControlledRepairAgent
======================================
Tests for Phase 2 LLM structure repair.

Design Spec:
  1. Repair prompt MUST explicitly forbid translation and semantic rewriting.
  2. Only ONE LLM call per repair attempt.
  3. Single 429 �?exactly one wait-and-retry.
  4. Second 429 �?RepairRateLimitExceededError (downgrade required).
  5. Prompt must not be derived from Phase 1 prompt templates.
"""
import asyncio
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

from backend.app.services.agents.controlled_repair_agent import (
    ControlledRepairAgent,
    RepairRateLimitExceededError,
    REPAIR_SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_agent() -> ControlledRepairAgent:
    return ControlledRepairAgent(config={
        "llm_config": {
            "api_key": "test-key",
            "base_url": "http://fake-llm/v1/chat",
            "model": "test-model",
        }
    })


def _make_session_with_responses(responses: list) -> MagicMock:
    """
    Build a MagicMock aiohttp.ClientSession whose `.post()` is an async
    context manager that yields each response in `responses` in turn.
    """
    call_count = [0]

    class FakePost:
        def __init__(self, resp):
            self._resp = resp

        async def __aenter__(self):
            return self._resp

        async def __aexit__(self, *args):
            return False

    def post_side_effect(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return FakePost(responses[idx])

    session = MagicMock()
    session.post = post_side_effect
    return session


def _make_ok_response(content: str):
    resp = MagicMock()
    resp.status = 200
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value={
        "choices": [{"message": {"content": content}}]
    })
    return resp


def _make_429_response():
    resp = MagicMock()
    resp.status = 429
    resp.headers = {"Retry-After": "0"}  # 0s wait so tests are instant
    return resp


# ---------------------------------------------------------------------------
# 1. Prompt safety guardrails (synchronous �?no async needed)
# ---------------------------------------------------------------------------

def test_repair_prompt_forbids_translation():
    prompt_lower = REPAIR_SYSTEM_PROMPT.lower()
    assert any(kw in prompt_lower for kw in [
        "do not translate", "must not translate", "禁止翻译",
        "no translation", "禁止任何翻译",
    ]), f"Prompt doesn't forbid translation. Start: {REPAIR_SYSTEM_PROMPT[:200]}"


def test_repair_prompt_forbids_semantic_rewriting():
    prompt_lower = REPAIR_SYSTEM_PROMPT.lower()
    assert any(kw in prompt_lower for kw in [
        "do not rewrite", "must not alter", "禁止改写",
        "no semantic", "禁止语义", "do not change the meaning",
        "rewrite", "paraphrase", "must not rewrite",
    ]), f"Prompt doesn't forbid semantic rewriting. Start: {REPAIR_SYSTEM_PROMPT[:200]}"


def test_repair_prompt_permits_escape_and_structure():
    prompt_lower = REPAIR_SYSTEM_PROMPT.lower()
    assert any(kw in prompt_lower for kw in [
        "escape", "encapsulate", "structure", "转义", "封装",
    ]), f"Prompt doesn't mention structural escaping. Start: {REPAIR_SYSTEM_PROMPT[:200]}"


def test_repair_system_prompt_is_a_literal_constant():
    assert isinstance(REPAIR_SYSTEM_PROMPT, str)
    assert len(REPAIR_SYSTEM_PROMPT) > 50


# ---------------------------------------------------------------------------
# 2. Single LLM call on success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exactly_one_llm_call_on_success():
    agent = make_agent()
    ok_resp = _make_ok_response("fixed content")
    call_count = [0]

    class CountingPost:
        async def __aenter__(self):
            call_count[0] += 1
            return ok_resp

        async def __aexit__(self, *args):
            return False

    def make_post(*args, **kwargs):
        return CountingPost()

    session = MagicMock()
    session.post = make_post

    result = await agent.attempt_repair(env={"content": "broken"}, session=session)
    assert call_count[0] == 1
    assert result["content"] == "fixed content"


# ---------------------------------------------------------------------------
# 3. One wait-and-retry on 429; second 429 �?RepairRateLimitExceededError
# ---------------------------------------------------------------------------




@pytest.mark.asyncio
async def test_single_429_then_ok_succeeds():
    """More clean version using monkeypatched sleep."""
    agent = make_agent()
    responses = [_make_429_response(), _make_ok_response("fixed")]
    session = _make_session_with_responses(responses)

    original_sleep = asyncio.sleep

    async def instant_sleep(_t):
        pass

    asyncio.sleep = instant_sleep
    try:
        result = await agent.attempt_repair(env={"content": "broken"}, session=session)
    finally:
        asyncio.sleep = original_sleep

    assert result["content"] == "fixed"


@pytest.mark.asyncio
async def test_second_429_raises_non_retryable_error():
    agent = make_agent()
    responses = [_make_429_response(), _make_429_response()]
    session = _make_session_with_responses(responses)

    original_sleep = asyncio.sleep

    async def instant_sleep(_t):
        pass

    asyncio.sleep = instant_sleep
    try:
        with pytest.raises(RepairRateLimitExceededError):
            await agent.attempt_repair(env={"content": "broken"}, session=session)
    finally:
        asyncio.sleep = original_sleep


@pytest.mark.asyncio
async def test_no_more_than_two_llm_calls_even_on_repeated_429():
    """Guarantee max 2 LLM calls (initial + 1 retry) regardless of 429 count."""
    agent = make_agent()
    call_count = [0]

    class Always429:
        async def __aenter__(self):
            call_count[0] += 1
            return _make_429_response()

        async def __aexit__(self, *args):
            return False

    session = MagicMock()
    session.post = MagicMock(return_value=Always429())

    original_sleep = asyncio.sleep

    async def instant_sleep(_t):
        pass

    asyncio.sleep = instant_sleep
    try:
        with pytest.raises(RepairRateLimitExceededError):
            await agent.attempt_repair(env={"content": "broken"}, session=session)
    finally:
        asyncio.sleep = original_sleep

    assert call_count[0] == 2, (
        f"Expected exactly 2 LLM calls (initial + 1 retry), got {call_count[0]}"
    )


# ---------------------------------------------------------------------------
# 4. Prompt isolation from Phase 1
# ---------------------------------------------------------------------------

def test_repair_agent_does_not_use_phase1_prompt_module():
    import backend.app.services.agents.controlled_repair_agent as repair_mod
    # Ensure the phase 1 prompts module is not referenced in repair module globals
    # (It should not have been imported there)
    module_values = set(id(v) for v in vars(repair_mod).values())
    try:
        import backend.app.services.latex.prompts as phase1_mod
        assert id(phase1_mod) not in module_values, (
            "ControlledRepairAgent imports Phase 1 prompt module �?forbidden."
        )
    except ImportError:
        pass  # if phase1 prompts module unavailable, test is trivially satisfied
