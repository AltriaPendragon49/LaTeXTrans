from backend.app.services.agents.translator_agent import TranslatorAgent
from backend.app.services.latex.utils import verify_hard_freeze_token_stream


def _build_agent() -> TranslatorAgent:
    return TranslatorAgent(
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


def _token_sequence_for(text: str):
    agent = _build_agent()
    _, context = agent._prepare_llm_payload_text(text)
    return (
        context["hard_freeze_token_sequence"],
        context["hard_freeze_audit_entries"],
        context["mask_mapping"],
    )


def test_relaxed_section_mode_accepts_reordered_low_risk_command_tokens():
    text = (
        "前文 "
        "\\keywords{diffusion, alignment} "
        "正文 "
        "\\received{March 2026} "
        "尾句。"
    )
    expected_tokens, audit_entries, mask_mapping = _token_sequence_for(text)
    actual = f"前文 {expected_tokens[1]} 正文 {expected_tokens[0]} 尾句。"

    verify_hard_freeze_token_stream(
        actual,
        expected_tokens,
        audit_entries=audit_entries,
        mask_mapping=mask_mapping,
        verification_mode="section_relaxed",
    )


def test_relaxed_section_mode_still_rejects_reordered_high_risk_reference_tokens():
    text = "参见 \\cref{eq:test}，随后参考 \\citep{smith2024}。"
    expected_tokens, audit_entries, mask_mapping = _token_sequence_for(text)
    actual = f"参见 {expected_tokens[1]}，随后参考 {expected_tokens[0]}。"

    try:
        verify_hard_freeze_token_stream(
            actual,
            expected_tokens,
            audit_entries=audit_entries,
            mask_mapping=mask_mapping,
            verification_mode="section_relaxed",
        )
    except ValueError as exc:
        assert "hard_freeze_token_stream_mismatch" in str(exc)
    else:
        raise AssertionError("reordered high-risk reference tokens must still fail")


def test_relaxed_section_mode_still_rejects_missing_tokens():
    text = "Alpha \\keywords{diffusion} Beta \\received{March 2026}"
    expected_tokens, audit_entries, mask_mapping = _token_sequence_for(text)

    try:
        verify_hard_freeze_token_stream(
                f"Alpha {expected_tokens[0]} Beta",
                expected_tokens,
                audit_entries=audit_entries,
                mask_mapping=mask_mapping,
                verification_mode="section_relaxed",
            )
    except ValueError as exc:
        assert "hard_freeze_token_stream_mismatch" in str(exc)
    else:
        raise AssertionError("missing protected tokens must still fail in relaxed mode")
