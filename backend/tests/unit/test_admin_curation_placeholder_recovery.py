import asyncio

from fastapi import HTTPException

from backend.app.services import paper_service


def test_ensure_admin_curation_placeholder_paper_reuses_existing_row_when_recreate_insert_conflicts(monkeypatch):
    fetch_calls: list[str] = []

    async def _fetch_paper(paper_id: str):
        fetch_calls.append(paper_id)
        return {
            "id": paper_id,
            "title": "Recovered placeholder",
            "visibility": "private",
            "status": "curating",
            "community_status": "official",
            "trans_status": "processing",
        }

    async def _insert_paper(_payload):
        raise HTTPException(status_code=500, detail="Failed to create paper")

    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", _fetch_paper)
    monkeypatch.setattr(paper_service, "_insert_paper", _insert_paper)

    result = asyncio.run(
        paper_service._ensure_admin_curation_placeholder_paper(
            paper_id="paper-1",
            job={
                "paper_id": "paper-1",
                "created_by": "admin-1",
                "source_type": "arxiv",
                "arxiv_id": "2104.14294",
            },
            metadata={
                "title": "Recovered placeholder",
                "authors": ["Alice"],
                "categories": ["cs.CV"],
                "abstract_raw": "raw abstract",
            },
            resolved_arxiv_id="2104.14294",
            force_recreate=True,
        )
    )

    assert result["id"] == "paper-1"
    assert result["status"] == "curating"
    assert fetch_calls == ["paper-1"]
