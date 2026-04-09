import asyncio
import os

from backend.app.db import DatabaseUnavailableError

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_service


def test_list_papers_orders_official_before_fallback(monkeypatch):
    papers = [
        {
            "id": "paper-fallback",
            "source": "arxiv",
            "arxiv_id": "2501.11111",
            "title": "Fallback first by time",
            "authors": [],
            "categories": [],
            "visibility": "public",
            "status": "published",
            "trans_status": "queued",
            "created_by": "user-1",
            "trans_latest_task_id": "task-fallback",
            "trans_latest_asset_pdf_id": None,
            "like_count": 1,
            "favorite_count": 0,
            "comment_count": 0,
            "view_count": 5,
            "download_count": 0,
            "created_at": "2026-03-18T03:00:00+00:00",
            "updated_at": "2026-03-18T03:00:00+00:00",
            "community_status": "user_fallback",
            "community_selected_task_id": "task-fallback",
            "community_selected_asset_id": None,
            "official_published_at": None,
        },
        {
            "id": "paper-official",
            "source": "arxiv",
            "arxiv_id": "2501.22222",
            "title": "Official later",
            "authors": [],
            "categories": [],
            "visibility": "public",
            "status": "published",
            "trans_status": "completed",
            "created_by": "admin-1",
            "trans_latest_task_id": "task-official",
            "trans_latest_asset_pdf_id": None,
            "like_count": 0,
            "favorite_count": 0,
            "comment_count": 0,
            "view_count": 1,
            "download_count": 0,
            "created_at": "2026-03-18T02:00:00+00:00",
            "updated_at": "2026-03-18T02:00:00+00:00",
            "community_status": "official",
            "community_selected_task_id": "task-official",
            "community_selected_asset_id": "asset-official",
            "official_published_at": "2026-03-18T04:00:00+00:00",
        },
    ]

    class _FakeCommunityRepository:
        def list_public_papers(self):
            return papers

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(
            0,
            result={
                "paper-official": {
                    "translated_pdf": {
                        "id": "asset-official",
                        "task_id": "task-official",
                        "asset_type": "translated_pdf",
                        "file_path": "/tmp/official.pdf",
                        "file_name": "official.pdf",
                        "mime_type": "application/pdf",
                        "created_at": "2026-03-18T04:00:00+00:00",
                    },
                }
            },
        ),
    )

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert result["items"][0]["id"] == "paper-official"
    assert result["items"][1]["id"] == "paper-fallback"


def test_list_papers_uses_baseline_seed_when_local_repository_is_unavailable(monkeypatch):
    papers = [
        {
            "id": "paper-official",
            "source": "arxiv",
            "arxiv_id": "2501.22222",
            "title": "Official later",
            "authors": [],
            "categories": [],
            "visibility": "public",
            "status": "published",
            "trans_status": "completed",
            "created_by": "admin-1",
            "trans_latest_task_id": "task-official",
            "trans_latest_asset_pdf_id": None,
            "like_count": 0,
            "favorite_count": 0,
            "comment_count": 0,
            "view_count": 1,
            "download_count": 0,
            "created_at": "2026-03-18T02:00:00+00:00",
            "updated_at": "2026-03-18T02:00:00+00:00",
            "community_status": "official",
            "community_selected_task_id": "task-official",
            "community_selected_asset_id": "asset-official",
            "official_published_at": "2026-03-18T04:00:00+00:00",
        },
    ]

    supabase_calls = {"count": 0}

    class _UnavailableCommunityRepository:
        def list_public_papers(self):
            raise DatabaseUnavailableError("local database unavailable")

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _UnavailableCommunityRepository())
    monkeypatch.setattr(paper_service, "_load_baseline_seed_rows", lambda: list(papers))
    monkeypatch.setattr(
        paper_service,
        "get_supabase_admin_client",
        lambda: supabase_calls.__setitem__("count", supabase_calls["count"] + 1),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(0, result={}),
    )

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert supabase_calls["count"] == 0
    assert result["source_mode"] == "baseline_seed"
    assert result["total"] == 1
    assert result["items"][0]["id"] == "paper-official"


