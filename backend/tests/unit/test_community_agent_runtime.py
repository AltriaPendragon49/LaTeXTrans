import asyncio

import pytest

from backend.app.services.community_agent.orchestrator import _extract_arxiv_id
from backend.app.services.community_agent.skills.start_translation_kernel import (
    StartTranslationKernelSkill,
)
from backend.app.services.community_agent.validator import (
    ValidationError,
    validate_search_query,
    validate_skill_call,
)


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("2602.24209讲了什么", "2602.24209"),
        ("请解释2602.24209这篇论文", "2602.24209"),
        ("2602.24209v2讲了什么", "2602.24209"),
        ("foo2602.24209bar", None),
    ],
)
def test_extract_arxiv_id_handles_cjk_adjacent_ids(prompt: str, expected: str | None) -> None:
    assert _extract_arxiv_id(prompt) == expected


def test_hidden_tool_calls_are_rejected_by_validator() -> None:
    with pytest.raises(ValidationError):
        validate_skill_call(
            skill_name="external_tavily_search",
            arguments={"query": "vision transformer", "max_results": 3},
            raw_input="Please search the web for recent vision transformer papers",
            visible_skill_names={"community_search_papers", "read_paper_context"},
        )


def test_query_extraction_quality_rejects_raw_utterance_search_query() -> None:
    with pytest.raises(ValidationError):
        validate_search_query(
            raw_input="Please search the web for recent diffusion papers and do not include surveys",
            query="Please search the web for recent diffusion papers and do not include surveys",
        )


def test_query_extraction_allows_title_like_raw_query() -> None:
    validate_search_query(
        raw_input="DA-Flow: Degradation-Aware Optical Flow Estimation with Diffusion Models",
        query="DA-Flow: Degradation-Aware Optical Flow Estimation with Diffusion Models",
    )


def test_translation_skill_wraps_full_kernel_only(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    async def fake_start_paper_translation(*, paper_id, request, credentials=None):  # type: ignore[no-untyped-def]
        calls["paper_id"] = paper_id
        calls["source_language"] = request.source_language
        calls["target_language"] = request.target_language
        return {
            "paper_id": paper_id,
            "task_id": "task-1",
            "status": "queued",
            "reused_existing_task": False,
            "processing_url": "/processing?task=task-1",
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.start_paper_translation",
        fake_start_paper_translation,
    )

    skill = StartTranslationKernelSkill()
    result = asyncio.run(
        skill.execute(
            {"paper_id": "paper-1", "source_language": "en", "target_language": "zh"},
            runtime_state=None,
        )
    )

    assert calls == {
        "paper_id": "paper-1",
        "source_language": "en",
        "target_language": "zh",
    }
    assert result["task_id"] == "task-1"


def test_translation_skill_forwards_submitter_user_id_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    async def fake_start_paper_translation(
        *,
        paper_id,
        request,
        credentials=None,
        submitter_user_id=None,
    ):  # type: ignore[no-untyped-def]
        calls["paper_id"] = paper_id
        calls["source_language"] = request.source_language
        calls["target_language"] = request.target_language
        calls["submitter_user_id"] = submitter_user_id
        return {
            "paper_id": paper_id,
            "task_id": "task-2",
            "status": "queued",
            "reused_existing_task": False,
            "processing_url": "/processing?task=task-2",
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.start_paper_translation",
        fake_start_paper_translation,
    )

    skill = StartTranslationKernelSkill()
    runtime_state = type("RuntimeState", (), {"context": {"user_id": "user-42"}})()
    result = asyncio.run(
        skill.execute(
            {"paper_id": "paper-2", "source_language": "en", "target_language": "zh"},
            runtime_state=runtime_state,
        )
    )

    assert calls["submitter_user_id"] == "user-42"
    assert result["task_id"] == "task-2"


def test_translation_skill_skips_redundant_start_for_prewarmed_translated_paper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    start_calls = {"count": 0}

    async def fake_get_community_paper_detail(
        *,
        paper_id: str,
        viewer_user_id=None,
        fast_path: bool = False,
    ):  # type: ignore[no-untyped-def]
        assert paper_id == "paper-3"
        assert viewer_user_id is None
        assert fast_path is True
        return {
            "paper": {
                "id": "paper-3",
                "community_selected_task_id": "task-prewarmed-3",
            },
            "reader": {"state": "translated_ready"},
            "reader_state": "ready",
        }

    async def fake_start_paper_translation(
        *,
        paper_id,
        request,
        credentials=None,
        submitter_user_id=None,
    ):  # type: ignore[no-untyped-def]
        del paper_id, request, credentials, submitter_user_id
        start_calls["count"] += 1
        return {
            "paper_id": "paper-3",
            "task_id": "task-should-not-run",
            "status": "queued",
            "reused_existing_task": False,
            "processing_url": "/processing?task=task-should-not-run",
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.get_community_paper_detail",
        fake_get_community_paper_detail,
    )
    monkeypatch.setattr(
        "backend.app.services.paper_service.start_paper_translation",
        fake_start_paper_translation,
    )

    skill = StartTranslationKernelSkill()
    result = asyncio.run(
        skill.execute(
            {"paper_id": "paper-3", "source_language": "en", "target_language": "zh"},
            runtime_state=None,
        )
    )

    assert start_calls["count"] == 0
    assert result["paper_id"] == "paper-3"
    assert result["task_id"] == "task-prewarmed-3"
    assert result["status"] == "translated_ready"
    assert result["reused_existing_task"] is True
