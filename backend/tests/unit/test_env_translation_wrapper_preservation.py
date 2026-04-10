import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from backend.app.services.agents.translator_agent import TranslatorAgent


def _build_agent(tmp_path: Path) -> TranslatorAgent:
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    agent = TranslatorAgent(
        config={
            "llm_config": {
                "model": "gpt-4o",
                "base_url": "http://dummy",
                "api_key": "dummy",
            },
            "model_context_tokens": 1000,
            "prompt_reserve_tokens": 100,
            "target_language": "zh",
            "source_language": "en",
        },
        project_dir=str(tmp_path / "project"),
        output_dir=str(output_dir),
        trans_mode=0,
    )
    agent.prompts = {
        "section_system_prompt": "translate section",
        "section_system_prompt_with_dict": "translate section with dict",
        "retrans_error_parts_system_prompt": "retry",
        "caption_system_prompt": "translate caption",
        "caption_system_prompt_with_dict": "translate caption with dict",
        "env_system_prompt": "translate env",
        "env_system_prompt_with_dict": "translate env with dict",
        "extract_terminology_system_prompt": "extract terms",
    }
    return agent


def test_generic_text_env_preserves_source_wrapper(tmp_path: Path):
    agent = _build_agent(tmp_path)
    env = {
        "placeholder": "<PLACEHOLDER_ENV_1>",
        "env_name": "abstract",
        "content": "\\begin{abstract}\nHello world.\n\\end{abstract}\n",
        "need_trans": True,
    }
    agent._request_env_translation = AsyncMock(return_value="你好，世界。\n")

    result = asyncio.run(agent._translate_env(env, MagicMock()))

    assert result["translation_status"] == agent.STATUS_TRANSLATED
    assert result["trans_content"].startswith("\\begin{abstract}")
    assert result["trans_content"].endswith("\\end{abstract}\n")
    assert "你好，世界�? in result["trans_content"]


def test_generic_text_env_falls_back_to_source_body_when_env_tokens_leak(tmp_path: Path):
    agent = _build_agent(tmp_path)
    env = {
        "placeholder": "<PLACEHOLDER_ENV_2>",
        "env_name": "abstract",
        "content": "\\begin{abstract}\nHello world.\n\\end{abstract}\n",
        "need_trans": True,
    }
    agent._request_env_translation = AsyncMock(return_value="<ENV_BEGIN_1>broken<ENV_END_1>")

    result = asyncio.run(agent._translate_env(env, MagicMock()))

    assert result["translation_status"] == agent.STATUS_FALLBACK_SOURCE_API_FAILURE
    assert result["fallback_reason"] == "env_wrapper_restore_preserved_source"
    assert result["trans_content"] == env["content"]
    assert "<ENV_BEGIN_" not in result["trans_content"]


def test_generic_text_env_retries_after_env_token_leak(tmp_path: Path):
    agent = _build_agent(tmp_path)
    env = {
        "placeholder": "<PLACEHOLDER_ENV_2_retry>",
        "env_name": "abstract",
        "content": "\\begin{abstract}\nHello world.\n\\end{abstract}\n",
        "need_trans": True,
    }
    agent._request_env_translation = AsyncMock(
        side_effect=["<ENV_BEGIN_1>broken<ENV_END_1>", "你好，世界。\n"]
    )

    result = asyncio.run(agent._translate_env(env, MagicMock()))

    assert result["translation_status"] == agent.STATUS_TRANSLATED
    assert result["trans_content"].startswith("\\begin{abstract}")
    assert result["trans_content"].endswith("\\end{abstract}\n")
    assert "你好，世界�? in result["trans_content"]
    assert agent._request_env_translation.await_count == 2