def test_list_recovers_completed_state_when_source_asset_is_newer_than_preview(monkeypatch, tmp_path):
    preview_file = tmp_path / "preview.html"
    preview_file.write_text(
        "<article><p>这是中文翻译内容用于测试预览状态一致性。</p></article>",
        encoding="utf-8",
    )

    papers = [
        {
            "id": "paper-asset-priority",
            "source": "arxiv",
            "arxiv_id": "2501.44444",
            "title": "Asset priority paper",
            "authors": [],
            "categories": [],
            "visibility": "public",
            "status": "published",
            "trans_status": "completed",
            "created_by": "admin-1",
            "trans_latest_task_id": "task-translate",
            "trans_latest_asset_pdf_id": None,
            "like_count": 0,
            "favorite_count": 0,
            "comment_count": 0,
            "view_count": 0,
            "download_count": 0,
            "created_at": "2026-03-18T02:00:00+00:00",
            "updated_at": "2026-03-18T02:00:00+00:00",
            "community_status": "official",
            "community_selected_task_id": "task-translate",
            "community_selected_asset_id": "asset-preview",
            "official_published_at": "2026-03-18T04:00:00+00:00",
        }
    ]

    class _FakeCommunityRepository:
        def list_public_papers(self):
            return papers

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(
            0,
            result={
                "paper-asset-priority": {
                    "preview_html": {
                        "id": "asset-preview",
                        "task_id": "task-translate",
                        "asset_type": "preview_html",
                        "file_path": str(preview_file),
                        "file_name": "preview.html",
                        "mime_type": "text/html",
                        "created_at": "2026-03-18T03:00:00+00:00",
                    },
                    "source_archive": {
                        "id": "asset-source",
                        "task_id": "task-intake",
                        "asset_type": "source_archive",
                        "file_path": "/tmp/source.zip",
                        "file_name": "source.zip",
                        "mime_type": "application/zip",
                        "created_at": "2026-03-18T04:00:00+00:00",
                    },
                }
            },
        ),
    )

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert result["total"] == 1
    assert result["items"][0]["trans_status"] == "completed"
    assert result["items"][0]["latest_asset"]["asset_type"] == "preview_html"


