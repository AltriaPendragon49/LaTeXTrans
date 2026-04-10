import asyncio

from backend.app.services import paper_service


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2503.01010",
        "title": "Insight-ready paper",
        "authors": [],
        "categories": [],
        "abstract_raw": "This paper studies a translation pipeline.",
        "abstract_translated": "本文研究一个翻译流水线。",
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


def test_detail_returns_not_ready_structured_insight_payload_for_legacy_visible_paper(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper()),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0,
            result={"paper-1": {"liked": False, "favorited": False}},
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_sanitized_arxiv_html",
        lambda _arxiv_id: asyncio.sleep(0, result=None),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_structured_insight_sections",
        lambda paper_id: asyncio.sleep(0, result=[]),
        raising=False,
    )

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1", fast_path=True))

    assert result["structured_insights"]["state"] == "not_ready"
    assert [section["section_key"] for section in result["structured_insights"]["sections"]] == [
        "problem",
        "method",
        "key_idea",
        "experiment",
        "result",
        "limitation",
    ]
