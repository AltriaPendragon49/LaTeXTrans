"""
Phase 3 deterministic repair and pipeline tests.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.services.agents.validator_agent import ERROR_TYPE_C1, ValidatorAgent
from backend.app.services.agents.pipeline_invariants import SpeculativeRepairForbiddenError
from backend.app.services.latex.utils import isolate_inline_math, preprocess_risky_tokens
from backend.app.services.latex.token_estimator import estimate_tokens_v1, safe_limit_v1


class TestBareUnderscoreEscaping:

    def test_preprocess_escapes_bare_underscore_in_text(self):
        text = "The word my_var is risky."
        _, math_map = isolate_inline_math(text)
        result = preprocess_risky_tokens(text, math_map)
        assert r"my\_var" in result

    def test_preprocess_does_not_escape_inside_math(self):
        text = r"See $x_i$ for index."
        isolated, math_map = isolate_inline_math(text)
        result = preprocess_risky_tokens(isolated, math_map)
        from backend.app.services.latex.utils import restore_inline_math

        restored = restore_inline_math(result, math_map)
        assert r"$x_i$" in restored

    def test_preprocess_no_double_escape(self):
        text = r"Already escaped \_ here."
        _, math_map = isolate_inline_math(text)
        result = preprocess_risky_tokens(text, math_map)
        assert result.count(r"\_") == 1

    def test_placeholder_underscore_not_escaped(self):
        text = "See <PLACEHOLDER_ENV_1> and file_name here."
        _, math_map = isolate_inline_math(text)
        result = preprocess_risky_tokens(text, math_map)
        assert "<PLACEHOLDER_ENV_1>" in result
        assert r"file\_name" in result

    def test_identifier_like_keys_remain_stable(self):
        text = r"See \cite{He_2016_CVPR} and \Cref{tab:foo_bar} plus plain_token."
        _, math_map = isolate_inline_math(text)
        result = preprocess_risky_tokens(text, math_map)
        assert r"\cite{He_2016_CVPR}" in result
        assert r"\Cref{tab:foo_bar}" in result
        assert r"plain\_token" in result


class TestRepairMathDelimitersSignalGated:

    def test_no_injection_without_math_signal(self):
        original = r"The value $x$ changes."
        translated = "Value x changes."
        with pytest.raises(SpeculativeRepairForbiddenError) as excinfo:
            ValidatorAgent.repair_math_delimiters(original, translated)
        assert excinfo.value.error_code == "SPEC_REPAIR_FORBIDDEN"

    def test_bare_frac_gets_wrapped(self):
        original = r"The result is $\frac{a}{b}$."
        translated = r"The result is \frac{a}{b}."
        with pytest.raises(SpeculativeRepairForbiddenError):
            ValidatorAgent.repair_math_delimiters(original, translated)

    def test_bare_caret_gets_wrapped(self):
        original = r"Area is $x^2$."
        translated = r"Area is x^2."
        with pytest.raises(SpeculativeRepairForbiddenError):
            ValidatorAgent.repair_math_delimiters(original, translated)


class TestChunkLevelFallback:

    def _make_agent(self, enable_fallback=True):
        from backend.app.services.agents.translator_agent import TranslatorAgent

        return TranslatorAgent(
            config={
                "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"},
                "enable_compile_first_structural_fallback": enable_fallback,
                "structural_fallback_ratio_cap": 1.0,
                "structural_fallback_cap_mode": "soft",
            },
            project_dir="dummy",
            output_dir="dummy",
            trans_mode=1,
            errors_report=[],
        )

    def test_fallback_only_affects_target_chunk(self):
        agent = self._make_agent(enable_fallback=True)
        agent._reset_structural_fallback_metrics()
        agent.structural_fallback_denominator = 2

        chunk1 = {
            "section": "2_chunk_1",
            "content": "Original chunk 1 content.",
            "trans_content": "Translated chunk 1.",
        }
        chunk2 = {
            "section": "2_chunk_2",
            "content": "Original chunk 2 content.",
            "trans_content": "Translated chunk 2.",
        }

        error = {
            "part": "sec",
            "num_or_ph": "2_chunk_1",
            "math_error": "math_delimiter_mismatch: ...",
            "error_type": "C2",
        }

        agent._apply_compile_first_fallback(chunk1, error)
        assert chunk1["trans_content"] == "Translated chunk 1."
        assert chunk1["translation_status"] == agent.STATUS_STRUCTURAL_FALLBACK_PENDING_COMPILE
        assert chunk2["trans_content"] == "Translated chunk 2."

    def test_fallback_disabled_does_not_alter_chunk(self):
        agent = self._make_agent(enable_fallback=False)
        agent._reset_structural_fallback_metrics()
        agent.structural_fallback_denominator = 1

        chunk = {
            "section": "3_chunk_1",
            "content": "Original content.",
            "trans_content": "Translated content.",
        }
        error = {"part": "sec", "num_or_ph": "3_chunk_1", "error_type": "C2"}

        result = agent._apply_compile_first_fallback(chunk, error)
        assert result is True
        assert chunk["trans_content"] == "Translated content."
        assert chunk["translation_status"] == agent.STATUS_STRUCTURAL_FALLBACK_PENDING_COMPILE


class TestValidatorSafeCommandArgSpans:

    def _make_validator(self):
        return ValidatorAgent(
            config={
                "llm_config": {"model": "test", "base_url": "http://x", "api_key": "x"},
                "source_language": "en",
                "target_language": "zh",
            },
            project_dir="dummy",
            output_dir="dummy",
        )

    def test_ref_label_cite_pageref_autoref_underscore_not_math_mismatch(self):
        validator = self._make_validator()
        part = {
            "content": (
                r"See \ref{eq:KDE_pred} and \label{sec:intro_part} and \cite{foo_bar}. "
                r"Inline math: $x_i$."
            ),
            "trans_content": (
                r"See \ref{eq:KDE_pred}, \label{sec:intro_part}, \cite{foo_bar}, "
                r"\pageref{appendix_a}, \autoref{thm_main}. Keep math $x_i$."
            ),
        }
        assert validator._validate_math_delimiters(part) is None

    def test_only_real_text_bare_underscore_triggers_mismatch(self):
        validator = self._make_validator()
        part = {
            "content": r"See \ref{eq:KDE_pred}. Math: $x_i$.",
            "trans_content": r"See \ref{eq:KDE_pred}, text_mode_token_with_underscore and math $x_i$.",
        }
        err = validator._validate_math_delimiters(part)
        assert err is not None
        assert "math_delimiter_mismatch" in err

    def test_env_boundary_mismatch_detected(self):
        validator = self._make_validator()
        part = {
            "content": "x",
            "trans_content": "<ENV_BEGIN_1> text <ENV_END_2>",
        }
        err = validator._validate(part)
        assert err is not None
        assert "env_boundary_mismatch" in err.get("math_error", "")
        assert err.get("error_type") == "C2"

    def test_pgfplots_addplot_expression_not_reported_as_math_mismatch(self):
        validator = self._make_validator()
        part = {
            "content": r"\begin{axis}\addplot coordinates {(0,1)};\end{axis}",
            "trans_content": (
                r"\begin{axis}"
                r"\addplot+[domain=0:10,samples=50] {x^(-0.04)};"
                r"\end{axis}"
            ),
        }
        assert validator._validate_math_delimiters(part) is None


class TestTranslatorPhase13Completion:

    def _make_agent(self, trans_mode: int = 0):
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
            "section_system_prompt": "Translate section.",
            "section_system_prompt_with_dict": "Translate section with glossary.",
            "env_system_prompt": "Translate env.",
            "env_system_prompt_with_dict": "Translate env with glossary.",
            "retrans_error_parts_system_prompt": "Fix translation errors.",
            "REFERENCE_CONTEXT_TEMPLATE": "\n<REFERENCE_CONTEXT>\n{context}\n</REFERENCE_CONTEXT>\n",
        }
        return agent

    def test_c1_same_part_only_one_llm_retry(self):
        agent = self._make_agent(trans_mode=1)
        secs = [{"section": "2", "content": "source", "trans_content": "old"}]
        caps = []
        envs = []
        session = MagicMock()

        agent.errors_report = [
            {"part": "sec", "num_or_ph": "2", "error_type": ERROR_TYPE_C1, "math_error": "math_delimiter_mismatch"},
            {"part": "sec", "num_or_ph": "2", "error_type": ERROR_TYPE_C1, "math_error": "math_delimiter_mismatch"},
        ]

        calls = {"count": 0}

        async def fake_translate_section(section, session, error_message=None):
            calls["count"] += 1
            updated = section.copy()
            updated["trans_content"] = "retried-once"
            return updated

        agent._translate_section = fake_translate_section
        agent._validate_part_after_structural_fix = lambda part: None

        asyncio.run(agent._retranslate_error_parts(secs, caps, envs, session))

        assert calls["count"] == 1
        assert agent.c1_retry_enforced_once is True

    def test_noop_retry_and_metadata_written(self):
        agent = self._make_agent(trans_mode=0)
        long_english = ("This section remains in English and should be translated properly. " * 20).strip()
        section = {"section": "11_2", "content": long_english, "previous_context": "ctx"}

        responses = [long_english, "这是修正后的中文译文。"]

        async def fake_request(system_prompt, text, fail_part, type, session, previous_context=None):
            return responses.pop(0)

        agent._request_llm_for_trans = fake_request

        result = asyncio.run(agent._translate_section(section, MagicMock()))

        assert result["no_op_detected"] is True
        assert result["translation_status"] == agent.STATUS_TRANSLATED_AFTER_NOOP_RETRY
        assert result["translation_retry_count"] == 1
        assert "11_2" in agent.noop_sections
        assert result["trans_content"] == "这是修正后的中文译文。"

    def test_llm_payload_pipeline_masks_math_and_env(self):
        agent = self._make_agent(trans_mode=0)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"choices": [{"message": {"content": "translated"}}]})
        mock_response.raise_for_status = MagicMock()

        mock_session = MagicMock()
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_response
        mock_session.post.return_value = cm

        text = (
            r"Use foo_bar and keep math $x_i$ plus \ref{eq:KDE_pred}. "
            r"\begin{theorem}Do not translate this block.\end{theorem} "
            r"\begin{customenv}translate me\end{customenv}"
        )

        asyncio.run(
            agent._request_llm_for_trans(
                system_prompt="Translate.",
                text=text,
                fail_part="2",
                type="sec",
                session=mock_session,
                previous_context=None,
            )
        )

        payload = mock_session.post.call_args[1]["json"]
        user_payload = payload["messages"][1]["content"]
        assert "<INLMATH_" in user_payload
        assert "$x_i$" not in user_payload
        assert "foo\\_bar" in user_payload
        assert "<PROTECTED_CMD_" in user_payload
        assert "<ENV_BEGIN_" not in user_payload

    def test_level_a_related_error_skips_retry_and_direct_fallback(self):
        agent = self._make_agent(trans_mode=1)
        secs = [{"section": "9", "content": "source", "trans_content": "translated"}]
        caps = []
        envs = []
        session = MagicMock()

        agent.errors_report = [
            {
                "part": "sec",
                "num_or_ph": "9",
                "error_type": "C2",
                "math_error": "level_a_env_placeholder_residual: unresolved Level-A ENV placeholders",
            }
        ]

        called = {"fallback": 0, "fix": 0}

        def fake_fallback(part, error, recheck_report=None):
            called["fallback"] += 1
            part["trans_content"] = part["content"]
            return True

        def fake_fix(part, error):
            called["fix"] += 1
            return True

        agent._apply_compile_first_fallback = fake_fallback
        agent._apply_structural_fix = fake_fix

        asyncio.run(agent._retranslate_error_parts(secs, caps, envs, session))

        assert called["fallback"] == 1
        assert called["fix"] == 0

    def test_api_failure_marks_section_fallback_status(self):
        agent = self._make_agent(trans_mode=0)
        section = {
            "section": "2",
            "content": "Short english section content for fallback check.",
            "previous_context": None,
        }

        async def fake_request(system_prompt, text, fail_part, type, session, previous_context=None):
            agent._mark_api_fallback("sec", str(fail_part), "api_request_failed_after_3_attempts")
            return text

        agent._request_llm_for_trans = fake_request

        result = asyncio.run(agent._translate_section(section, MagicMock()))
        assert result["translation_status"] == agent.STATUS_FALLBACK_SOURCE_API_FAILURE
        assert result["fallback_reason"] == "api_request_failed_after_3_attempts"

    def test_eqnarray_without_text_rows_marked_math_preserved(self):
        agent = self._make_agent(trans_mode=0)
        env = {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "eqnarray",
            "need_trans": True,
            "content": r"\begin{eqnarray}a &=& b \\ c &=& d\end{eqnarray}",
            "trans_content": "",
        }
        result = asyncio.run(agent._translate_env(env, MagicMock()))
        assert result["trans_content"] == env["content"]
        assert result["translation_status"] == agent.STATUS_MATH_PRESERVED
        assert result["fallback_subtype"] == agent.FALLBACK_SUBTYPE_NONE
        assert result["row_fallback_count"] == 0

    def test_env_row_retry_key_stable(self):
        agent = self._make_agent(trans_mode=0)
        assert agent._env_row_retry_key("<PLACEHOLDER_ENV_9>", 3) == "part:env:<PLACEHOLDER_ENV_9>:row:3"

    def test_list_item_anchor_mismatch_triggers_compile_fallback(self):
        agent = self._make_agent(trans_mode=0)
        env = {
            "placeholder": "<PLACEHOLDER_ENV_2>",
            "env_name": "itemize",
            "need_trans": True,
            "content": r"\begin{itemize}\item A \item B\end{itemize}",
            "trans_content": "",
        }

        async def fake_env_request(env, text, placeholder, session, error_message=None):
            return text.replace("<ITEM_2>", "")

        agent._request_env_translation = fake_env_request
        result = asyncio.run(agent._translate_env(env, MagicMock()))
        assert result["translation_status"] == agent.STATUS_STRUCTURAL_FALLBACK_PENDING_COMPILE
        assert result["fallback_subtype"] == agent.FALLBACK_SUBTYPE_LIST_ENV
        assert result["trans_content"] != env["content"]


class TestOversizeSourcePassThrough:

    def _make_agent(self, trans_mode: int = 0):
        from backend.app.services.agents.translator_agent import TranslatorAgent

        agent = TranslatorAgent(
            config={
                "llm_config": {
                    "model": "gpt-4o",
                    "base_url": "http://dummy",
                    "api_key": "dummy",
                    "model_context_tokens": 3000,
                    "prompt_reserve_tokens": 900,
                },
                "source_language": "en",
                "target_language": "ja",
            },
            project_dir="dummy",
            output_dir="dummy",
            trans_mode=trans_mode,
            errors_report=[],
        )
        agent.prompts = {
            "section_system_prompt": "Translate section.",
            "section_system_prompt_with_dict": "Translate section with glossary.",
            "REFERENCE_CONTEXT_TEMPLATE": "\n<REFERENCE_CONTEXT>\n{context}\n</REFERENCE_CONTEXT>\n",
        }
        return agent

    def test_oversize_chunk_bypasses_translator_and_keeps_source(self):
        agent = self._make_agent(trans_mode=0)
        content = "A" * 9000
        section = {
            "section": "7_chunk_3",
            "content": content,
            "oversize_no_safe_boundary": True,
            "previous_context": "context",
        }

        agent._request_llm_for_trans = AsyncMock(return_value="SHOULD_NOT_BE_USED")
        result = asyncio.run(agent._translate_section(section, MagicMock()))

        assert result["trans_content"] == content
        assert result["translated"] is False
        assert result["downgrade_reason"] == "oversize_no_safe_boundary"
        assert result["translation_status"] == agent.STATUS_SOURCE_PASS_THROUGH
        assert result["estimated_tokens"] > result["safe_input_limit"]
        agent._request_llm_for_trans.assert_not_called()

    def test_oversize_chunk_skips_env_and_caption_secondary_chain(self):
        agent = self._make_agent(trans_mode=0)
        content = "<PLACEHOLDER_ENV_1> <PLACEHOLDER_CAP_1> " + ("A" * 9000)
        section = {
            "section": "8_chunk_1",
            "content": content,
            "oversize_no_safe_boundary": True,
        }
        envs = [{
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "customenv",
            "need_trans": True,
            "content": r"\begin{customenv}source\end{customenv}",
            "trans_content": "",
        }]
        captions = [{
            "placeholder": "<PLACEHOLDER_CAP_1>",
            "content": r"\caption{source caption}",
            "trans_content": "",
        }]

        agent._translate_env = AsyncMock(side_effect=lambda env, session: env)
        agent._translate_caption = AsyncMock(side_effect=lambda cap, session: cap)

        translated = asyncio.run(agent.translate(section, envs, captions, MagicMock()))
        assert translated["downgrade_reason"] == "oversize_no_safe_boundary"
        agent._translate_env.assert_not_called()
        agent._translate_caption.assert_not_called()


class TestTokenEstimatorDeterminism:

    def test_estimate_tokens_v1_repeatable(self):
        text = "Deterministic テスト with UTF-8 payload " * 20
        values = [estimate_tokens_v1(text) for _ in range(5)]
        assert len(set(values)) == 1

    def test_safe_limit_v1_repeatable(self):
        values = [safe_limit_v1(128000, 4096) for _ in range(5)]
        assert len(set(values)) == 1
        assert values[0] == safe_limit_v1(128000, 4096)
