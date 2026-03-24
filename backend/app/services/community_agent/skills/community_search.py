from __future__ import annotations

from typing import Any, Dict, List

from backend.app.services import paper_service

from .base import AgentSkill


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _citation_from_paper(paper: Dict[str, Any], index: int) -> Dict[str, Any]:
    return {
        "id": paper.get("id") or f"community-{index}",
        "title": _normalize_text(paper.get("title")) or f"Community paper {index + 1}",
        "url": f"/paper/{paper.get('id')}" if paper.get("id") else None,
        "source": "community",
        "arxiv_id": paper.get("arxiv_id"),
        "paper_id": paper.get("id"),
        "snippet": _normalize_text(paper.get("abstract_translated") or paper.get("abstract_raw")),
    }


class CommunitySearchPapersSkill(AgentSkill):
    contract_slug = "community_search_papers"

    async def execute(self, arguments: Dict[str, Any], runtime_state) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        query = _normalize_text(arguments.get("query"))
        limit = int(arguments.get("limit") or 4)
        payload = await paper_service.list_community_papers(sort="latest", q=query, limit=limit)
        items = payload.get("items") if isinstance(payload, dict) else []
        papers = items if isinstance(items, list) else []
        citations: List[Dict[str, Any]] = [
            _citation_from_paper(item, index) for index, item in enumerate(papers)
        ]
        return {"query_executed": query, "results": citations, "count": len(citations)}
