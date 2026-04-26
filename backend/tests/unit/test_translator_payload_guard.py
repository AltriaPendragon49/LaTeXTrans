import asyncio
import re
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.services.agents.pipeline_invariants import (
    PipelineInvariantViolation,
    assert_no_raw_structure,
)
from backend.app.services.agents.translator_agent import TranslatorAgent


def _build_agent(trans_mode: int = 0, extra_config: dict | None = None) -> TranslatorAgent:
    config = {
        "llm_config": {
            "model": "gpt-4o",
            "base_url": "http://dummy-llm",
            "api_key": "dummy-key",
        }
    }
    if extra_config:
        config.update(extra_config)
    agent = TranslatorAgent(
        config=config,
        project_dir="dummy",
        output_dir="dummy",
        trans_mode=trans_mode,
    )
    agent.prompts = {
        "section_system_prompt": "Translate section content.",
        "caption_system_prompt": "Translate caption content.",
        "env_system_prompt": "Translate environment content.",
        "retrans_error_parts_system_prompt": "Fix translated content.",
    }
    return agent


def _mock_success_session(return_text: str = "translated text") -> MagicMock:
    response = MagicMock()
    response.status = 200
    response.headers = {}
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(
        return_value={"choices": [{"message": {"content": return_text}}]}
    )

    ctx = AsyncMock()
    ctx.__aenter__.return_value = response
    session = MagicMock()
    session.post.return_value = ctx
    return session


def _mock_echo_user_payload_session() -> MagicMock:
    session = MagicMock()

    def _post(*args, **kwargs):
        response = MagicMock()
        response.status = 200
        response.headers = {}
        response.raise_for_status = MagicMock()
        response.json = AsyncMock(
            return_value={
                "choices": [
                    {"message": {"content": kwargs["json"]["messages"][1]["content"]}}
                ]
            }
        )
        ctx = AsyncMock()
        ctx.__aenter__.return_value = response
        return ctx

    session.post.side_effect = _post
    return session


