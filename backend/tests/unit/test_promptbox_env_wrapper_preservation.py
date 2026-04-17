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


def test_promptbox_env_preserves_source_wrapper(tmp_path: Path):
    agent = _build_agent(tmp_path)
    env = {
        "placeholder": "<PLACEHOLDER_ENV_promptbox>",
        "env_name": "promptbox",
        "content": (
            "\\begin{promptbox}\n"
            "\\textbf{System:} Keep wrapper.\n"
            "\\texttt{<think>...</think>}\n"
            "\\end{promptbox}\n"
        ),
        "need_trans": True,
    }
    agent._request_env_translation = AsyncMock(
        return_value="\\textbf{System:} translated.\n\\texttt{<thinking>...</thinking>}\n"
    )

    result = asyncio.run(agent._translate_env(env, MagicMock()))

    assert result["translation_status"] == agent.STATUS_TRANSLATED
    assert result["trans_content"].startswith("\\begin{promptbox}\n")
    assert result["trans_content"].endswith("\\end{promptbox}\n")
    assert "\\texttt{<thinking>...</thinking>}" in result["trans_content"]
