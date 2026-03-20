import asyncio
import json
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_service


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2503.01010",
        "title": "Previewable paper",
        "authors": [],
        "categories": [],
        "abstract_raw": "raw abstract",
        "abstract_translated": "中文摘要",
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


def test_list_papers_falls_back_to_operator_baseline_seed(monkeypatch, tmp_path):
    baseline_path = tmp_path / "community-baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "items": [
                    _paper(
                        id="paper-baseline",
                        title="Operator baseline paper",
                        community_selected_task_id=None,
                        community_selected_asset_id=None,
                    )
                ]
            }
        ),
        encoding="utf-8",
    )

    class _Query:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def neq(self, *_args, **_kwargs):
            return self

        def execute(self):
            return type("_Result", (), {"data": []})()

    class _Client:
        def table(self, _name):
            return _Query()

    monkeypatch.setattr(paper_service.settings, "community_baseline_seed_path", baseline_path)
    monkeypatch.setattr(paper_service, "get_supabase_admin_client", lambda: _Client())
    monkeypatch.setattr(paper_service, "run_db_blocking", lambda fn, **_kwargs: asyncio.sleep(0, result=fn()))
    monkeypatch.setattr(paper_service, "_fetch_latest_assets", lambda _paper_ids: asyncio.sleep(0, result={}))

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert result["total"] == 1
    assert result["items"][0]["id"] == "paper-baseline"
    assert result["source_mode"] == "baseline_seed"


def test_detail_includes_preview_bootstrap_when_reader_is_ready(monkeypatch, tmp_path):
    preview_path = tmp_path / "data" / "community_papers" / "paper-1" / "preview" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text("<article><h2>Readable</h2></article>", encoding="utf-8")

    monkeypatch.setattr(paper_service.settings, "base_dir", tmp_path)
    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", lambda _paper_id: asyncio.sleep(0, result=_paper()))
    monkeypatch.setattr(
        paper_service,
        "_hydrate_arxiv_metadata_if_needed",
        lambda paper: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_translated_abstract_if_needed",
        lambda paper, asset_map=None: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "preview_html": {
                    "id": "asset-preview",
                    "task_id": "task-1",
                    "asset_type": "preview_html",
                    "file_path": "data/community_papers/paper-1/preview/preview.html",
                    "file_name": "preview.html",
                    "mime_type": "text/html",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0, result={"paper-1": {"liked": False, "favorited": False}}
        ),
    )

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1"))

    assert result["reader_state"] == "ready"
    assert result["preview"]["asset"]["id"] == "asset-preview"
    assert "Readable" in result["preview"]["html_content"]


def test_detail_marks_preview_as_warming_and_schedules_recovery(monkeypatch):
    scheduled = {"count": 0}

    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(
                trans_status="completed",
                community_selected_task_id="task-translate",
                community_selected_asset_id=None,
            ),
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_arxiv_metadata_if_needed",
        lambda paper: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_hydrate_translated_abstract_if_needed",
        lambda paper, asset_map=None: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-translate",
                    "asset_type": "translated_pdf",
                    "file_path": "data/community_papers/paper-1/translated/paper.pdf",
                    "file_name": "paper.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
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

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1"))

    assert result["reader_state"] == "warming"
    assert result["preview"] is None
    assert scheduled["count"] == 1


def test_preview_route_keeps_unavailable_preview_as_not_found(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_ensure_public_paper",
        lambda _paper_id: asyncio.sleep(0, result=_paper(trans_status="processing")),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={}),
    )

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert excinfo.value.status_code == 404
