import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.services.agents.translator_agent import TranslatorAgent


def _build_agent(extra_config: dict | None = None) -> TranslatorAgent:
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
        trans_mode=0,
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


def test_legacy_translation_core_uses_origin_order_and_skips_front_matter():
    agent = _build_agent()
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

    assert "trans_content" not in skipped
    assert translated["trans_content"] == "SEC:1"
    assert calls == [
        ("env", "<PLACEHOLDER_ENV_1>"),
        ("cap", "<PLACEHOLDER_CAP_1>"),
        ("sec", "1"),
        ("env", "<PLACEHOLDER_ENV_1>"),
        ("cap", "<PLACEHOLDER_CAP_2>"),
        ("cap", "<PLACEHOLDER_CAP_1>"),
    ]


def test_single_key_api_call_uses_direct_origin_style_post():
    agent = _build_agent()
    session = _mock_success_session("translated")

    with patch(
        "backend.app.services.agents.translator_agent.post_chat_completion_with_pool",
        new=AsyncMock(side_effect=AssertionError("single-key parity mode must not use token pool transport")),
    ):
        result = asyncio.run(
            agent._legacy_request_llm_for_trans(
                "Translate.",
                "Source text",
                fail_part="1",
                type="sec",
                session=session,
            )
        )

    assert result == "translated"
    assert session.post.call_count == 1
    assert session.post.call_args.kwargs["json"]["messages"][1]["content"] == "Source text"
    assert "X-LLM-Pool-Member" not in session.post.call_args.kwargs["headers"]
    assert session.post.call_args.kwargs["timeout"].total == 100


def test_payload_mask_restore_uses_plain_placeholders():
    agent = _build_agent()
    source = r"\section{Intro} Body with $x_i$ and \ref{eq:a}."

    prepared, context = agent._prepare_llm_payload_text(source)
    restored = agent._restore_llm_output_text(prepared, context)

    assert "@@HF:" not in prepared
    assert set(context) == {"math_map", "env_map", "mask_mapping"}
    assert "<INLMATH_" in prepared
    assert "<PROTECTED_CMD_" in prepared
    assert restored == source
