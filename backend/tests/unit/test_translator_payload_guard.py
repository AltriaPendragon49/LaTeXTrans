import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from backend.app.services.agents.pipeline_invariants import assert_no_raw_structure
from backend.app.services.agents.translator_agent import TranslatorAgent


def _build_agent(trans_mode: int = 0) -> TranslatorAgent:
    agent = TranslatorAgent(
        config={
            "llm_config": {
                "model": "gpt-4o",
                "base_url": "http://dummy-llm",
                "api_key": "dummy-key",
            }
        },
        project_dir="dummy",
        output_dir="dummy",
        trans_mode=trans_mode,
    )
    agent.prompts = {
        "section_system_prompt": "Translate section content.",
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


class TestTranslatorPayloadGuard(unittest.TestCase):
    def test_prepare_llm_payload_text_masks_preamble_command_arguments(self):
        agent = _build_agent()
        text = (
            "\\documentclass{article}\n"
            "\\usepackage{iclr2022_conference,times}\n"
            "\\input{math_commands.tex}\n"
            "\\title{LoRA}\n"
        )

        prepared, context = agent._prepare_llm_payload_text(text)

        self.assertIn("<PROTECTED_CMD_", prepared)
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
        self.assertIn("<PROTECTED_CMD_", prepared_1)
        self.assertNotIn("<ENV_BEGIN_1>", prepared_1)
        self.assertNotIn("<ENV_END_1>", prepared_1)

    def test_call_llm_with_freeze_masks_structure_before_send_and_restores_response(self):
        agent = _build_agent()
        user_text = "\\begin{document}\n\\end{document}\n\\endinput\n\\bibliography{refs}"
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
        self.assertIn("<PROTECTED_CMD_", user_payload)
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
        self.assertIn("<PROTECTED_CMD_", user_payload)
        self.assertNotIn("<ENV_BEGIN_1>", user_payload)
        self.assertNotIn("<ENV_END_2>", user_payload)

    def test_translate_section_restores_structure_only_sections_after_llm_response(self):
        agent = _build_agent(trans_mode=0)
        section = {
            "section": "7",
            "content": "\\begin{document}\n<PLACEHOLDER_CAP_1>\n\\end{document}\n\\endinput",
            "previous_context": "",
        }
        prepared_section, _ = agent._prepare_llm_payload_text(section["content"])
        session = _mock_success_session(prepared_section)

        translated = asyncio.run(agent._translate_section(section, session))

        self.assertEqual(translated["trans_content"], section["content"])
        self.assertEqual(translated["translation_status"], agent.STATUS_TRANSLATED)
        self.assertEqual(session.post.call_count, 1)
        payload = session.post.call_args.kwargs["json"]
        user_payload = payload["messages"][1]["content"]
        assert_no_raw_structure(user_payload, context="translator:sec:7")
        self.assertIn("<PROTECTED_CMD_", user_payload)
        self.assertNotIn("<PLACEHOLDER_CAP_1>", user_payload)
        self.assertNotIn("<ENV_BEGIN_1>", user_payload)
        self.assertNotIn("<ENV_END_1>", user_payload)

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
        self.assertIn("<PROTECTED_CMD_", prepared)

    def test_prepare_llm_payload_text_masks_display_math_and_restores_it(self):
        agent = _build_agent()
        raw_text = "We optimize $$x_i = y_i$$ and \\[z = 1\\] in context."

        prepared, context = agent._prepare_llm_payload_text(raw_text)
        restored = agent._restore_llm_output_text(prepared, context)

        assert_no_raw_structure(prepared, context="translator:sec:display-math")
        self.assertEqual(restored, raw_text)
        self.assertGreaterEqual(prepared.count("<INLMATH_"), 2)
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
