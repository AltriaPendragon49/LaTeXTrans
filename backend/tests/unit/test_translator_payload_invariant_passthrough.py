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

    def test_translate_generic_text_env_marks_payload_invariant_passthrough(self):
        agent = _build_agent()
        env = {
            "placeholder": "<PLACEHOLDER_ENV_44>",
            "env_name": "theorem",
            "content": "\\begin{theorem}Stable body.\\end{theorem}",
            "need_trans": True,
        }

        agent._request_env_translation = AsyncMock(return_value=env["content"])
        agent._mark_api_fallback("env", env["placeholder"], "invariant_hard_freeze_protocol_violation")

        translated = asyncio.run(agent._translate_env(env, MagicMock()))

        self.assertEqual(translated["trans_content"], env["content"])
        self.assertEqual(
            translated["translation_status"],
            agent.STATUS_PAYLOAD_INVARIANT_PASSTHROUGH,
        )
        self.assertEqual(
            translated["fallback_reason"],
            "invariant_hard_freeze_protocol_violation",
        )

    def test_register_llm_part_failure_deduplicates_identifiers(self):
        agent = _build_agent()

        agent._register_llm_part_failure("env", "<PLACEHOLDER_ENV_44>")
        agent._register_llm_part_failure("env", "<PLACEHOLDER_ENV_44>")
        agent._register_llm_part_failure("cap", "<PLACEHOLDER_CAP_8>")
        agent._register_llm_part_failure("cap", "<PLACEHOLDER_CAP_8>")

        self.assertEqual(agent.fail_env_phs, ["<PLACEHOLDER_ENV_44>"])
        self.assertEqual(agent.fail_caption_phs, ["<PLACEHOLDER_CAP_8>"])


if __name__ == "__main__":
    unittest.main()
