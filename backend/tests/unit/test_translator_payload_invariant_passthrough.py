import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from backend.app.services.agents.translator_agent import TranslatorAgent


def _build_agent() -> TranslatorAgent:
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
        trans_mode=0,
    )
    agent.prompts = {
        "caption_system_prompt": "Translate caption content.",
        "env_system_prompt": "Translate environment content.",
        "section_system_prompt": "Translate section content.",
        "retrans_error_parts_system_prompt": "Fix translated content.",
    }
    return agent


class TestTranslatorPayloadInvariantPassthrough(unittest.TestCase):
    def test_register_llm_part_failure_normalizes_nested_identifiers(self):
        agent = _build_agent()

        agent._register_llm_part_failure("sec", "4_1:paragraph:6")
        agent._register_llm_part_failure("sec", "4_1:paragraph:0:fragment:1")
        agent._register_llm_part_failure("cap", "<PLACEHOLDER_CAP_8>:paragraph:0")
        agent._register_llm_part_failure("env", "part:env:<PLACEHOLDER_ENV_44>:row:0")

        self.assertEqual(agent.fail_section_nums, ["4_1"])
        self.assertEqual(agent.fail_caption_phs, ["<PLACEHOLDER_CAP_8>"])
        self.assertEqual(agent.fail_env_phs, ["<PLACEHOLDER_ENV_44>"])

    def test_translate_section_successful_rescue_clears_fail_queue(self):
        agent = _build_agent()
        section = {
            "section": "12",
            "content": "This section should leave no stale fail queue entry after rescue.",
            "previous_context": "",
        }

        async def fake_request(*args, **kwargs):
            agent._register_llm_part_failure("sec", section["section"])
            agent._mark_api_fallback("sec", section["section"], "invariant_hard_freeze_protocol_violation")
            return section["content"]

        agent._request_llm_for_trans = fake_request
        agent._rescue_plain_text_by_paragraph = AsyncMock(return_value="Recovered Chinese content.")

        translated = asyncio.run(agent._translate_section(section, MagicMock()))

        self.assertEqual(translated["translation_status"], agent.STATUS_TRANSLATED)
        self.assertEqual(agent.fail_section_nums, [])
        self.assertFalse(agent.have_fail_parts)

    def test_translate_section_payload_invariant_non_source_candidate_uses_paragraph_rescue(self):
        agent = _build_agent()
        section = {
            "section": "13+13_1",
            "content": (
                "\\section{Additional Empirical Results}\n\n"
                "\\subsection{Performance of Best of $N$ baseline for Various $N$}\n"
                "We find that the Best of $N$ baseline remains strong."
            ),
            "previous_context": "",
        }
        unsafe_candidate = (
            "\\section{其他实证结果}\n\n"
            "\\subsection{最佳表现} $N$ 各种方法的基线 $N$}\n"
            "我们发现，$N$ 基线仍然很强。"
        )
        rescued_candidate = (
            "\\section{其他实证结果}\n\n"
            "\\subsection{各种 $N$ 下 Best of $N$ 基线的表现}\n"
            "我们发现，Best of $N$ 基线仍然很强。"
        )

        async def fake_request(*args, **kwargs):
            agent._mark_api_fallback("sec", section["section"], "invariant_hard_freeze_protocol_violation")
            return unsafe_candidate

        agent._request_llm_for_trans = fake_request
        agent._rescue_plain_text_by_paragraph = AsyncMock(return_value=rescued_candidate)

        translated = asyncio.run(agent._translate_section(section, MagicMock()))

        self.assertEqual(translated["trans_content"], rescued_candidate)
        self.assertEqual(translated["translation_status"], agent.STATUS_TRANSLATED)
        self.assertNotIn("payload_invariant_passthrough", str(translated))

    def test_translate_section_payload_invariant_non_source_candidate_never_persists_unsafe_text(self):
        agent = _build_agent()
        section = {
            "section": "13+13_1",
            "content": (
                "\\section{Additional Empirical Results}\n\n"
                "\\subsection{Performance of Best of $N$ baseline for Various $N$}\n"
                "We find that the Best of $N$ baseline remains strong."
            ),
            "previous_context": "",
        }
        unsafe_candidate = (
            "\\section{其他实证结果}\n\n"
            "\\subsection{最佳表现} $N$ 各种方法的基线 $N$}\n"
            "我们发现，$N$ 基线仍然很强。"
        )

        async def fake_request(*args, **kwargs):
            agent._mark_api_fallback("sec", section["section"], "invariant_hard_freeze_protocol_violation")
            return unsafe_candidate

        agent._request_llm_for_trans = fake_request
        agent._rescue_plain_text_by_paragraph = AsyncMock(return_value=None)

        translated = asyncio.run(agent._translate_section(section, MagicMock()))

        self.assertEqual(translated["trans_content"], section["content"])
        self.assertEqual(
            translated["translation_status"],
            agent.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
        )

    def test_translate_section_demotes_stray_sectioning_commands_from_translated_body(self):
        agent = _build_agent()
        section = {
            "section": "13+13_1",
            "content": (
                "\\section{Additional Empirical Results}\n\n"
                "\\subsection{Performance of Best of $N$ baseline for Various $N$}\n"
                "We find that the Best of $N$ baseline is strong in our experiments."
            ),
            "previous_context": "",
        }
        translated_candidate = (
            "\\section{补充实证结果}\n\n"
            "\\subsection{不同 $N$ 下 Best of $N$ 基线的表现}\n"
            "我们发现，Best of $N$ 基线在实验中依然很强。 "
            "我们给出了 Best of $N$ \\section{各种基准线} $N$ 在对话与摘要任务上的结果。"
        )

        agent._request_llm_for_trans = AsyncMock(return_value=translated_candidate)

        translated = asyncio.run(agent._translate_section(section, MagicMock()))

        self.assertEqual(translated["translation_status"], agent.STATUS_TRANSLATED)
        self.assertNotIn("\\section{各种基准线}", translated["trans_content"])
        self.assertIn("各种基准线", translated["trans_content"])
        self.assertTrue(translated.get("sectioning_command_drift_sanitized"))

    def test_rescue_plain_text_by_paragraph_falls_back_to_fragment_rescue(self):
        agent = _build_agent()
        text = (
            "First sentence stays in English on the coarse retry. "
            "<PLACEHOLDER_ENV_3> "
            "Second sentence should still be translated."
        )

        async def fake_request(*args, **kwargs):
            fail_part = kwargs["fail_part"]
            user_text = args[1]
            if fail_part == "7:paragraph:0":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return user_text
            if fail_part == "7:paragraph:0:fragment:0":
                return "绗竴鍙ヨ鏇寸粏绮掑害 rescue 鎴愬姛缈昏瘧銆? "
            if fail_part == "7:paragraph:0:fragment:2":
                return "绗簩鍙ヤ篃琚垚鍔熺炕璇戙€?"
            return user_text

        agent._request_llm_for_trans = AsyncMock(side_effect=fake_request)

        rescued = asyncio.run(
            agent._rescue_plain_text_by_paragraph(
                text=text,
                identifier="7",
                part_type="sec",
                session=MagicMock(),
            )
        )

        self.assertEqual(
            rescued,
            "绗竴鍙ヨ鏇寸粏绮掑害 rescue 鎴愬姛缈昏瘧銆? <PLACEHOLDER_ENV_3> 绗簩鍙ヤ篃琚垚鍔熺炕璇戙€?",
        )
        self.assertGreaterEqual(agent._request_llm_for_trans.await_count, 3)

    def test_rescue_plain_text_by_paragraph_fragment_rescue_masks_commands_and_placeholders(self):
        agent = _build_agent()
        text = (
            "With the reverse process defined in \\cref{eq:test}, "
            "we optimize <PLACEHOLDER_ENV_16> for sample quality."
        )

        seen_fragment_inputs = []

        async def fake_request(*args, **kwargs):
            fail_part = kwargs["fail_part"]
            user_text = args[1]
            if fail_part == "3:paragraph:0":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return text
            seen_fragment_inputs.append(user_text)
            if "\\cref{" in user_text:
                raise AssertionError("fragment rescue should not expose raw cref commands")
            if "<PLACEHOLDER_ENV_16>" in user_text:
                raise AssertionError("fragment rescue should not expose raw placeholders")
            mapping = {
                "3:paragraph:0:fragment:0": "The translated discussion ",
                "3:paragraph:0:fragment:2": " explains the optimization target ",
                "3:paragraph:0:fragment:4": " and preserves sample quality.",
            }
            return mapping.get(fail_part, user_text)

        agent._request_llm_for_trans = AsyncMock(side_effect=fake_request)

        rescued = asyncio.run(
            agent._rescue_plain_text_by_paragraph(
                text=text,
                identifier="3",
                part_type="sec",
                session=MagicMock(),
            )
        )

        self.assertIn("\\cref{eq:test}", rescued)
        self.assertIn("<PLACEHOLDER_ENV_16>", rescued)
        self.assertNotEqual(rescued, text)
        self.assertGreaterEqual(len(seen_fragment_inputs), 3)

    def test_translate_plain_text_rescue_piece_retries_when_fragment_stays_source_preserved(self):
        agent = _build_agent()
        piece = "Diffusion models still need a translated rescue fragment."
        fail_part = "3:paragraph:0:fragment:0"

        async def fake_request(*args, **kwargs):
            current_fail_part = kwargs["fail_part"]
            if current_fail_part == fail_part:
                return piece
            if current_fail_part == f"{fail_part}:force":
                return "Translated fragment after force retry."
            return piece

        agent._request_llm_for_trans = AsyncMock(side_effect=fake_request)

        rescued = asyncio.run(
            agent._translate_plain_text_rescue_piece(
                piece=piece,
                fail_part=fail_part,
                part_type="sec",
                session=MagicMock(),
                error_message=None,
                paragraph_hint="force translation",
                prompt_suffix="\n[Paragraph Rescue]",
                prompt_key="section_system_prompt",
                prompt_key_with_terms=None,
            )
        )

        self.assertEqual(rescued, "Translated fragment after force retry.")
        self.assertEqual(agent._request_llm_for_trans.await_count, 2)

    def test_rescue_plain_text_by_paragraph_tries_masked_paragraph_before_fragment_rescue(self):
        agent = _build_agent()
        text = (
            "We discuss \\cref{eq:test} and optimize <PLACEHOLDER_ENV_16> for better samples."
        )

        async def fake_request(*args, **kwargs):
            fail_part = kwargs["fail_part"]
            user_text = args[1]
            if fail_part == "8:paragraph:0":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return text
            if fail_part == "8:paragraph:0:masked":
                if "\\cref{" in user_text:
                    raise AssertionError("masked paragraph rescue should not expose raw cref commands")
                if "<PLACEHOLDER_ENV_16>" in user_text:
                    raise AssertionError("masked paragraph rescue should only expose masked placeholders")
                return user_text.replace(
                    "We discuss ",
                    "Translated masked paragraph ",
                    1,
                )
            raise AssertionError(f"unexpected fail_part {fail_part}")

        agent._request_llm_for_trans = AsyncMock(side_effect=fake_request)

        rescued = asyncio.run(
            agent._rescue_plain_text_by_paragraph(
                text=text,
                identifier="8",
                part_type="sec",
                session=MagicMock(),
            )
        )

        self.assertEqual(
            rescued,
            "Translated masked paragraph \\cref{eq:test} and optimize <PLACEHOLDER_ENV_16> for better samples.",
        )
        self.assertEqual(agent._request_llm_for_trans.await_count, 2)

    def test_rescue_plain_text_by_paragraph_recursively_splits_long_failed_fragment(self):
        agent = _build_agent()
        text = (
            "Diffusion models require stable placeholder handling while preserving mathematical context "
            "across long rescue fragments without punctuation or explicit sentence boundaries so the "
            "fallback path must keep splitting until the model can translate each smaller window safely"
        )

        async def fake_request(*args, **kwargs):
            fail_part = kwargs["fail_part"]
            user_text = args[1]
            if fail_part == "11:paragraph:0":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return text
            if fail_part == "11:paragraph:0:masked":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return user_text
            if fail_part == "11:paragraph:0:window:0":
                return "扩散模型需要稳定的占位符保护，"
            if fail_part == "11:paragraph:0:window:1":
                return "并且在长片段回退时保持数学上下文，"
            if fail_part == "11:paragraph:0:window:2":
                return "因此系统必须继续细分，直到每个更小窗口都能安全翻译。"
            return user_text

        agent._request_llm_for_trans = AsyncMock(side_effect=fake_request)

        rescued = asyncio.run(
            agent._rescue_plain_text_by_paragraph(
                text=text,
                identifier="11",
                part_type="sec",
                session=MagicMock(),
            )
        )

        self.assertEqual(
            rescued,
            "扩散模型需要稳定的占位符保护，并且在长片段回退时保持数学上下文，因此系统必须继续细分，直到每个更小窗口都能安全翻译。",
        )
        self.assertGreaterEqual(agent._request_llm_for_trans.await_count, 5)

    def test_rescue_plain_text_by_paragraph_keeps_best_effort_translation_when_one_paragraph_fails(self):
        agent = _build_agent()
        text = (
            "The first paragraph remains hard to translate and may stay in English.\n\n"
            "The second paragraph should still become a readable Chinese downgrade with target language priority."
        )

        async def fake_request(*args, **kwargs):
            fail_part = kwargs["fail_part"]
            user_text = args[1]
            if fail_part == "18:paragraph:0":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return user_text
            if fail_part == "18:paragraph:0:force":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return user_text
            if fail_part == "18:paragraph:0:masked":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return user_text
            if fail_part == "18:paragraph:2":
                return "第二段已经被降级为可读的中文译文，并优先保留目标语言效果。"
            raise AssertionError(f"unexpected fail_part {fail_part}")

        agent._request_llm_for_trans = AsyncMock(side_effect=fake_request)

        rescued = asyncio.run(
            agent._rescue_plain_text_by_paragraph(
                text=text,
                identifier="18",
                part_type="sec",
                session=MagicMock(),
            )
        )

        self.assertIn("The first paragraph remains hard to translate", rescued)
        self.assertIn("第二段已经被降级为可读的中文译文", rescued)

    def test_rescue_plain_text_by_paragraph_accepts_best_effort_single_paragraph_window_rescue(self):
        agent = _build_agent()
        text = (
            "This long rescue paragraph keeps some English scientific tokens while "
            "the recovery path should still preserve a substantial Chinese downgrade "
            "instead of reverting the whole paragraph back to the original source text."
        )

        async def fake_request(*args, **kwargs):
            fail_part = kwargs["fail_part"]
            user_text = args[1]
            if fail_part == "21:paragraph:0":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return text
            if fail_part == "21:paragraph:0:force":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return user_text
            if fail_part == "21:paragraph:0:masked":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return user_text
            if fail_part == "21:paragraph:0:window:0":
                return "这一段已经被尽量降级成中文译文，"
            if fail_part == "21:paragraph:0:window:1":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return user_text
            if fail_part == "21:paragraph:0:window:1:force":
                agent._mark_api_fallback("sec", fail_part, "invariant_hard_freeze_protocol_violation")
                return user_text
            raise AssertionError(f"unexpected fail_part {fail_part}")

        agent._request_llm_for_trans = AsyncMock(side_effect=fake_request)

        rescued = asyncio.run(
            agent._rescue_plain_text_by_paragraph(
                text=text,
                identifier="21",
                part_type="sec",
                session=MagicMock(),
            )
        )

        self.assertIsNotNone(rescued)
        self.assertIn("这一段已经被尽量降级成中文译文", rescued)

    def test_rescue_plain_text_by_paragraph_stops_after_non_invariant_api_failure(self):
        agent = _build_agent()
        text = "This paragraph should not recurse into finer rescue levels after an API outage."

        async def fake_request(*args, **kwargs):
            fail_part = kwargs["fail_part"]
            if fail_part != "15:paragraph:0":
                raise AssertionError(f"unexpected nested rescue for {fail_part}")
            agent._mark_api_fallback("sec", fail_part, "api_request_failed_after_3_attempts")
            return text

        agent._request_llm_for_trans = AsyncMock(side_effect=fake_request)

        rescued = asyncio.run(
            agent._rescue_plain_text_by_paragraph(
                text=text,
                identifier="15",
                part_type="sec",
                session=MagicMock(),
            )
        )

        self.assertIsNone(rescued)
        self.assertEqual(agent._request_llm_for_trans.await_count, 1)

    def test_translate_section_rescues_payload_invariant_source_preservation_by_paragraph(self):
        agent = _build_agent()
        section = {
            "section": "12",
            "content": "This section should still become Chinese after an invariant hit.",
            "previous_context": "",
        }

        async def fake_request(*args, **kwargs):
            agent._mark_api_fallback("sec", section["section"], "invariant_hard_freeze_protocol_violation")
            return section["content"]

        agent._request_llm_for_trans = fake_request
        agent._rescue_plain_text_by_paragraph = AsyncMock(return_value="这一节在 invariant 后仍然被成功翻译。")

        translated = asyncio.run(agent._translate_section(section, MagicMock()))

        self.assertEqual(translated["trans_content"], "这一节在 invariant 后仍然被成功翻译。")
        self.assertEqual(translated["translation_status"], agent.STATUS_TRANSLATED)
        self.assertNotIn("fallback_reason", translated)
        agent._rescue_plain_text_by_paragraph.assert_awaited_once()

    def test_translate_caption_marks_payload_invariant_passthrough(self):
        agent = _build_agent()
        caption = {
            "placeholder": "<PLACEHOLDER_CAP_8>",
            "content": "Caption content that should remain source on invariant failure.",
        }

        async def fake_request(*args, **kwargs):
            agent._mark_api_fallback("cap", caption["placeholder"], "invariant_hard_freeze_protocol_violation")
            return caption["content"]

        agent._request_llm_for_trans = fake_request

        translated = asyncio.run(agent._translate_caption(caption, MagicMock()))

        self.assertEqual(translated["trans_content"], caption["content"])
        self.assertEqual(
            translated["translation_status"],
            agent.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
        )
        self.assertEqual(
            translated["fallback_reason"],
            "invariant_hard_freeze_protocol_violation",
        )

    def test_translate_caption_rescues_payload_invariant_source_preservation(self):
        agent = _build_agent()
        caption = {
            "placeholder": "<PLACEHOLDER_CAP_8>",
            "content": "Caption content should still be translated after invariant fallback.",
        }

        async def fake_request(*args, **kwargs):
            agent._mark_api_fallback("cap", caption["placeholder"], "invariant_hard_freeze_protocol_violation")
            return caption["content"]

        agent._request_llm_for_trans = fake_request
        agent._rescue_plain_text_by_paragraph = AsyncMock(return_value="图注在 invariant 后也被翻译。")

        translated = asyncio.run(agent._translate_caption(caption, MagicMock()))

        self.assertEqual(translated["trans_content"], "图注在 invariant 后也被翻译。")
        self.assertEqual(translated["translation_status"], agent.STATUS_TRANSLATED)
        self.assertNotIn("fallback_reason", translated)
        agent._rescue_plain_text_by_paragraph.assert_awaited_once()

    def test_translate_list_env_skips_item_rescue_after_non_invariant_api_failure(self):
        agent = _build_agent()
        env = {
            "placeholder": "<PLACEHOLDER_ENV_41>",
            "env_name": "itemize",
            "content": (
                "\\begin{itemize}\n"
                "    \\item The first item stays in English.\n"
                "    \\item The second item stays in English.\n"
                "\\end{itemize}"
            ),
            "need_trans": True,
        }

        async def fake_request_env_translation(*, text, placeholder, **kwargs):
            agent._mark_api_fallback("env", placeholder, "api_request_failed_after_3_attempts")
            return text

        agent._request_env_translation = AsyncMock(side_effect=fake_request_env_translation)
        agent._rescue_list_env_items = AsyncMock(return_value="should not be used")

        translated = asyncio.run(agent._translate_list_env(env, MagicMock()))

        self.assertEqual(
            translated["translation_status"],
            agent.STATUS_FALLBACK_SOURCE_API_FAILURE,
        )
        self.assertEqual(
            translated["fallback_reason"],
            "api_request_failed_after_3_attempts",
        )
        agent._rescue_list_env_items.assert_not_awaited()

    def test_translate_list_env_rescues_payload_invariant_items_individually(self):
        agent = _build_agent()
        env = {
            "placeholder": "<PLACEHOLDER_ENV_31>",
            "env_name": "itemize",
            "content": (
                "\\begin{itemize}\n"
                "    \\item We chose the beta schedule carefully.\n"
                "    \\item We tuned dropout for CIFAR10.\n"
                "\\end{itemize}"
            ),
            "need_trans": True,
        }

        async def fake_request_env_translation(*, text, placeholder, **kwargs):
            agent._mark_api_fallback("env", placeholder, "invariant_hard_freeze_protocol_violation")
            return text

        async def fake_rescue_plain_text_by_paragraph(*, text, identifier, **kwargs):
            mapping = {
                "<PLACEHOLDER_ENV_31>:item:0": "我们仔细选择了 beta 调度。",
                "<PLACEHOLDER_ENV_31>:item:1": "我们为 CIFAR10 调整了 dropout。",
            }
            return mapping.get(identifier)

        agent._request_env_translation = AsyncMock(side_effect=fake_request_env_translation)
        agent._rescue_plain_text_by_paragraph = AsyncMock(side_effect=fake_rescue_plain_text_by_paragraph)

        translated = asyncio.run(agent._translate_list_env(env, MagicMock()))

        self.assertIn("我们仔细选择了 beta 调度。", translated["trans_content"])
        self.assertIn("我们为 CIFAR10 调整了 dropout。", translated["trans_content"])
        self.assertEqual(translated["translation_status"], agent.STATUS_TRANSLATED)
        self.assertNotIn("fallback_reason", translated)

    def test_translate_generic_text_env_skips_plain_text_recovery_after_non_invariant_api_failure(self):
        agent = _build_agent()
        env = {
            "placeholder": "<PLACEHOLDER_ENV_52>",
            "env_name": "theorem",
            "content": "\\begin{theorem}English theorem body.\\end{theorem}",
            "need_trans": True,
        }

        agent._request_env_translation = AsyncMock(return_value=env["content"])
        agent._mark_api_fallback("env", env["placeholder"], "api_request_failed_after_3_attempts")
        agent._recover_generic_text_env_body_as_plain_text = AsyncMock(return_value="should not be used")
        agent._rescue_generic_text_env_by_paragraph = AsyncMock(return_value="should not be used")

        translated = asyncio.run(agent._translate_env(env, MagicMock()))

        self.assertEqual(
            translated["translation_status"],
            agent.STATUS_FALLBACK_SOURCE_API_FAILURE,
        )
        self.assertEqual(
            translated["fallback_reason"],
            "api_request_failed_after_3_attempts",
        )
        agent._recover_generic_text_env_body_as_plain_text.assert_not_awaited()
        agent._rescue_generic_text_env_by_paragraph.assert_not_awaited()

    def test_translate_generic_text_env_rescues_payload_invariant_source_preservation(self):
        agent = _build_agent()
        env = {
            "placeholder": "<PLACEHOLDER_ENV_44>",
            "env_name": "theorem",
            "content": "\\begin{theorem}Stable body.\\end{theorem}",
            "need_trans": True,
        }

        agent._request_env_translation = AsyncMock(return_value=env["content"])
        agent._mark_api_fallback("env", env["placeholder"], "invariant_hard_freeze_protocol_violation")
        agent._recover_generic_text_env_body_as_plain_text = AsyncMock(return_value="恢复后的中文定理内容。")
        agent._rescue_plain_text_by_paragraph = AsyncMock(return_value=None)

        translated = asyncio.run(agent._translate_env(env, MagicMock()))

        self.assertEqual(
            translated["trans_content"],
            "\\begin{theorem}恢复后的中文定理内容。\\end{theorem}",
        )
        self.assertEqual(
            translated["translation_status"],
            agent.STATUS_TRANSLATED,
        )
        self.assertNotIn("fallback_reason", translated)
        agent._recover_generic_text_env_body_as_plain_text.assert_awaited_once()

    def test_register_llm_part_failure_deduplicates_identifiers(self):
        agent = _build_agent()

        agent._register_llm_part_failure("env", "<PLACEHOLDER_ENV_44>")
        agent._register_llm_part_failure("env", "<PLACEHOLDER_ENV_44>")
        agent._register_llm_part_failure("cap", "<PLACEHOLDER_CAP_8>")
        agent._register_llm_part_failure("cap", "<PLACEHOLDER_CAP_8>")

        self.assertEqual(agent.fail_env_phs, ["<PLACEHOLDER_ENV_44>"])
        self.assertEqual(agent.fail_caption_phs, ["<PLACEHOLDER_CAP_8>"])

    def test_val_fail_parts_skips_payload_invariant_passthrough_retries(self):
        agent = _build_agent()
        agent.have_fail_parts = True
        agent.fail_section_nums = ["9"]
        agent.fail_caption_phs = ["<PLACEHOLDER_CAP_8>"]
        agent.fail_env_phs = ["<PLACEHOLDER_ENV_44>"]

        sections = [
            {
                "section": "9",
                "content": "Section source content",
                "trans_content": "Section source content",
                "translation_status": agent.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
            }
        ]
        captions = [
            {
                "placeholder": "<PLACEHOLDER_CAP_8>",
                "content": "Caption source content",
                "trans_content": "Caption source content",
                "translation_status": agent.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
            }
        ]
        envs = [
            {
                "placeholder": "<PLACEHOLDER_ENV_44>",
                "env_name": "theorem",
                "content": "\\begin{theorem}Stable body.\\end{theorem}",
                "trans_content": "\\begin{theorem}Stable body.\\end{theorem}",
                "translation_status": agent.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
                "need_trans": True,
            }
        ]

        agent._translate_section = AsyncMock(side_effect=AssertionError("section should not retry"))
        agent._translate_caption = AsyncMock(side_effect=AssertionError("caption should not retry"))
        agent._translate_env = AsyncMock(side_effect=AssertionError("env should not retry"))
        agent.save_file = MagicMock()

        asyncio.run(
            agent._val_fail_parts(
                sections=sections,
                captions=captions,
                envs=envs,
                Maxtry=3,
                session=MagicMock(),
            )
        )

        agent._translate_section.assert_not_awaited()
        agent._translate_caption.assert_not_awaited()
        agent._translate_env.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
