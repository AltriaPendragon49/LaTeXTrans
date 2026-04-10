import asyncio
from unittest.mock import MagicMock

from backend.app.services.agents.validator_agent import ERROR_TYPE_C1, ERROR_TYPE_C2, ValidatorAgent


def _make_validator() -> ValidatorAgent:
    return ValidatorAgent(
        config={
            "llm_config": {"model": "test", "base_url": "http://x", "api_key": "x"},
            "source_language": "en",
            "target_language": "zh",
        },
        project_dir="dummy",
        output_dir="dummy",
    )


def _make_translator(trans_mode: int = 0):
    from backend.app.services.agents.translator_agent import TranslatorAgent

    agent = TranslatorAgent(
        config={
            "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"},
            "source_language": "en",
            "target_language": "zh",
            "enable_compile_first_structural_fallback": True,
            "structural_fallback_ratio_cap": 1.0,
            "structural_fallback_cap_mode": "soft",
        },
        project_dir="dummy",
        output_dir="dummy",
        trans_mode=trans_mode,
        errors_report=[],
    )
    agent.prompts = {
        "env_system_prompt": "Translate env.",
        "env_system_prompt_with_dict": "Translate env with glossary.",
        "retrans_error_parts_system_prompt": "Fix translation errors.",
    }
    return agent


def test_validator_catches_item_placeholder_sequence_drift_as_c1():
    validator = _make_validator()
    part = {
        "env_name": "itemize",
        "placeholder": "<PLACEHOLDER_ENV_1>",
        "content": r"\begin{itemize}\item A\item B\end{itemize}",
        "trans_content": r"\begin{itemize}\item A<ITEM_1>\item B\end{itemize}",
    }
    error = validator._validate(part)
    assert error is not None
    assert "item_anchor_sequence_mismatch" in error.get("math_error", "")
    assert error.get("error_type") == ERROR_TYPE_C1


def test_validator_catches_eqrow_placeholder_sequence_drift_as_c2():
    validator = _make_validator()
    part = {
        "env_name": "eqnarray",
        "placeholder": "<PLACEHOLDER_ENV_2>",
        "content": r"\begin{eqnarray}a &=& b\\c &=& d\end{eqnarray}",
        "trans_content": r"\begin{eqnarray}<EQROW_0>\\c &=& d\end{eqnarray}",
    }
    error = validator._validate(part)
    assert error is not None
    assert "eqrow_placeholder_sequence_mismatch" in error.get("math_error", "")
    assert error.get("error_type") == ERROR_TYPE_C2


def test_translator_list_path_falls_back_when_item_sequence_breaks():
    agent = _make_translator(trans_mode=0)
    env = {
        "placeholder": "<PLACEHOLDER_ENV_3>",
        "env_name": "itemize",
        "need_trans": True,
        "content": r"\begin{itemize}\item A\item B\end{itemize}",
        "trans_content": "",
    }

    async def fake_env_request(env, text, placeholder, session, error_message=None):
        return text.replace("<ITEM_2>", "")

    agent._request_env_translation = fake_env_request
    result = asyncio.run(agent._translate_env(env, MagicMock()))
    assert result["translation_status"] == agent.STATUS_STRUCTURAL_FALLBACK_PENDING_COMPILE
    assert result["fallback_subtype"] == agent.FALLBACK_SUBTYPE_LIST_ENV
    assert result["trans_content"] != env["content"]


def test_translator_eqrow_row_level_fallback_only_affects_failed_rows():
    agent = _make_translator(trans_mode=0)
    env = {
        "placeholder": "<PLACEHOLDER_ENV_4>",
        "env_name": "eqnarray",
        "need_trans": True,
        "content": r"\begin{eqnarray}Natural language row \\ a &=& b\end{eqnarray}",
        "trans_content": "",
    }

    async def fake_env_request(env, text, placeholder, session, error_message=None):
        # Drop EQROW token to force row-level fallback.
        return text.replace("<EQROW_0>", "")

    agent._request_env_translation = fake_env_request
    result = asyncio.run(agent._translate_env(env, MagicMock()))
    assert result["translation_status"] == agent.STATUS_TRANSLATED
    assert result["fallback_subtype"] == agent.FALLBACK_SUBTYPE_MATH_ENV
    assert result["row_fallback_count"] == 1
    assert result["trans_content"] == env["content"]
