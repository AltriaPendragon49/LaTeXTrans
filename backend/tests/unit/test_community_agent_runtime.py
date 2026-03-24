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
