import asyncio
from typing import Any

import pytest

from backend.app.services import community_agent_service


def _citation(index: int, *, query: str) -> dict[str, Any]:
    return {
        "id": f"paper-{query}-{index}",
        "title": f"{query} evidence paper {index}",
        "url": f"/paper/paper-{query}-{index}",
        "source": "community",
        "arxiv_id": f"2603.{10000 + index}",
        "paper_id": f"paper-{query}-{index}",
        "snippet": f"Evidence {index} for {query}",
    }


def test_deep_research_mode_returns_long_form_report_with_bounded_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_community_search_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        del runtime_state
        query = str(arguments["query"]).replace(" ", "-")
        limit = int(arguments.get("limit") or 5)
        return {
            "query_executed": arguments["query"],
            "results": [_citation(i + 1, query=query) for i in range(limit)],
            "count": limit,
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.community_search.CommunitySearchPapersSkill.execute",
        fake_community_search_execute,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "Summarize retrieval augmented generation evaluation papers",
            {"source": "conversation"},
            {"external_search": False},
            execution_mode="blocking",
            run_mode="deep_research",
            access_token="header.payload.signature",
        )
    )

    assert result["status"] == "completed"
    assert result["mode"] == "deep_research"
    assert result["report"] is not None
    assert 15 <= int(result["report"]["evidence_count"]) <= 20
    assert int(result["report"]["target_min_evidence"]) == 15
    assert int(result["report"]["target_max_evidence"]) == 20
    assert isinstance(result["message"], str) and "## Executive Summary" in result["message"]
    assert len(result["citations"]) <= 20


def test_deep_research_mode_reports_partial_coverage_when_evidence_is_too_sparse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_community_search_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        del arguments, runtime_state
        return {
            "query_executed": "sparse-query",
            "results": [
                _citation(1, query="sparse"),
                _citation(2, query="sparse"),
                _citation(3, query="sparse"),
            ],
            "count": 3,
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.community_search.CommunitySearchPapersSkill.execute",
        fake_community_search_execute,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "Find sparse evidence for a niche topic",
            {"source": "conversation"},
            {"external_search": False},
            execution_mode="blocking",
            run_mode="deep_research",
            access_token="header.payload.signature",
        )
    )

    assert result["mode"] == "deep_research"
    assert result["report"]["partial_coverage"] is True
    assert "partial" in str(result["report"]["coverage_note"]).lower()