def test_detail_returns_selected_version_and_viewer_state(monkeypatch):
    paper = {
        "id": "paper-detail",
        "source": "arxiv",
        "arxiv_id": "2501.33333",
        "title": "Detail paper",
        "authors": [],
        "categories": [],
        "visibility": "public",
        "status": "published",
        "trans_status": "completed",
        "created_by": "admin-1",
        "trans_latest_task_id": "task-detail",
        "trans_latest_asset_pdf_id": None,
        "like_count": 10,
        "favorite_count": 2,
        "comment_count": 1,
        "view_count": 99,
        "download_count": 4,
        "created_at": "2026-03-18T02:00:00+00:00",
        "updated_at": "2026-03-18T02:00:00+00:00",
        "community_status": "official",
        "community_selected_task_id": "task-detail",
        "community_selected_asset_id": "asset-detail",
        "official_published_at": "2026-03-18T04:00:00+00:00",
    }

    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", lambda _paper_id: asyncio.sleep(0, result=paper))
    monkeypatch.setattr(
        paper_service,
        "_fetch_latest_assets",
        lambda _paper_ids: asyncio.sleep(
            0,
            result={
                "paper-detail": {
                    "id": "asset-detail",
                    "task_id": "task-detail",
                    "asset_type": "translated_pdf",
                    "file_path": "/tmp/detail.pdf",
                    "file_name": "detail.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T04:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0,
            result={"paper-detail": {"liked": user_id == "user-1", "favorited": False}},
        ),
    )

    result = asyncio.run(
        paper_service.get_community_paper_detail(
            paper_id="paper-detail",
            viewer_user_id="user-1",
        )
    )

    assert result["paper"]["community_status"] == "official"
    assert result["paper"]["community_selected_task_id"] == "task-detail"
    assert result["paper"]["community_selected_asset_id"] == "asset-detail"
    assert result["paper"]["viewer_state"] == {"liked": True, "favorited": False}


def test_detail_hides_stale_preview_and_marks_reader_warming(monkeypatch):
    paper = {
        "id": "paper-detail",
        "source": "arxiv",
        "arxiv_id": "2501.33333",
        "title": "Detail paper",
        "authors": [],
        "categories": [],
        "visibility": "public",
        "status": "published",
        "trans_status": "completed",
        "created_by": "admin-1",
        "trans_latest_task_id": "task-detail",
        "trans_latest_asset_pdf_id": None,
        "like_count": 10,
        "favorite_count": 2,
        "comment_count": 1,
        "view_count": 99,
        "download_count": 4,
        "created_at": "2026-03-18T02:00:00+00:00",
        "updated_at": "2026-03-18T02:00:00+00:00",
        "community_status": "official",
        "community_selected_task_id": "task-detail",
        "community_selected_asset_id": "asset-preview",
        "official_published_at": "2026-03-18T04:00:00+00:00",
    }
    asset_map = {
        "preview_html": {
            "id": "asset-preview",
            "task_id": "task-detail",
            "asset_type": "preview_html",
            "file_path": "/tmp/preview.html",
            "file_name": "preview.html",
            "mime_type": "text/html",
            "created_at": "2026-03-18T04:00:00+00:00",
        }
    }

    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", lambda _paper_id: asyncio.sleep(0, result=paper))
    monkeypatch.setattr(paper_service, "_hydrate_arxiv_metadata_if_needed", lambda payload: asyncio.sleep(0, result=payload))
    monkeypatch.setattr(paper_service, "_fetch_asset_map_for_paper", lambda paper_id: asyncio.sleep(0, result=asset_map))
    monkeypatch.setattr(paper_service, "_hydrate_translated_abstract_if_needed", lambda payload, asset_map=None: asyncio.sleep(0, result=payload))
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(0, result={"paper-detail": {"liked": False, "favorited": False}}),
    )
    monkeypatch.setattr(paper_service, "_preview_asset_needs_refresh", lambda _path: True)
    monkeypatch.setattr(paper_service, "_schedule_preview_recovery", lambda **_kwargs: True)

    result = asyncio.run(
        paper_service.get_community_paper_detail(
            paper_id="paper-detail",
            viewer_user_id=None,
        )
    )

    assert result["preview"] is None
    assert result["reader_state"] == "warming"


def test_detail_recovers_completed_state_from_latest_translated_asset(monkeypatch):
    paper = {
        "id": "paper-detail",
        "source": "arxiv",
        "arxiv_id": "2501.33333",
        "title": "Detail paper",
        "authors": [],
        "categories": [],
        "visibility": "public",
        "status": "published",
        "trans_status": "not_started",
        "created_by": "admin-1",
        "trans_latest_task_id": "task-translate",
        "trans_latest_asset_pdf_id": None,
        "like_count": 10,
        "favorite_count": 2,
        "comment_count": 1,
        "view_count": 99,
        "download_count": 4,
        "created_at": "2026-03-18T02:00:00+00:00",
        "updated_at": "2026-03-18T02:00:00+00:00",
        "community_status": "official",
        "community_selected_task_id": "task-intake",
        "community_selected_asset_id": "asset-source",
        "official_published_at": "2026-03-18T04:00:00+00:00",
    }

    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", lambda _paper_id: asyncio.sleep(0, result=paper))
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "translated_pdf": {
                    "id": "asset-translate",
                    "task_id": "task-translate",
                    "asset_type": "translated_pdf",
                    "file_path": "/tmp/detail.pdf",
                    "file_name": "detail.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T04:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0,
            result={"paper-detail": {"liked": False, "favorited": False}},
        ),
    )

    result = asyncio.run(
        paper_service.get_community_paper_detail(
            paper_id="paper-detail",
            viewer_user_id="user-1",
        )
    )

    assert result["paper"]["trans_status"] == "completed"
    assert result["paper"]["community_selected_task_id"] == "task-translate"
    assert result["paper"]["community_selected_asset_id"] == "asset-translate"


