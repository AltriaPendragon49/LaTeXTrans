import asyncio
import os
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services.agents.parser_agent import ParserAgent
from backend.app.services.agents.pipeline_invariants import SpeculativeRepairForbiddenError
from backend.app.services.agents.translator_agent import TranslatorAgent
from backend.app.services.agents.validator_agent import ValidatorAgent


def _make_translator(trans_mode: int = 0) -> TranslatorAgent:
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
        "REFERENCE_CONTEXT_TEMPLATE": "\n<REFERENCE_CONTEXT>\n{context}\n</REFERENCE_CONTEXT>\n",
        "retrans_error_parts_system_prompt": "Fix translation errors.",
    }
    return agent


def _make_parser() -> ParserAgent:
    return ParserAgent(
        config={
            "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"},
            "source_language": "en",
            "target_language": "zh",
        },
        project_dir="dummy",
        output_dir="dummy",
    )


def _make_async_session_with_text(text: str) -> MagicMock:
    response = MagicMock()
    response.status = 200
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(return_value={"choices": [{"message": {"content": text}}]})
    cm = AsyncMock()
    cm.__aenter__.return_value = response
    session = MagicMock()
    session.post.return_value = cm
    return session


def test_retrans_payload_no_raw_structure_tokens():
    agent = _make_translator(trans_mode=1)
    session = _make_async_session_with_text("修复后的译文")
    part = {
        "content": r"\begin{theorem}Keep $x_i$ and text.\end{theorem}",
        "trans_content": "broken translation",
    }

    asyncio.run(
        agent._request_llm_for_retrans_error_parts(
            system_prompt="Fix translation",
            part=part,
            error_message=r"math_delimiter_mismatch around \begin{theorem} and $",
            fail_part="sec_1",
            type="sec",
            session=session,
        )
    )

    payload = session.post.call_args[1]["json"]["messages"][1]["content"]
    assert re.search(r"\\begin\{", payload) is None
    assert re.search(r"\\end\{", payload) is None
    assert re.search(r"(?<!\\)\$", payload) is None


def test_env_judge_payload_reuses_freeze_pipeline():
    parser = _make_parser()
    session = _make_async_session_with_text("true")
    semaphore = asyncio.Semaphore(1)
    env_text = r"\begin{customenv}Sentence with $x_i$ and \ref{eq:foo_bar}.\end{customenv}"

    result = asyncio.run(
        parser._request_llm_for_judge_async(
            system_prompt="Judge if need translation",
            text=env_text,
            session=session,
            semaphore=semaphore,
        )
    )
    assert result is True

    payload = session.post.call_args[1]["json"]["messages"][1]["content"]
    assert re.search(r"\\begin\{", payload) is None
    assert re.search(r"\\end\{", payload) is None
    assert re.search(r"(?<!\\)\$", payload) is None
    assert "<PROTECTED_CMD_" in payload
    assert "<ENV_BEGIN_" not in payload
    assert "<INLMATH_" in payload


def test_env_judge_payload_no_long_raw_span():
    parser = _make_parser()
    semaphore = asyncio.Semaphore(1)
    long_body = "A" * 240
    env_text = rf"\begin{{customenv}}{long_body}\end{{customenv}}"

    session = MagicMock()
    session.post.side_effect = AssertionError("session.post should not be called on leakage violation")

    result = asyncio.run(
        parser._request_llm_for_judge_async(
            system_prompt="Judge if need translation",
            text=env_text,
            session=session,
            semaphore=semaphore,
        )
    )
    assert result is True
    session.post.assert_not_called()


def test_llm_client_no_freeze_bypass():
    agent = _make_translator(trans_mode=0)
    session = MagicMock()
    session.post.side_effect = AssertionError("raw LLM client should be accessed only via freeze entrypoint mock")

    with patch.object(agent, "_call_llm_with_freeze", new=AsyncMock(return_value="ok")) as freeze_call:
        asyncio.run(
            agent._request_llm_for_trans(
                system_prompt="Translate",
                text=r"Body with $x_i$ and \begin{theorem}X\end{theorem}",
                fail_part="sec_1",
                type="sec",
                session=session,
            )
        )
        asyncio.run(
            agent._request_llm_for_trans_with_terms(
                system_prompt="Translate with glossary",
                text=r"Body with $x_i$ and \begin{theorem}X\end{theorem}",
                fail_part="sec_2",
                type="sec",
                session=session,
            )
        )
        asyncio.run(
            agent._request_llm_for_retrans_error_parts(
                system_prompt="Fix",
                part={"content": "src", "trans_content": "tgt"},
                error_message="err",
                fail_part="sec_3",
                type="sec",
                session=session,
            )
        )
        assert freeze_call.await_count == 3
    session.post.assert_not_called()


def test_fix_missing_placeholders_forbidden_error_contract():
    agent = _make_translator(trans_mode=0)
    with pytest.raises(SpeculativeRepairForbiddenError) as excinfo:
        agent._fix_missing_placeholders("src <PLACEHOLDER_ENV_1>", "tgt")
    assert excinfo.value.error_code == "SPEC_REPAIR_FORBIDDEN"
    assert "_fix_missing_placeholders" in str(excinfo.value)


def test_repair_math_delimiters_forbidden_error_contract():
    with pytest.raises(SpeculativeRepairForbiddenError) as excinfo:
        ValidatorAgent.repair_math_delimiters(r"$x$", "x")
    assert excinfo.value.error_code == "SPEC_REPAIR_FORBIDDEN"
    assert "repair_math_delimiters" in str(excinfo.value)


def test_no_structural_token_injection_after_c1_c2_routing():
    agent = _make_translator(trans_mode=1)
    secs = [{"section": "9", "content": "source-$x$", "trans_content": "broken x"}]
    caps = []
    envs = []
    session = MagicMock()
    agent.errors_report = [
        {"part": "sec", "num_or_ph": "9", "error_type": "C2", "math_error": "math_delimiter_mismatch"}
    ]

    with patch.object(agent, "_fix_missing_placeholders", wraps=agent._fix_missing_placeholders) as fix_ph, patch(
        "backend.app.services.agents.validator_agent.ValidatorAgent.repair_math_delimiters",
        wraps=ValidatorAgent.repair_math_delimiters,
    ) as fix_math:
        asyncio.run(agent._retranslate_error_parts(secs, caps, envs, session))
        assert fix_ph.call_count == 0
        assert fix_math.call_count == 0
    assert secs[0]["trans_content"] == "broken x"
    assert secs[0]["translation_status"] == agent.STATUS_STRUCTURAL_FALLBACK_PENDING_COMPILE
    assert secs[0]["fallback_reason"] == "compile_first_structural_fallback:C2_math_delimiter_mismatch"
