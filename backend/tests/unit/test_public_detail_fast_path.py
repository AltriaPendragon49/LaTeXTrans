import asyncio
import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_service


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2503.01010",
        "title": "arXiv:2503.01010",
        "authors": [],
        "categories": [],
        "abstract_raw": "",
        "abstract_translated": None,
        "community_status": "official",
        "trans_status": "completed",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": "2026-03-18T02:00:00+00:00",
        "community_selected_task_id": "task-1",
        "community_selected_asset_id": None,
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


def test_public_detail_returns_fast_path_and_schedules_metadata_repairs(monkeypatch):
    scheduled = {"count": 0}

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
            0, result={"paper-1": {"liked": False, "favorited": False}}
        ),
    )
    monkeypatch.setattr(
        paper_service.asyncio,
        "create_task",
        lambda coro: (scheduled.__setitem__("count", scheduled["count"] + 1), coro.close())[0],
    )

    result = asyncio.run(
        paper_service.get_community_paper_detail(
            paper_id="paper-1",
            fast_path=True,
        )
    )

    assert result["paper"]["title"] == "arXiv:2503.01010"
    assert result["reader_state"] == "warming"
    assert scheduled["count"] >= 1


def test_public_detail_fast_path_skips_sanitized_source_html_fetch(monkeypatch):
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
            0, result={"paper-1": {"liked": False, "favorited": False}}
        ),
    )
    monkeypatch.setattr(
        paper_service.asyncio,
        "create_task",
        lambda coro: coro.close(),
    )

    async def _unexpected_source_fetch(_arxiv_id):
        raise AssertionError("fast path should not fetch sanitized source HTML")

    monkeypatch.setattr(
        paper_service,
        "_fetch_sanitized_arxiv_html",
        _unexpected_source_fetch,
    )

    result = asyncio.run(
        paper_service.get_community_paper_detail(
            paper_id="paper-1",
            fast_path=True,
        )
    )

    assert result["reader"]["source"]["kind"] == "source_pdf"