def test_detail_hydrates_missing_arxiv_metadata(monkeypatch):
    paper = {
        "id": "paper-detail",
        "source": "arxiv",
        "arxiv_id": "2501.33333",
        "title": "arXiv:2501.33333",
        "authors": [],
        "categories": [],
        "abstract_raw": None,
        "abstract_translated": None,
        "visibility": "public",
        "status": "published",
        "trans_status": "not_started",
        "created_by": "admin-1",
        "trans_latest_task_id": None,
        "trans_latest_asset_pdf_id": None,
        "like_count": 10,
        "favorite_count": 2,
        "comment_count": 1,
        "view_count": 99,
        "download_count": 4,
        "created_at": "2026-03-18T02:00:00+00:00",
        "updated_at": "2026-03-18T02:00:00+00:00",
        "community_status": "official",
        "community_selected_task_id": None,
        "community_selected_asset_id": None,
        "official_published_at": "2026-03-18T04:00:00+00:00",
    }

    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", lambda _paper_id: asyncio.sleep(0, result=paper))
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
            result={"paper-detail": {"liked": False, "favorited": False}},
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_arxiv_metadata",
        lambda _arxiv_id: asyncio.sleep(
            0,
            result={
                "title": "Recovered arXiv title",
                "authors": ["Alice", "Bob"],
                "categories": ["cs.CV"],
                "abstract_raw": "Recovered abstract",
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(0, result={**paper, "id": paper_id, **payload}),
    )

    result = asyncio.run(
        paper_service.get_community_paper_detail(
            paper_id="paper-detail",
            viewer_user_id="user-1",
        )
    )

    assert result["paper"]["title"] == "Recovered arXiv title"
    assert result["paper"]["authors"] == ["Alice", "Bob"]
    assert result["paper"]["categories"] == ["cs.CV"]
    assert result["paper"]["abstract_raw"] == "Recovered abstract"


def test_reader_payload_exposes_anchor_metadata_for_source_and_translated_html():
    payload = paper_service._build_reader_experience_payload(
        paper={
            "id": "paper-anchor",
            "source": "arxiv",
            "arxiv_id": "2501.00001",
            "trans_status": "completed",
        },
        paper_id="paper-anchor",
        preview_payload={
            "paper_id": "paper-anchor",
            "task_id": "task-anchor",
            "asset": {
                "id": "asset-anchor",
                "task_id": "task-anchor",
                "asset_type": "preview_html",
                "file_name": "preview.html",
                "mime_type": "text/html",
                "created_at": "2026-03-18T04:00:00+00:00",
            },
            "html_content": (
                "<article>"
                "<section id=\"section-intro\" data-section-id=\"section-intro\">"
                "<h2>Introduction</h2>"
                "<div id=\"section-intro-block-0\" data-block-id=\"section-intro-block-0\">Body</div>"
                "</section>"
                "</article>"
            ),
            "generated_at": "2026-03-18T04:00:00+00:00",
        },
        translated_asset=None,
        source_html_content="<article><h2 id=\"source-overview\">Overview</h2></article>",
    )

    source = payload["reader"]["source"]
    translated = payload["reader"]["translated"]
    assert source is not None
    assert translated is not None

    source_anchors = source.get("anchors") or []
    translated_anchors = translated.get("anchors") or []

    assert any(item.get("anchor_id") == "source-overview" for item in source_anchors)
    assert any(item.get("anchor_id") == "section-intro" for item in translated_anchors)
    assert any(item.get("anchor_id") == "section-intro-block-0" for item in translated_anchors)
