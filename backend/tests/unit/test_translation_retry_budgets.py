from backend.app.services.agents.translator_agent import TranslatorAgent


def _make_agent() -> TranslatorAgent:
    return TranslatorAgent(
        config={
            "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"},
            "source_language": "en",
            "target_language": "zh",
        },
        project_dir="dummy",
        output_dir="dummy",
        trans_mode=1,
        errors_report=[],
    )


def test_nested_rescue_stops_after_part_and_task_caps() -> None:
    agent = _make_agent()
    agent._RESCUE_MAX_NESTED_LLM_CALLS_PER_BASE_PART = 4
    agent._RESCUE_MAX_NESTED_LLM_CALLS_PER_TASK = 5  # type: ignore[attr-defined]

    results = [
        agent._reserve_nested_rescue_attempt("sec", "1:fragment:0"),
        agent._reserve_nested_rescue_attempt("sec", "1:fragment:1"),
        agent._reserve_nested_rescue_attempt("sec", "1:fragment:2"),
        agent._reserve_nested_rescue_attempt("sec", "1:fragment:3"),
        agent._reserve_nested_rescue_attempt("sec", "1:fragment:4"),
        agent._reserve_nested_rescue_attempt("sec", "2:fragment:0"),
    ]

    assert results == [True, True, True, True, False, False]


def test_api_failure_statuses_are_skipped_by_outer_retry_loop() -> None:
    agent = _make_agent()

    assert agent._should_skip_fail_part_retry({"translation_status": agent.STATUS_FALLBACK_SOURCE_API_FAILURE}) is True


def test_task_level_remedial_budget_caps_at_forty_calls() -> None:
    agent = _make_agent()

    results = [
        agent._reserve_remedial_llm_call(
            "paragraph_rescue",
            part_type="sec",
            identifier=f"rescue-{idx}",
        )
        for idx in range(41)
    ]

    assert results[:40] == [True] * 40
    assert results[40] is False
    assert agent._remedial_llm_call_count == 40
    assert agent._remedial_budget_exhausted_reason == "task_remedial_llm_budget_exhausted"
    assert (
        agent._get_api_fallback_reason("sec", "rescue-40")
        == "task_remedial_llm_budget_exhausted"
    )


def test_first_pass_calls_do_not_consume_task_level_remedial_budget() -> None:
    agent = _make_agent()

    reserved = agent._reserve_remedial_llm_call(
        None,
        part_type="sec",
        identifier="baseline-section",
    )

    assert reserved is True
    assert agent._remedial_llm_call_count == 0
    assert agent._remedial_budget_exhausted_reason is None


def test_hard_freeze_violation_budget_caps_at_eight_events() -> None:
    agent = _make_agent()

    exhaustion_markers = [
        agent._record_hard_freeze_protocol_violation(
            part_type="sec",
            identifier=f"hard-freeze-{idx}",
        )
        for idx in range(8)
    ]

    assert exhaustion_markers == [False, False, False, False, False, False, False, True]
    assert agent._hard_freeze_protocol_violation_count == 8
    assert (
        agent._remedial_budget_exhausted_reason
        == "hard_freeze_protocol_violation_budget_exhausted"
    )
    assert (
        agent._get_api_fallback_reason("sec", "hard-freeze-7")
        == "hard_freeze_protocol_violation_budget_exhausted"
    )
