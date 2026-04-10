import asyncio

import pytest
from fastapi import HTTPException

from backend.app.services import paper_service


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2503.01010",
        "title": "Canonical paper",
        "authors": [],
        "categories": [],
        "abstract_raw": "raw abstract",
        "abstract_translated": "translated abstract",
        "community_status": "official",
        "trans_status": "completed",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": "2026-03-18T02:00:00+00:00",
        "community_selected_task_id": "task-1",
        "community_selected_asset_id": "asset-preview",
        "visibility": "public",
        "status": "published",
        "like_count": 0,
        "favorite_count": 0,
        "comment_count": 0,
        "view_count": 0,
        "download_count": 0,
    }
    base.update(overrides)
    return base


def test_list_community_papers_excludes_fallback_incomplete_and_deleting_rows(monkeypatch):
    papers = [
        _paper(id="paper-official-ready"),
        _paper(id="paper-fallback", community_status="user_fallback"),
        _paper(id="paper-processing", trans_status="processing"),
        _paper(id="paper-private", visibility="private"),
        _paper(id="paper-curating", status="curating"),
        _paper(id="paper-deleting", status="deleting"),
    ]

    class _Repository:
        def list_public_papers(self):
            return papers

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _Repository())
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(0, result={}),
    )

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert [item["id"] for item in result["items"]] == ["paper-official-ready"]


def test_community_detail_rejects_non_official_or_non_published_rows(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(
                id="paper-fallback",
                community_status="user_fallback",
                status="published",
                visibility="public",
            ),
        ),
    )

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-fallback", fast_path=True))

    assert excinfo.value.status_code == 404