class TestTranslatorPayloadGuard(unittest.TestCase):
    def test_legacy_translation_core_uses_origin_order_and_skips_front_matter(self):
        agent = _build_agent(extra_config={"enable_legacy_translation_core": True})
        calls = []

        async def fake_section(section, session, error_message=None):
            calls.append(("sec", section["section"]))
            section = section.copy()
            section["trans_content"] = f"SEC:{section['section']}"
            return section

        async def fake_env(env, session, error_message=None):
            calls.append(("env", env["placeholder"]))
            env = env.copy()
            env["trans_content"] = f"ENV:{env['placeholder']}"
            return env

        async def fake_caption(caption, session, error_message=None):
            calls.append(("cap", caption["placeholder"]))
            caption = caption.copy()
            caption["trans_content"] = f"CAP:{caption['placeholder']}"
            return caption

        agent._translate_section = fake_section
        agent._translate_env = fake_env
        agent._translate_caption = fake_caption

        sections = [
            {"section": "0", "content": r"\begin{document}<PLACEHOLDER_ENV_1>"},
            {"section": "1", "content": r"\section{Intro}<PLACEHOLDER_ENV_1><PLACEHOLDER_CAP_2>"},
        ]
        envs = [
            {
                "placeholder": "<PLACEHOLDER_ENV_1>",
                "content": r"\begin{abstract}<PLACEHOLDER_CAP_1>\end{abstract}",
                "need_trans": True,
            }
        ]
        captions = [
            {"placeholder": "<PLACEHOLDER_CAP_1>", "content": "A figure."},
            {"placeholder": "<PLACEHOLDER_CAP_2>", "content": "A table."},
        ]

        skipped = asyncio.run(agent.translate(sections[0], envs, captions, MagicMock()))
        translated = asyncio.run(agent.translate(sections[1], envs, captions, MagicMock()))

        self.assertNotIn("trans_content", skipped)
        self.assertEqual(translated["trans_content"], "SEC:1")
        self.assertEqual(
            calls,
            [
                ("env", "<PLACEHOLDER_ENV_1>"),
                ("cap", "<PLACEHOLDER_CAP_1>"),
                ("sec", "1"),
                ("env", "<PLACEHOLDER_ENV_1>"),
                ("cap", "<PLACEHOLDER_CAP_2>"),
                ("cap", "<PLACEHOLDER_CAP_1>"),
            ],
        )

    def test_legacy_translate_section_bypasses_hard_freeze_transport(self):
        agent = _build_agent(extra_config={"enable_legacy_translation_core": True})
        agent._call_llm_with_freeze = AsyncMock(side_effect=AssertionError("hard-freeze should be bypassed"))
        agent._legacy_request_llm_for_trans = AsyncMock(return_value=r"\section{引言} 正文")

        result = asyncio.run(
            agent._translate_section(
                {"section": "1", "content": r"\section{Intro} Body"},
                MagicMock(),
            )
        )

        self.assertEqual(result["trans_content"], r"\section{引言} 正文")
        agent._call_llm_with_freeze.assert_not_awaited()

    def test_prepare_llm_payload_text_replaces_all_protected_placeholder_families_with_hard_freeze_tokens(self):
        agent = _build_agent()
        text = (
            "<PLACEHOLDER_ENV_3>\n"
            "<PLACEHOLDER_CAP_1>\n"
            "<PLACEHOLDER_NEWCOMMAND_2>\n"
            "<PLACEHOLDER_sec_intro_begin>\n"
            "Body @@ should stay textual.\n"
            "<PLACEHOLDER_sec_intro_end>\n"
        )

        prepared, context = agent._prepare_llm_payload_text(text)

        self.assertNotIn("<PLACEHOLDER_ENV_3>", prepared)
        self.assertNotIn("<PLACEHOLDER_CAP_1>", prepared)
        self.assertNotIn("<PLACEHOLDER_NEWCOMMAND_2>", prepared)
        self.assertNotIn("<PLACEHOLDER_sec_intro_begin>", prepared)
        self.assertNotIn("<PLACEHOLDER_sec_intro_end>", prepared)
        self.assertGreaterEqual(prepared.count("@@HF:"), 5)
        self.assertRegex(prepared, r"@@HF:[A-Z]+:\d{4}:[0-9A-F]{8}:[0-9A-F]{8}@@")
        self.assertTrue(context["hard_freeze_request_nonce"])
        self.assertEqual(len(context["hard_freeze_token_sequence"]), 5)
        self.assertEqual(agent._restore_llm_output_text(prepared, context), text)

    def test_prepare_llm_payload_text_masks_preamble_command_arguments(self):
        agent = _build_agent()
        text = (
            "\\documentclass{article}\n"
            "\\usepackage{iclr2022_conference,times}\n"
            "\\input{math_commands.tex}\n"
            "\\title{LoRA}\n"
        )

        prepared, context = agent._prepare_llm_payload_text(text)

        self.assertIn("@@HF:CMD:", prepared)
        self.assertNotIn("\\documentclass{article}", prepared)
        self.assertNotIn("\\usepackage{iclr2022_conference,times}", prepared)
        self.assertNotIn("\\input{math_commands.tex}", prepared)
        self.assertIn("\\title{LoRA}", prepared)
        self.assertEqual(agent._restore_llm_output_text(prepared, context), text)

    def test_prepare_llm_payload_text_masks_env_boundaries_idempotently(self):
        agent = _build_agent()
        text = (
            "\\documentclass{article}\n"
            "\\usepackage{amsmath}\n"
            "\\begin{document}\n"
            "\\bibliographystyle{plain}\n"
            "\\bibliography{refs}\n"
            "\\end{document}\n"
            "\\endinput\n"
        )

        prepared_1, _ = agent._prepare_llm_payload_text(text)
        prepared_2, _ = agent._prepare_llm_payload_text(prepared_1)

        self.assertEqual(prepared_1, prepared_2)
        assert_no_raw_structure(prepared_1, context="translator-payload-guard")
        self.assertIn("@@HF:CMD:", prepared_1)
        self.assertNotIn("<ENV_BEGIN_1>", prepared_1)
        self.assertNotIn("<ENV_END_1>", prepared_1)

    def test_call_llm_with_freeze_masks_structure_before_send_and_restores_response(self):
        agent = _build_agent()
        user_text = "\\begin{document}\n\\end{document}\n\\endinput\n\\bibliography{refs}"
        with patch(
            "backend.app.services.latex.utils.secrets.token_hex",
            return_value="56A34CE8",
        ):
            prepared_text, _ = agent._prepare_llm_payload_text(user_text)
            session = _mock_success_session(prepared_text)

            result = asyncio.run(
                agent._call_llm_with_freeze(
                    system_prompt="prompt",
                    user_text=user_text,
                    fail_part="7",
                    part_type="sec",
                    session=session,
                    fallback_text="fallback-text",
                )
            )

        self.assertEqual(result, user_text)
        self.assertEqual(session.post.call_count, 1)
        payload = session.post.call_args.kwargs["json"]
        user_payload = payload["messages"][1]["content"]
        assert_no_raw_structure(user_payload, context="translator:sec:7")
        self.assertIn("@@HF:CMD:", user_payload)
        self.assertNotIn("<ENV_BEGIN_1>", user_payload)
        self.assertNotIn("<ENV_END_1>", user_payload)

    def test_retrans_path_uses_prepare_guard_before_send(self):
        agent = _build_agent(trans_mode=1)
        part = {
            "content": "\\begin{document}\nNatural language content.\n\\end{document}\n\\endinput",
            "trans_content": "\\begin{document}\nNatural language content.\n\\end{document}\n\\endinput",
        }
        raw_user_prompt = (
            f"[Original]:\n{part['content']}\n"
            f"[Translation]:\n{part['trans_content']}\n"
            "[Error]:\n"
        )
        with patch(
            "backend.app.services.latex.utils.secrets.token_hex",
            return_value="71CD7F8F",
        ):
            prepared_prompt, _ = agent._prepare_llm_payload_text(raw_user_prompt)
            session = _mock_success_session(prepared_prompt)

            result = asyncio.run(
                agent._request_llm_for_retrans_error_parts(
                    "retry prompt",
                    part=part,
                    error_message="",
                    fail_part="7",
                    type="sec",
                    session=session,
                )
            )

        self.assertEqual(result, raw_user_prompt.rstrip("\n"))
        self.assertEqual(session.post.call_count, 1)
        payload = session.post.call_args.kwargs["json"]
        user_payload = payload["messages"][1]["content"]
        assert_no_raw_structure(user_payload, context="translator:sec:7")
        self.assertIn("@@HF:CMD:", user_payload)
        self.assertNotIn("<ENV_BEGIN_1>", user_payload)
        self.assertNotIn("<ENV_END_2>", user_payload)

    def test_translate_section_restores_structure_only_sections_after_llm_response(self):
        agent = _build_agent(trans_mode=0)
        section = {
            "section": "7",
            "content": "\\begin{document}\n<PLACEHOLDER_CAP_1>\n\\end{document}\n\\endinput",
            "previous_context": "",
        }
        with patch(
            "backend.app.services.latex.utils.secrets.token_hex",
            return_value="2C4CA12B",
        ):
            prepared_section, _ = agent._prepare_llm_payload_text(section["content"])
            session = _mock_success_session(prepared_section)

            translated = asyncio.run(agent._translate_section(section, session))

        self.assertEqual(translated["trans_content"], section["content"])
        self.assertEqual(translated["translation_status"], agent.STATUS_TRANSLATED)
        self.assertEqual(session.post.call_count, 1)
        payload = session.post.call_args.kwargs["json"]
        user_payload = payload["messages"][1]["content"]
        assert_no_raw_structure(user_payload, context="translator:sec:7")
        self.assertIn("@@HF:CMD:", user_payload)
        self.assertNotIn("<PLACEHOLDER_CAP_1>", user_payload)
        self.assertNotIn("<ENV_BEGIN_1>", user_payload)
        self.assertNotIn("<ENV_END_1>", user_payload)

    def test_call_llm_with_freeze_rejects_reordered_hard_freeze_tokens(self):
        agent = _build_agent(trans_mode=0)
        user_text = "Alpha <PLACEHOLDER_ENV_1> Beta <PLACEHOLDER_CAP_2>"
        prepared_text, _ = agent._prepare_llm_payload_text(user_text)
        hard_freeze_tokens = [chunk for chunk in prepared_text.split() if chunk.startswith("@@HF:")]
        self.assertEqual(len(hard_freeze_tokens), 2)
        session = _mock_success_session(
            f"Alpha {hard_freeze_tokens[1]} Beta {hard_freeze_tokens[0]}"
        )

        with self.assertRaises(PipelineInvariantViolation):
            asyncio.run(
                agent._call_llm_with_freeze(
                    system_prompt="prompt",
                    user_text=user_text,
                    fail_part="reordered",
                    part_type="sec",
                    session=session,
                    fallback_text="fallback-text",
                )
            )

    def test_call_llm_with_freeze_rejects_unknown_hard_freeze_token(self):
        agent = _build_agent(trans_mode=0)
        user_text = "Alpha <PLACEHOLDER_ENV_1> Beta"
        prepared_text, _ = agent._prepare_llm_payload_text(user_text)
        hard_freeze_token = next(chunk for chunk in prepared_text.split() if chunk.startswith("@@HF:"))
        session = _mock_success_session(
            f"Alpha {hard_freeze_token} Beta {hard_freeze_token.replace(':0001:', ':9999:', 1)}"
        )

        with self.assertRaises(PipelineInvariantViolation):
            asyncio.run(
                agent._call_llm_with_freeze(
                    system_prompt="prompt",
                    user_text=user_text,
                    fail_part="unknown",
                    part_type="sec",
                    session=session,
                    fallback_text="fallback-text",
                )
            )

    def test_call_llm_with_freeze_rejects_missing_hard_freeze_token(self):
        agent = _build_agent(trans_mode=0)
        user_text = "Alpha <PLACEHOLDER_ENV_1> Beta <PLACEHOLDER_CAP_2>"
        session = _mock_success_session("Alpha Beta")

        with self.assertRaises(PipelineInvariantViolation):
            asyncio.run(
                agent._call_llm_with_freeze(
                    system_prompt="prompt",
                    user_text=user_text,
                    fail_part="missing",
                    part_type="sec",
                    session=session,
                    fallback_text="fallback-text",
                )
            )

    def test_call_llm_with_freeze_rejects_duplicate_hard_freeze_token(self):
        agent = _build_agent(trans_mode=0)
        user_text = "Alpha <PLACEHOLDER_ENV_1> Beta"
        prepared_text, _ = agent._prepare_llm_payload_text(user_text)
        hard_freeze_token = next(chunk for chunk in prepared_text.split() if chunk.startswith("@@HF:"))
        session = _mock_success_session(
            f"Alpha {hard_freeze_token} {hard_freeze_token} Beta"
        )

        with self.assertRaises(PipelineInvariantViolation):
            asyncio.run(
                agent._call_llm_with_freeze(
                    system_prompt="prompt",
                    user_text=user_text,
                    fail_part="duplicate",
                    part_type="sec",
                    session=session,
                    fallback_text="fallback-text",
                )
            )

    def test_translate_section_still_calls_llm_for_normal_content(self):
        agent = _build_agent(trans_mode=0)
        session = _mock_success_session("normal translated content")
        section = {
            "section": "2",
            "content": "This is a normal paragraph for translation.",
            "previous_context": "",
        }

        translated = asyncio.run(agent._translate_section(section, session))
        self.assertEqual(translated["trans_content"], "normal translated content")
        self.assertEqual(session.post.call_count, 1)

    def test_prepare_llm_payload_text_masks_residual_begin_end_and_dollar_tokens(self):
        agent = _build_agent()
        raw_text = "\\end{snugshade*}\nResidual $ token\n\\begin{appendix}"

        prepared, context = agent._prepare_llm_payload_text(raw_text)
        restored = agent._restore_llm_output_text(prepared, context)

        assert_no_raw_structure(prepared, context="translator:sec:residual")
        self.assertEqual(restored, raw_text)
        self.assertNotIn("\\end{snugshade*}", prepared)
        self.assertNotIn("\\begin{appendix}", prepared)
        self.assertNotIn("Residual $ token", prepared)
        self.assertIn("@@HF:CMD:", prepared)

    def test_prepare_llm_payload_text_masks_display_math_and_restores_it(self):
        agent = _build_agent()
        raw_text = "We optimize $$x_i = y_i$$ and \\[z = 1\\] in context."

        prepared, context = agent._prepare_llm_payload_text(raw_text)
        restored = agent._restore_llm_output_text(prepared, context)

        assert_no_raw_structure(prepared, context="translator:sec:display-math")
        self.assertEqual(restored, raw_text)
        self.assertGreaterEqual(len(re.findall(r"@@HF:INLMATH:", prepared)), 2)
        self.assertNotIn("$$x_i = y_i$$", prepared)
        self.assertNotIn("\\[z = 1\\]", prepared)

    def test_translate_section_uses_core_translatable_content_and_reattaches_shells(self):
        agent = _build_agent(trans_mode=0)
        section = {
            "section": "3",
            "content": "<PLACEHOLDER_ENV_3>\n\\end{snugshade*}\nHello world.\n\\begin{appendix}",
            "core_translatable_content": "Hello world.\n",
            "leading_structure_shell": "<PLACEHOLDER_ENV_3>\n\\end{snugshade*}\n",
            "trailing_structure_shell": "\\begin{appendix}",
            "contains_structure_shell": True,
            "structure_shell_only": False,
            "previous_context": "",
        }
        session = _mock_success_session("你好世界。\n")

        translated = asyncio.run(agent._translate_section(section, session))

        self.assertEqual(
            translated["trans_content"],
            "<PLACEHOLDER_ENV_3>\n\\end{snugshade*}\n你好世界。\\begin{appendix}",
        )
        payload = session.post.call_args.kwargs["json"]["messages"][1]["content"]
        self.assertIn("Hello world.", payload)
        self.assertNotIn("snugshade", payload)
        self.assertNotIn("<PLACEHOLDER_ENV_3>", payload)

    def test_reassemble_section_translation_strips_document_boundary_leaks_without_structure_shell(self):
        agent = _build_agent(trans_mode=0)
        section = {
            "section": "11",
            "contains_structure_shell": False,
        }

        reassembled = agent._reassemble_section_translation(
            section,
            "Translated body.\n\\end{document}\nMore translated body.",
        )

        self.assertNotIn("\\begin{document}", reassembled)
        self.assertNotIn("\\end{document}", reassembled)
        self.assertIn("Translated body.", reassembled)
        self.assertIn("More translated body.", reassembled)

    def test_translate_section_marks_payload_invariant_passthrough_without_noop_retry(self):
        agent = _build_agent(trans_mode=0)
        section = {
            "section": "9",
            "content": "This section should not become a noop retry.",
            "previous_context": "",
        }

        async def fake_request(system_prompt, text, fail_part, type, session, previous_context=None):
            agent._mark_api_fallback(type, str(fail_part), "invariant_raw_structure_exposed")
            return text

        agent._request_llm_for_trans = fake_request

        translated = asyncio.run(agent._translate_section(section, MagicMock()))

        self.assertEqual(
            translated["translation_status"],
            agent.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
        )
        self.assertEqual(translated["fallback_reason"], "invariant_raw_structure_exposed")
        self.assertNotIn("9", agent.noop_sections)
        self.assertIn("9", agent.payload_invariant_sections)
        self.assertFalse(translated.get("no_op_detected", False))

    def test_translate_section_rejects_mutated_hard_freeze_output_without_persisting_it(self):
        agent = _build_agent(trans_mode=0)
        section = {
            "section": "13",
            "content": "Alpha <PLACEHOLDER_ENV_1> Beta <PLACEHOLDER_CAP_2>",
            "previous_context": "",
        }
        with patch(
            "backend.app.services.latex.utils.secrets.token_hex",
            return_value="EE11AA22",
        ):
            prepared_text, _ = agent._prepare_llm_payload_text(section["content"])
            hard_freeze_tokens = [
                chunk for chunk in prepared_text.split() if chunk.startswith("@@HF:")
            ]
            session = _mock_success_session(
                f"Alpha {hard_freeze_tokens[1]} Beta {hard_freeze_tokens[0]}"
            )
            translated = asyncio.run(agent._translate_section(section, session))

        self.assertEqual(translated["trans_content"], section["content"])
        self.assertEqual(
            translated["translation_status"],
            agent.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
        )
        self.assertEqual(
            translated["fallback_reason"],
            "invariant_hard_freeze_protocol_violation",
        )
        self.assertNotIn("@@HF:", translated["trans_content"])
        self.assertIn("13", agent.payload_invariant_sections)

    def test_hard_freeze_can_be_disabled_for_legacy_core_path(self):
        agent = _build_agent(extra_config={"enable_hard_freeze_tokens": False})
        prepared, context = agent._prepare_llm_payload_text("We compare $x$ with \\cite{a}.")

        self.assertNotIn("@@HF:", prepared)
        self.assertEqual(context["hard_freeze_token_sequence"], [])
        assert_no_raw_structure(prepared, context="translator-legacy-core")

        math_token = re.search(r"<INLMATH_[^>]+>", prepared).group(0)
        restored = agent._restore_llm_output_text(f"我们比较 {math_token} 与 \\cite{{a}}。", context)
        self.assertEqual(restored, "我们比较 $x$ 与 \\cite{a}。")

    def test_translate_caption_round_trips_hard_freeze_tokens(self):
        agent = _build_agent(trans_mode=0)
        caption = {
            "placeholder": "<PLACEHOLDER_CAP_9>",
            "content": "Caption uses $x_i$ in the figure.",
        }
        session = _mock_echo_user_payload_session()

        with patch(
            "backend.app.services.latex.utils.secrets.token_hex",
            return_value="A1B2C3D4",
        ):
            translated = asyncio.run(agent._translate_caption(caption, session))

        self.assertEqual(translated["trans_content"], caption["content"])
        user_payload = session.post.call_args.kwargs["json"]["messages"][1]["content"]
        self.assertIn("@@HF:INLMATH:", user_payload)
        self.assertNotIn("$x_i$", user_payload)

    def test_translate_generic_text_env_round_trips_hard_freeze_tokens(self):
        agent = _build_agent(trans_mode=0)
        env = {
            "placeholder": "<PLACEHOLDER_ENV_10>",
            "env_name": "theorem",
            "content": "\\begin{theorem}Keep $x_i$ stable.\\end{theorem}",
            "need_trans": True,
        }
        session = _mock_echo_user_payload_session()

        with patch(
            "backend.app.services.latex.utils.secrets.token_hex",
            return_value="B1C2D3E4",
        ):
            translated = asyncio.run(agent._translate_env(env, session))

        self.assertEqual(translated["trans_content"], env["content"])
        payloads = [
            call.kwargs["json"]["messages"][1]["content"]
            for call in session.post.call_args_list
        ]
        self.assertTrue(any("@@HF:INLMATH:" in payload for payload in payloads))
        self.assertTrue(any("\\begin{theorem}" not in payload for payload in payloads))

    def test_translate_list_env_round_trips_hard_freeze_tokens(self):
        agent = _build_agent(trans_mode=0)
        env = {
            "placeholder": "<PLACEHOLDER_ENV_11>",
            "env_name": "itemize",
            "content": "\\begin{itemize}\n\\item First item\n\\item Second item\n\\end{itemize}",
            "need_trans": True,
        }
        session = _mock_echo_user_payload_session()

        with patch(
            "backend.app.services.latex.utils.secrets.token_hex",
            return_value="C1D2E3F4",
        ):
            translated = asyncio.run(agent._translate_env(env, session))

        self.assertEqual(translated["trans_content"], env["content"])
        payloads = [
            call.kwargs["json"]["messages"][1]["content"]
            for call in session.post.call_args_list
        ]
        self.assertTrue(any("@@HF:CMD:" in payload for payload in payloads))
        self.assertTrue(any("\\item" not in payload for payload in payloads))

    def test_translate_eqnarray_env_round_trips_hard_freeze_tokens(self):
        agent = _build_agent(trans_mode=0)
        env = {
            "placeholder": "<PLACEHOLDER_ENV_12>",
            "env_name": "eqnarray",
            "content": "\\begin{eqnarray}where x is stable\\\\a&=&b\\end{eqnarray}",
            "need_trans": True,
        }
        session = _mock_echo_user_payload_session()

        with patch(
            "backend.app.services.latex.utils.secrets.token_hex",
            return_value="D1E2F3A4",
        ):
            translated = asyncio.run(agent._translate_env(env, session))

        self.assertIn("where x is stable", translated["trans_content"])
        user_payload = session.post.call_args.kwargs["json"]["messages"][1]["content"]
        self.assertIn("@@HF:CMD:", user_payload)
        self.assertNotIn("<EQROW_0>", user_payload)

    def test_translate_section_falls_back_when_env_restore_marker_leaks(self):
        agent = _build_agent(trans_mode=0)
        agent._request_llm_for_trans = AsyncMock(return_value="broken chunk\n<ENV_RESTORE_FAILED>")
        section = {
            "section": "8",
            "content": "Original section content with <PLACEHOLDER_ENV_1>.\n",
            "previous_context": "",
        }

        translated = asyncio.run(agent._translate_section(section, MagicMock()))

        self.assertEqual(translated["trans_content"], section["content"])
        self.assertEqual(
            translated["translation_status"],
            agent.STATUS_FALLBACK_SOURCE_API_FAILURE,
        )
        self.assertEqual(
            translated["fallback_reason"],
            "section_env_restore_preserved_source",
        )

    def test_compile_first_fallback_marks_section_pending_compile_without_mutating_content(self):
        agent = _build_agent(trans_mode=1)
        agent.enable_compile_first_structural_fallback = True
        agent.structural_fallback_denominator = 10
        section_part = {
            "section": "7",
            "content": "\\bibliography{refs}\n\\end{document}\n\\endinput\n",
            "trans_content": "",
        }
        error = {"num_or_ph": "7", "error_type": "C2", "command_error": "bad tail"}

        applied = agent._apply_compile_first_fallback(section_part, error, recheck_report=error)

        self.assertTrue(applied)
        self.assertEqual(section_part["trans_content"], "")
        self.assertEqual(
            section_part["translation_status"],
            agent.STATUS_STRUCTURAL_FALLBACK_PENDING_COMPILE,
        )
        self.assertEqual(
            section_part["fallback_reason"],
            "compile_first_structural_fallback:C2_structural_validation_failed",
        )
        self.assertEqual(agent.structural_fallback_parts, ["7"])

    def test_translate_skips_chunked_document_root_sections(self):
        agent = _build_agent(trans_mode=0)
        section = {
            "section": "-1_chunk_1",
            "chunk_role": "document_root",
            "content": "\\documentclass{article}\n\\usepackage{times}\n",
            "previous_context": "",
        }
        agent._translate_section = AsyncMock(side_effect=AssertionError("document_root should not be translated"))

        translated = asyncio.run(agent.translate(section, [], [], MagicMock()))

        self.assertEqual(translated["trans_content"], section["content"])
        self.assertEqual(translated["translation_status"], agent.STATUS_IMMUTABLE_PASSTHROUGH)
        self.assertFalse(translated["translated"])
        agent._translate_section.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