def test_generic_text_env_uses_plain_text_recovery_after_repeated_env_token_leak(tmp_path: Path):
    agent = _build_agent(tmp_path)
    env = {
        "placeholder": "<PLACEHOLDER_ENV_2_plain_recover>",
        "env_name": "abstract",
        "content": "\\begin{abstract}\nHello world.\n\\end{abstract}\n",
        "need_trans": True,
    }
    agent._request_env_translation = AsyncMock(
        side_effect=["<ENV_BEGIN_1>broken<ENV_END_1>", "<ENV_BEGIN_1>still-broken<ENV_END_1>"]
    )
    agent._request_llm_for_trans = AsyncMock(return_value="你好，世界。\n")

    result = asyncio.run(agent._translate_env(env, MagicMock()))

    assert result["translation_status"] == agent.STATUS_TRANSLATED
    assert result["trans_content"].startswith("\\begin{abstract}")
    assert result["trans_content"].endswith("\\end{abstract}\n")
    assert "你好，世界�? in result["trans_content"]
    assert agent._request_env_translation.await_count == 2
    agent._request_llm_for_trans.assert_awaited()


def test_generic_text_env_uses_plain_text_recovery_after_api_source_fallback(tmp_path: Path):
    agent = _build_agent(tmp_path)
    env = {
        "placeholder": "<PLACEHOLDER_ENV_2_api_recover>",
        "env_name": "abstract",
        "content": "\\begin{abstract}\nHello world.\n\\end{abstract}\n",
        "need_trans": True,
    }

    async def _fallback_to_source(*args, **kwargs):
        agent._mark_api_fallback("env", env["placeholder"], "invariant_command_mismatch")
        return "Hello world.\n"

    agent._request_env_translation = AsyncMock(side_effect=_fallback_to_source)
    agent._request_llm_for_trans = AsyncMock(return_value="你好，世界。\n")

    result = asyncio.run(agent._translate_env(env, MagicMock()))

    assert result["translation_status"] == agent.STATUS_TRANSLATED
    assert result["trans_content"].startswith("\\begin{abstract}\n")
    assert "你好，世界�? in result["trans_content"]
    assert "Hello world." not in result["trans_content"]
    agent._request_llm_for_trans.assert_awaited()


def test_generic_text_env_uses_paragraph_rescue_after_plain_text_recovery_still_noops(tmp_path: Path):
    agent = _build_agent(tmp_path)
    env = {
        "placeholder": "<PLACEHOLDER_ENV_2_para_recover>",
        "env_name": "abstract",
        "content": "\\begin{abstract}\nHello world.\n\nSecond paragraph.\n\\end{abstract}\n",
        "need_trans": True,
    }

    async def _fallback_to_source(*args, **kwargs):
        agent._mark_api_fallback("env", env["placeholder"], "invariant_command_mismatch")
        return "Hello world.\n\nSecond paragraph.\n"

    agent._request_env_translation = AsyncMock(side_effect=_fallback_to_source)
    agent._request_llm_for_trans = AsyncMock(
        side_effect=[
            "Hello world.\n\nSecond paragraph.\n",
            "你好，世界。\n",
            "第二段。\n",
        ]
    )

    result = asyncio.run(agent._translate_env(env, MagicMock()))

    assert result["translation_status"] == agent.STATUS_TRANSLATED
    assert "你好，世界�? in result["trans_content"]
    assert "第二段�? in result["trans_content"]
    assert "Hello world." not in result["trans_content"]
    assert "Second paragraph." not in result["trans_content"]
    assert agent._request_llm_for_trans.await_count == 3


def test_list_env_falls_back_to_source_when_nested_env_tokens_leak(tmp_path: Path):
    agent = _build_agent(tmp_path)
    env = {
        "placeholder": "<PLACEHOLDER_ENV_3>",
        "env_name": "itemize",
        "content": "\\begin{itemize}\n\\item Alpha\n\\begin{equation}x = 1\\end{equation}\n\\end{itemize}\n",
        "need_trans": True,
    }
    agent._request_env_translation = AsyncMock(return_value="<ITEM_1>\n<ENV_BEGIN_1>坏掉<ENV_END_1>")

    result = asyncio.run(agent._translate_env(env, MagicMock()))

    assert result["translation_status"] == agent.STATUS_FALLBACK_SOURCE_API_FAILURE
    assert result["fallback_reason"] == "list_env_restore_preserved_source"
    assert result["trans_content"] == env["content"]
    assert "<ENV_BEGIN_" not in result["trans_content"]
