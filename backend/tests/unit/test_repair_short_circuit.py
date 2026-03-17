import asyncio

from backend.app.services.agents.pipeline_schema import FallbackReport
from backend.app.services.agents.translation_repair_agent import TranslationRepairAgent


def test_repair_skips_immutable_chunk_without_llm_call():
    agent = TranslationRepairAgent(
        config={"llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"}}
    )

    async def _repair_one(*args, **kwargs):
        raise AssertionError("_repair_one must not run for immutable chunks")

    agent._repair_one = _repair_one  # type: ignore[method-assign]

    report = FallbackReport(
        fallback_kind="c2_structural_collapse",
        chunk_scope="10_chunk_2",
        root_cause="placeholder_only",
        validation_evidence={"ph_error": "Missing placeholders: <PLACEHOLDER_ENV_25>"},
        translated_text="<PLACEHOLDER_ENV_25>",
    )
    sections = [{
        "section": "10_chunk_2",
        "content": "<PLACEHOLDER_ENV_25>",
        "trans_content": "<PLACEHOLDER_ENV_25>",
        "immutable_only": True,
        "chunk_kind": "placeholder_only",
        "translatable_char_count": 0,
        "translation_status": "immutable_passthrough",
    }]

    repaired_sections, repaired_envs, events = asyncio.run(agent.repair([report], sections, []))

    assert repaired_envs == []
    assert repaired_sections[0]["translation_status"] == "repair_skipped_non_translatable"
    assert repaired_sections[0]["repair_rejection_reason"] == "non-translatable-chunk"
    assert events == [{
        "event": "repair_skipped_immutable_chunk",
        "chunk_scope": "10_chunk_2",
        "fallback_kind": "c2_structural_collapse",
    }]


def test_repair_deduplicates_same_failure_signature():
    agent = TranslationRepairAgent(
        config={"llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"}}
    )
    call_count = {"value": 0}

    async def _repair_one(*args, **kwargs):
        call_count["value"] += 1
        return "fixed", None

    agent._repair_one = _repair_one  # type: ignore[method-assign]

    report_a = FallbackReport(
        fallback_kind="c1_structural_rollback",
        chunk_scope="4_chunk_1",
        root_cause="same-root",
        validation_evidence={"math_error": "math_delimiter_mismatch: original has 2 inline $, translation has 1"},
        translated_text="broken",
    )
    report_b = FallbackReport(
        fallback_kind="c1_structural_rollback",
        chunk_scope="4_chunk_1",
        root_cause="same-root",
        validation_evidence={"math_error": "math_delimiter_mismatch: original has 2 inline $, translation has 1"},
        translated_text="broken",
    )
    sections = [{
        "section": "4_chunk_1",
        "content": "broken",
        "trans_content": "broken",
        "translatable_char_count": 42,
    }]

    repaired_sections, _repaired_envs, events = asyncio.run(agent.repair([report_a, report_b], sections, []))

    assert call_count["value"] == 1
    assert repaired_sections[0]["trans_content"] == "fixed"
    assert any(event["event"] == "repair_deduplicated_same_failure" for event in events)
