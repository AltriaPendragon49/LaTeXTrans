"""
Tests for TranslatorAgent intra-section parallelization (Task 7 & 8).

This test module uses environment variable injection so that pydantic Settings
can initialize without a real .env file.
"""

import asyncio
import pytest
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

# Inject required env vars before any backend imports
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://mock-api/v1/chat/completions")
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("SUPABASE_URL", "http://mock-supabase")
os.environ.setdefault("SUPABASE_ANON_KEY", "mock-anon-key")


def _make_config():
    return {
        "llm_config": {
            "api_key": "test-key",
            "base_url": "http://mock-api/v1/chat/completions",
            "model": "test-model",
        },
        "source_language": "en",
        "target_language": "zh",
        "user_term": None,
        "update_term": False,
    }


def _make_section(num: str, content: str):
    return {"section": num, "content": content}


def _make_env(placeholder: str, content: str, need_trans: bool = True):
    return {"placeholder": placeholder, "content": content, "need_trans": need_trans}


def _make_caption(placeholder: str, content: str):
    return {"placeholder": placeholder, "content": content}


def _make_agent():
    from backend.app.services.agents.translator_agent import TranslatorAgent
    return TranslatorAgent(config=_make_config(), trans_mode=0, project_dir="/tmp", output_dir="/tmp")


# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_translate_envs_run_concurrently():
    """
    Phase 2: all environments of a section should be translated concurrently.
    Timing check: ≥2 tasks must start before the first one finishes.
    """
    agent = _make_agent()
    start_times: list = []
    finish_times: list = []

    async def slow_env(env, session, error_message=None):
        start_times.append(time.monotonic())
        await asyncio.sleep(0.05)
        finish_times.append(time.monotonic())
        return {**env, "trans_content": "[OK]"}

    section = _make_section("1", "<PLACEHOLDER_ENV_1> <PLACEHOLDER_ENV_2> <PLACEHOLDER_ENV_3>")
    envs = [
        _make_env("<PLACEHOLDER_ENV_1>", "E1"),
        _make_env("<PLACEHOLDER_ENV_2>", "E2"),
        _make_env("<PLACEHOLDER_ENV_3>", "E3"),
    ]

    with patch.object(agent, "_translate_section", AsyncMock(return_value=section)), \
         patch.object(agent, "_translate_env", side_effect=slow_env), \
         patch.object(agent, "_translate_caption", AsyncMock()):
        await agent.translate(section, envs, [], MagicMock())

    assert len(start_times) == 3
    first_finish = min(finish_times)
    concurrent = sum(t < first_finish for t in start_times)
    assert concurrent >= 2, f"Expected ≥2 concurrent env starts, got {concurrent}"


@pytest.mark.asyncio
async def test_translate_captions_run_concurrently():
    """
    Phase 3: all captions of a section should be translated concurrently.
    """
    agent = _make_agent()
    start_times: list = []
    finish_times: list = []

    async def slow_cap(caption, session, error_message=None):
        start_times.append(time.monotonic())
        await asyncio.sleep(0.05)
        finish_times.append(time.monotonic())
        return {**caption, "trans_content": "[OK]"}

    section = _make_section("1", "<PLACEHOLDER_CAP_1> <PLACEHOLDER_CAP_2> <PLACEHOLDER_CAP_3>")
    captions = [
        _make_caption("<PLACEHOLDER_CAP_1>", "C1"),
        _make_caption("<PLACEHOLDER_CAP_2>", "C2"),
        _make_caption("<PLACEHOLDER_CAP_3>", "C3"),
    ]

    with patch.object(agent, "_translate_section", AsyncMock(return_value=section)), \
         patch.object(agent, "_translate_caption", side_effect=slow_cap):
        await agent.translate(section, [], captions, MagicMock())

    assert len(start_times) == 3
    first_finish = min(finish_times)
    concurrent = sum(t < first_finish for t in start_times)
    assert concurrent >= 2, f"Expected ≥2 concurrent caption starts, got {concurrent}"


@pytest.mark.asyncio
async def test_captions_inside_envs_are_discovered():
    """
    A caption placeholder inside env content must be picked up in Phase 2
    and translated in Phase 3, even if not referenced directly in the section.
    """
    agent = _make_agent()
    translated_cap_phs: list = []

    async def mock_env(env, session, error_message=None):
        return {**env, "trans_content": "[ENV OK]"}

    async def mock_cap(caption, session, error_message=None):
        translated_cap_phs.append(caption["placeholder"])
        return {**caption, "trans_content": "[CAP OK]"}

    section = _make_section("1", "<PLACEHOLDER_ENV_1>")
    envs = [_make_env("<PLACEHOLDER_ENV_1>", "Env with <PLACEHOLDER_CAP_99>")]
    captions = [_make_caption("<PLACEHOLDER_CAP_99>", "Hidden caption")]

    with patch.object(agent, "_translate_section", AsyncMock(return_value=section)), \
         patch.object(agent, "_translate_env", side_effect=mock_env), \
         patch.object(agent, "_translate_caption", side_effect=mock_cap):
        await agent.translate(section, envs, captions, MagicMock())

    assert "<PLACEHOLDER_CAP_99>" in translated_cap_phs, \
        "Caption nested inside env must be discovered and translated"


@pytest.mark.asyncio
async def test_global_semaphore_limits_concurrency():
    """
    asyncio.Semaphore(N) keeps concurrent count ≤ N at all times.
    """
    sem = asyncio.Semaphore(2)
    max_concurrent = 0
    current = 0

    async def task():
        nonlocal max_concurrent, current
        async with sem:
            current += 1
            max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0.02)
            current -= 1

    await asyncio.gather(*[task() for _ in range(8)])
    assert max_concurrent <= 2, f"Semaphore(2) violated: got {max_concurrent} concurrent"
