import asyncio
import json
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


def test_oversize_chunk_short_circuits_before_llm(tmp_path: Path):
    agent = _build_agent(tmp_path)
    section = {
        "section": "1_chunk_1",
        "content": "A" * 9000,
        "previous_context": "",
        "oversize_no_safe_boundary": True,
    }
    agent._request_llm_for_trans = AsyncMock(side_effect=AssertionError("LLM call must be skipped"))

    result = asyncio.run(agent._translate_section(section, MagicMock()))

    assert result["translation_status"] == agent.STATUS_SOURCE_PASS_THROUGH
    assert result["translated"] is False
    assert result["downgrade_reason"] == "oversize_no_safe_boundary"
    assert result["trans_content"] == section["content"]
    agent._request_llm_for_trans.assert_not_called()


def test_oversize_chunk_bypasses_env_and_caption_translation_chain(tmp_path: Path):
    agent = _build_agent(tmp_path)
    section = {
        "section": "2_chunk_1",
        "content": ("B" * 9000) + " <PLACEHOLDER_ENV_1> <PLACEHOLDER_CAP_1>",
        "previous_context": "",
        "oversize_no_safe_boundary": True,
    }
    envs = [{"placeholder": "<PLACEHOLDER_ENV_1>", "content": "env body"}]
    captions = [{"placeholder": "<PLACEHOLDER_CAP_1>", "content": "cap body"}]
    agent._translate_env = AsyncMock(side_effect=AssertionError("env translation must be skipped"))
    agent._translate_caption = AsyncMock(side_effect=AssertionError("caption translation must be skipped"))

    result = asyncio.run(agent.translate(section, envs, captions, MagicMock()))

    assert result["translation_status"] == agent.STATUS_SOURCE_PASS_THROUGH
    assert result["translated"] is False
    agent._translate_env.assert_not_called()
    agent._translate_caption.assert_not_called()


def test_oversize_downgrade_flush_writes_replay_bundle_fields(tmp_path: Path):
    agent = _build_agent(tmp_path)
    section = {
        "section": "3_chunk_1",
        "content": "C" * 9000,
        "oversize_no_safe_boundary": True,
    }
    metadata = agent._evaluate_oversize_downgrade(section)
    assert metadata is not None

    agent._record_oversize_downgrade(metadata)
    agent._flush_oversize_downgrade_events()

    replay_path = Path(agent.output_dir) / "replay_bundle.json"
    assert replay_path.exists()
    replay = json.loads(replay_path.read_text(encoding="utf-8"))

    assert replay["safe_limit_id"] == "safe_limit_v1"
    assert replay["token_estimator_id"] == "estimate_tokens_v1"
    assert replay["safe_input_limit"] == metadata["safe_input_limit"]
    assert replay["oversize_chunk_downgrades"]
    assert replay["oversize_chunk_downgrades"][0]["estimated_tokens"] == metadata["estimated_tokens"]

    task_log_path = Path(agent.output_dir) / "task_log.json"
    assert task_log_path.exists()
    task_events = json.loads(task_log_path.read_text(encoding="utf-8"))
    assert any(event.get("event") == "oversize_chunk_downgraded" for event in task_events)

