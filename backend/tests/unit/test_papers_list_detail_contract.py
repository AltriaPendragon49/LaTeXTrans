import asyncio
from datetime import datetime
import os

from backend.app.db import DatabaseUnavailableError

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_service


class _FakeSharedFeedStore:
    def __init__(self):
        self.available = True
        self.cached_payloads = {}
        self.indexes = {"latest": {}, "views": {}, "likes": {}}
        self.registry_cleared = 0
        self.rebuild_lock_acquired = True
        self.replace_calls = []

    def response_key(self, *, sort: str, limit: int | None, offset: int) -> str:
        return f"{sort}:{limit}:{offset}"

    def get_cached_payload(self, *, sort: str, limit: int | None, offset: int):
        payload = self.cached_payloads.get(self.response_key(sort=sort, limit=limit, offset=offset))
        return dict(payload) if payload else None

    def set_cached_payload(self, *, sort: str, limit: int | None, offset: int, payload):
        self.cached_payloads[self.response_key(sort=sort, limit=limit, offset=offset)] = dict(payload)

    def clear_cached_payloads(self):
        self.registry_cleared += 1
        self.cached_payloads.clear()

    def read_ranked_ids(self, *, sort: str, offset: int, limit: int | None):
        values = sorted(self.indexes.get(sort, {}).items(), key=lambda item: item[1], reverse=True)
        normalized_offset = max(0, int(offset or 0))
        normalized_limit = max(0, int(limit or 0))
        return [paper_id for paper_id, _score in values[normalized_offset : normalized_offset + normalized_limit]]

    def count_ranked_ids(self, *, sort: str) -> int:
        return len(self.indexes.get(sort, {}))

    def replace_index(self, *, sort: str, mapping):
        self.replace_calls.append((sort, dict(mapping)))
        self.indexes[sort] = dict(mapping)

    def upsert_ranked_paper(self, *, sort: str, paper_id: str, score: float):
        self.indexes.setdefault(sort, {})[paper_id] = score

    def increment_ranked_paper(self, *, sort: str, paper_id: str, delta: float):
        self.indexes.setdefault(sort, {})[paper_id] = self.indexes.setdefault(sort, {}).get(paper_id, 0.0) + delta

    def remove_ranked_paper(self, *, paper_id: str):
        for sort in ("latest", "views", "likes"):
            self.indexes.setdefault(sort, {}).pop(paper_id, None)

    def acquire_rebuild_lock(self) -> bool:
        return self.rebuild_lock_acquired


def test_rebuild_public_feed_indexes_replaces_indexes_and_clears_response_cache(monkeypatch):
    store = _FakeSharedFeedStore()
    store.cached_payloads["likes:12:0"] = {"items": [{"id": "stale"}]}

    papers = [
        {
            "id": "paper-a",
            "visibility": "public",
            "status": "published",
            "community_status": "official",
            "created_at": "2026-03-18T02:00:00+00:00",
            "official_published_at": "2026-03-20T04:00:00+00:00",
            "arxiv_published_at": "2026-03-21T04:00:00+00:00",
            "like_count": 3,
            "view_count": 10,
        },
        {
            "id": "paper-b",
            "visibility": "public",
            "status": "published",
            "community_status": "user_fallback",
            "created_at": "2026-03-17T02:00:00+00:00",
            "official_published_at": "2026-03-19T04:00:00+00:00",
            "arxiv_published_at": "2026-03-19T04:00:00+00:00",
            "like_count": 1,
            "view_count": 5,
        },
    ]

    class _FakeCommunityRepository:
        def list_public_papers(self):
            return papers

    monkeypatch.setattr(paper_service, "_public_feed_store", store)
    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())

    rebuilt = asyncio.run(paper_service._rebuild_public_feed_indexes_from_db())

    assert rebuilt is True
    assert [sort for sort, _mapping in store.replace_calls] == ["latest", "views", "likes"]
    assert store.registry_cleared == 1
    assert store.cached_payloads == {}
    assert store.indexes["likes"]["paper-a"] > store.indexes["likes"]["paper-b"]


def test_rebuild_public_feed_indexes_if_enabled_skips_when_interval_disabled(monkeypatch):
    monkeypatch.setattr(paper_service.settings, "community_feed_rebuild_interval_seconds", 0.0, raising=False)
    rebuilt = asyncio.run(paper_service.rebuild_public_feed_indexes_if_enabled())
    assert rebuilt is False


def test_list_papers_orders_by_publication_time_not_official_priority(monkeypatch):
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
            "title": "Official older",
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
            "official_published_at": "2026-03-18T01:00:00+00:00",
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

    assert result["items"][0]["id"] == "paper-fallback"
    assert result["items"][1]["id"] == "paper-official"


def test_list_papers_latest_sort_prefers_original_arxiv_publish_time(monkeypatch):
    papers = [
        {
            "id": "paper-later-official",
            "source": "arxiv",
            "arxiv_id": "2501.11111",
            "title": "Later official publish",
            "authors": [],
            "categories": [],
            "visibility": "public",
            "status": "published",
            "trans_status": "completed",
            "created_by": "admin-1",
            "trans_latest_task_id": "task-later-official",
            "trans_latest_asset_pdf_id": None,
            "like_count": 0,
            "favorite_count": 0,
            "comment_count": 0,
            "view_count": 0,
            "download_count": 0,
            "created_at": "2026-03-18T02:00:00+00:00",
            "updated_at": "2026-03-18T02:00:00+00:00",
            "community_status": "official",
            "community_selected_task_id": "task-later-official",
            "community_selected_asset_id": None,
            "official_published_at": "2026-03-20T04:00:00+00:00",
            "arxiv_published_at": "2026-03-10T04:00:00+00:00",
        },
        {
            "id": "paper-newer-arxiv",
            "source": "arxiv",
            "arxiv_id": "2501.22222",
            "title": "Newer arxiv publish",
            "authors": [],
            "categories": [],
            "visibility": "public",
            "status": "published",
            "trans_status": "completed",
            "created_by": "admin-1",
            "trans_latest_task_id": "task-newer-arxiv",
            "trans_latest_asset_pdf_id": None,
            "like_count": 0,
            "favorite_count": 0,
            "comment_count": 0,
            "view_count": 0,
            "download_count": 0,
            "created_at": "2026-03-18T02:00:00+00:00",
            "updated_at": "2026-03-18T02:00:00+00:00",
            "community_status": "official",
            "community_selected_task_id": "task-newer-arxiv",
            "community_selected_asset_id": None,
            "official_published_at": "2026-03-19T04:00:00+00:00",
            "arxiv_published_at": "2026-03-15T04:00:00+00:00",
        },
    ]

    class _FakeCommunityRepository:
        def list_public_papers(self):
            return papers

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(0, result={}),
    )

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert [item["id"] for item in result["items"]] == ["paper-newer-arxiv", "paper-later-official"]


def test_list_papers_returns_empty_when_local_repository_is_unavailable(monkeypatch):
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

    legacy_client_calls = {"count": 0}

    class _UnavailableCommunityRepository:
        def list_public_papers(self):
            raise DatabaseUnavailableError("local database unavailable")

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _UnavailableCommunityRepository())
    monkeypatch.setattr(paper_service, "_load_baseline_seed_rows", lambda: list(papers))
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(0, result={}),
    )

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert legacy_client_calls["count"] == 0
    assert result["source_mode"] == "database"
    assert result["total"] == 0
    assert result["items"] == []


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


def test_list_papers_serializes_datetime_fields_from_local_repository(monkeypatch):
    papers = [
        {
            "id": "paper-datetime",
            "source": "arxiv",
            "arxiv_id": "2501.55555",
            "title": "Datetime paper",
            "authors": [],
            "categories": [],
            "visibility": "public",
            "status": "published",
            "trans_status": "completed",
            "created_by": "admin-1",
            "trans_latest_task_id": "task-datetime",
            "trans_latest_asset_pdf_id": None,
            "like_count": 0,
            "favorite_count": 0,
            "comment_count": 0,
            "view_count": 0,
            "download_count": 0,
            "created_at": datetime(2026, 3, 18, 2, 0, 0),
            "updated_at": datetime(2026, 3, 18, 2, 0, 0),
            "community_status": "official",
            "community_selected_task_id": "task-datetime",
            "community_selected_asset_id": "asset-datetime",
            "official_published_at": datetime(2026, 3, 18, 4, 0, 0),
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
                "paper-datetime": {
                    "translated_pdf": {
                        "id": "asset-datetime",
                        "task_id": "task-datetime",
                        "asset_type": "translated_pdf",
                        "file_path": "/tmp/datetime.pdf",
                        "file_name": "datetime.pdf",
                        "mime_type": "application/pdf",
                        "created_at": datetime(2026, 3, 18, 4, 0, 0),
                    },
                }
            },
        ),
    )

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert result["items"][0]["created_at"] == "2026-03-18 02:00:00"
    assert result["items"][0]["official_published_at"] == "2026-03-18 04:00:00"
    assert result["items"][0]["latest_asset"]["created_at"] == "2026-03-18 04:00:00"


def test_list_papers_trims_heavy_fields_for_feed_payload(monkeypatch):
    long_abstract = "A" * 900
    translated_abstract = "中" * 500
    papers = [
        {
            "id": "paper-compact",
            "source": "upload",
            "arxiv_id": None,
            "title": "Compact payload paper",
            "authors": [],
            "categories": ["cs.CL"],
            "abstract_raw": long_abstract,
            "abstract_translated": translated_abstract,
            "visibility": "public",
            "status": "published",
            "trans_status": "completed",
            "created_by": "admin-1",
            "trans_latest_task_id": "task-compact",
            "trans_latest_asset_pdf_id": "asset-translated",
            "like_count": 0,
            "favorite_count": 0,
            "comment_count": 0,
            "view_count": 0,
            "download_count": 0,
            "created_at": "2026-03-18T02:00:00+00:00",
            "updated_at": "2026-03-18T02:00:00+00:00",
            "community_status": "official",
            "community_selected_task_id": "task-compact",
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
                "paper-compact": {
                    "preview_html": {
                        "id": "asset-preview",
                        "task_id": "task-compact",
                        "asset_type": "preview_html",
                        "file_path": "/tmp/preview.html",
                        "file_name": "preview.html",
                        "mime_type": "text/html",
                        "created_at": "2026-03-18T04:00:00+00:00",
                    },
                    "source_archive": {
                        "id": "asset-source",
                        "task_id": "task-source",
                        "asset_type": "source_archive",
                        "file_path": "/tmp/source.zip",
                        "file_name": "source.zip",
                        "mime_type": "application/zip",
                        "created_at": "2026-03-18T04:00:00+00:00",
                    },
                    "translated_pdf": {
                        "id": "asset-translated",
                        "task_id": "task-compact",
                        "asset_type": "translated_pdf",
                        "file_path": "/tmp/translated.pdf",
                        "file_name": "translated.pdf",
                        "mime_type": "application/pdf",
                        "created_at": "2026-03-18T04:00:00+00:00",
                    },
                }
            },
        ),
    )

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    item = result["items"][0]
    assert len(item["abstract_raw"]) < len(long_abstract)
    assert item["abstract_raw"].endswith("...")
    assert len(item["abstract_translated"]) < len(translated_abstract)
    assert item["abstract_translated"].endswith("...")
    assert set(item["assets"].keys()) == {"source_archive", "translated_pdf"}


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


def test_detail_returns_preview_locator_instead_of_inline_html(monkeypatch, tmp_path):
    preview_file = tmp_path / "preview.html"
    preview_file.write_text(
        "<article><section id='intro' data-section-id='intro'><h2>Intro</h2></section></article>",
        encoding="utf-8",
    )
    paper = {
        "id": "paper-preview",
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
            "file_path": str(preview_file),
            "file_name": "preview.html",
            "mime_type": "text/html",
            "created_at": "2026-03-18T04:00:00+00:00",
        }
    }

    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", lambda _paper_id: asyncio.sleep(0, result=paper))
    monkeypatch.setattr(paper_service, "_hydrate_arxiv_metadata_if_needed", lambda payload: asyncio.sleep(0, result=payload))
    monkeypatch.setattr(paper_service, "_hydrate_translated_abstract_if_needed", lambda payload, asset_map=None: asyncio.sleep(0, result=payload))
    monkeypatch.setattr(paper_service, "_fetch_asset_map_for_paper", lambda **_kwargs: asyncio.sleep(0, result=asset_map))
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(0, result={"paper-preview": {"liked": False, "favorited": False}}),
    )

    result = asyncio.run(
        paper_service.get_community_paper_detail(
            paper_id="paper-preview",
            viewer_user_id=None,
        )
    )

    assert result["preview"]["fetch_url"] == "/api/papers/paper-preview/preview"
    assert result["reader"]["translated"]["url"] == "/api/papers/paper-preview/preview"
    assert result["reader"]["translated"]["html_content"] is None


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


def test_list_papers_hydrates_curated_placeholder_metadata(monkeypatch):
    paper = {
        "id": "paper-curated",
        "source": "arxiv",
        "arxiv_id": "2501.44444",
        "title": "Curated paper",
        "authors": [],
        "categories": [],
        "abstract_raw": None,
        "abstract_translated": "translated abstract",
        "visibility": "public",
        "status": "published",
        "trans_status": "completed",
        "created_by": "admin-1",
        "trans_latest_task_id": "task-curated",
        "trans_latest_asset_pdf_id": None,
        "like_count": 0,
        "favorite_count": 0,
        "comment_count": 0,
        "view_count": 0,
        "download_count": 0,
        "created_at": "2026-03-18T02:00:00+00:00",
        "updated_at": "2026-03-18T02:00:00+00:00",
        "community_status": "official",
        "community_selected_task_id": "task-curated",
        "community_selected_asset_id": None,
        "official_published_at": "2026-03-18T04:00:00+00:00",
    }

    class _FakeCommunityRepository:
        def count_public_papers(self, *, query=None):
            assert query is None
            return 1

        def list_public_papers_page(self, *, sort, query, limit, offset):
            assert (sort, query, limit, offset) == ("latest", None, 12, 0)
            return [dict(paper)]

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_arxiv_metadata",
        lambda _arxiv_id: asyncio.sleep(
            0,
            result={
                "title": "Recovered curated title",
                "authors": ["Alice", "Bob"],
                "categories": ["cs.LG"],
                "abstract_raw": "Recovered abstract",
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(0, result={**paper, "id": paper_id, **payload}),
    )
    monkeypatch.setattr(paper_service, "_public_feed_store", _FakeSharedFeedStore(), raising=False)

    result = asyncio.run(
        paper_service.list_community_papers(sort="latest", q=None, limit=12, offset=0)
    )

    assert result["items"][0]["title"] == "Recovered curated title"
    assert result["items"][0]["authors"] == ["Alice", "Bob"]
    assert result["items"][0]["categories"] == ["cs.LG"]
    assert result["items"][0]["abstract_raw"] == "Recovered abstract"


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


def test_list_papers_paginates_and_reports_has_more(monkeypatch):
    list_calls = []
    count_calls = []

    class _FakeCommunityRepository:
        def count_public_papers(self, *, query=None):
            count_calls.append(query)
            return 3

        def list_public_papers_page(self, *, sort, query, limit, offset):
            list_calls.append((sort, query, limit, offset))
            return [
                {
                    "id": "paper-2",
                    "source": "arxiv",
                    "arxiv_id": "2501.22222",
                    "title": "Second page candidate",
                    "authors": [],
                    "categories": [],
                    "visibility": "public",
                    "status": "published",
                    "trans_status": "completed",
                    "created_by": "admin-1",
                    "trans_latest_task_id": "task-2",
                    "trans_latest_asset_pdf_id": None,
                    "like_count": 0,
                    "favorite_count": 0,
                    "comment_count": 0,
                    "view_count": 0,
                    "download_count": 0,
                    "created_at": "2026-03-18T02:00:00+00:00",
                    "updated_at": "2026-03-18T02:00:00+00:00",
                    "community_status": "official",
                    "community_selected_task_id": "task-2",
                    "community_selected_asset_id": None,
                    "official_published_at": "2026-03-18T04:00:00+00:00",
                },
                {
                    "id": "paper-3",
                    "source": "arxiv",
                    "arxiv_id": "2501.33333",
                    "title": "Third page candidate",
                    "authors": [],
                    "categories": [],
                    "visibility": "public",
                    "status": "published",
                    "trans_status": "completed",
                    "created_by": "admin-1",
                    "trans_latest_task_id": "task-3",
                    "trans_latest_asset_pdf_id": None,
                    "like_count": 0,
                    "favorite_count": 0,
                    "comment_count": 0,
                    "view_count": 0,
                    "download_count": 0,
                    "created_at": "2026-03-18T01:00:00+00:00",
                    "updated_at": "2026-03-18T01:00:00+00:00",
                    "community_status": "official",
                    "community_selected_task_id": "task-3",
                    "community_selected_asset_id": None,
                    "official_published_at": "2026-03-18T03:00:00+00:00",
                },
            ]

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(paper_service, "_public_feed_store", _FakeSharedFeedStore(), raising=False)

    result = asyncio.run(
        paper_service.list_community_papers(sort="latest", q=None, limit=2, offset=1)
    )

    assert result["total"] == 3
    assert len(result["items"]) == 2
    assert result["offset"] == 1
    assert result["limit"] == 2
    assert result["has_more"] is False
    assert result["next_offset"] is None
    assert count_calls == [None]
    assert list_calls == [("latest", None, 2, 1)]


def test_list_papers_reuses_cached_first_page_for_latest_sort(monkeypatch):
    calls = {"count": 0, "list": 0}

    class _FakeCommunityRepository:
        def count_public_papers(self, *, query=None):
            calls["count"] += 1
            return 1

        def list_public_papers_page(self, *, sort, query, limit, offset):
            calls["list"] += 1
            return [
                {
                    "id": "paper-cached",
                    "source": "arxiv",
                    "arxiv_id": "2501.99999",
                    "title": "Cached latest paper",
                    "authors": [],
                    "categories": [],
                    "visibility": "public",
                    "status": "published",
                    "trans_status": "completed",
                    "created_by": "admin-1",
                    "trans_latest_task_id": "task-cached",
                    "trans_latest_asset_pdf_id": None,
                    "like_count": 0,
                    "favorite_count": 0,
                    "comment_count": 0,
                    "view_count": 0,
                    "download_count": 0,
                    "created_at": "2026-03-18T02:00:00+00:00",
                    "updated_at": "2026-03-18T02:00:00+00:00",
                    "community_status": "official",
                    "community_selected_task_id": "task-cached",
                    "community_selected_asset_id": None,
                    "official_published_at": "2026-03-18T04:00:00+00:00",
                }
            ]

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(paper_service, "_public_feed_store", _FakeSharedFeedStore(), raising=False)

    first = asyncio.run(
        paper_service.list_community_papers(sort="latest", q=None, limit=12, offset=0)
    )
    second = asyncio.run(
        paper_service.list_community_papers(sort="latest", q=None, limit=12, offset=0)
    )

    assert first["items"][0]["id"] == "paper-cached"
    assert second["items"][0]["id"] == "paper-cached"
    assert calls == {"count": 1, "list": 1}


def test_list_papers_uses_shared_ranked_ids_before_db_query(monkeypatch):
    store = _FakeSharedFeedStore()
    store.indexes["likes"] = {"paper-b": 20.0, "paper-a": 10.0}
    papers_by_id = {
        "paper-a": {
            "id": "paper-a",
            "source": "arxiv",
            "arxiv_id": "2501.10000",
            "title": "Paper A",
            "authors": [],
            "categories": [],
            "visibility": "public",
            "status": "published",
            "trans_status": "completed",
            "created_by": "admin-1",
            "trans_latest_task_id": "task-a",
            "trans_latest_asset_pdf_id": None,
            "like_count": 1,
            "favorite_count": 0,
            "comment_count": 0,
            "view_count": 0,
            "download_count": 0,
            "created_at": "2026-03-18T02:00:00+00:00",
            "updated_at": "2026-03-18T02:00:00+00:00",
            "community_status": "official",
            "community_selected_task_id": "task-a",
            "community_selected_asset_id": None,
            "official_published_at": "2026-03-18T01:00:00+00:00",
        },
        "paper-b": {
            "id": "paper-b",
            "source": "arxiv",
            "arxiv_id": "2501.20000",
            "title": "Paper B",
            "authors": [],
            "categories": [],
            "visibility": "public",
            "status": "published",
            "trans_status": "completed",
            "created_by": "admin-1",
            "trans_latest_task_id": "task-b",
            "trans_latest_asset_pdf_id": None,
            "like_count": 2,
            "favorite_count": 0,
            "comment_count": 0,
            "view_count": 0,
            "download_count": 0,
            "created_at": "2026-03-18T03:00:00+00:00",
            "updated_at": "2026-03-18T03:00:00+00:00",
            "community_status": "official",
            "community_selected_task_id": "task-b",
            "community_selected_asset_id": None,
            "official_published_at": "2026-03-18T05:00:00+00:00",
        },
    }

    class _FakeCommunityRepository:
        def get_paper_by_id(self, paper_id):
            return papers_by_id.get(paper_id)

        def count_public_papers(self, *, query=None):
            raise AssertionError("count_public_papers should not run when shared indexes are warm")

        def list_public_papers_page(self, *, sort, query, limit, offset):
            raise AssertionError("list_public_papers_page should not run when shared indexes are warm")

    monkeypatch.setattr(paper_service, "_public_feed_store", store, raising=False)
    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(paper_service, "_fetch_asset_maps_for_papers", lambda _paper_ids: asyncio.sleep(0, result={}))

    result = asyncio.run(paper_service.list_community_papers(sort="likes", q=None, limit=2, offset=0))

    assert [item["id"] for item in result["items"]] == ["paper-b", "paper-a"]
    assert result["source_mode"] == "redis"


def test_like_refresh_updates_shared_rankings_and_clears_cached_payloads(monkeypatch):
    store = _FakeSharedFeedStore()
    store.cached_payloads["likes:12:0"] = {"items": [{"id": "paper-1"}]}
    paper = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2501.99998",
        "title": "Sorted paper",
        "authors": [],
        "categories": [],
        "visibility": "public",
        "status": "published",
        "trans_status": "completed",
        "created_by": "admin-1",
        "trans_latest_task_id": "task-sort",
        "trans_latest_asset_pdf_id": None,
        "like_count": 4,
        "favorite_count": 1,
        "comment_count": 0,
        "view_count": 9,
        "download_count": 0,
        "created_at": "2026-03-18T02:00:00+00:00",
        "updated_at": "2026-03-18T02:00:00+00:00",
        "community_status": "official",
        "community_selected_task_id": "task-sort",
        "community_selected_asset_id": None,
        "official_published_at": "2026-03-18T04:00:00+00:00",
    }

    class _FakeCommunityRepository:
        def like_paper(self, *, paper_id, user_id):
            assert (paper_id, user_id) == ("paper-1", "user-1")
            return 4

    monkeypatch.setattr(paper_service, "_public_feed_store", store, raising=False)
    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(paper_service, "_ensure_public_paper", lambda _paper_id: asyncio.sleep(0, result=None))
    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", lambda _paper_id: asyncio.sleep(0, result=paper))

    result = asyncio.run(paper_service.like_paper(paper_id="paper-1", user_id="user-1"))

    assert result == {"paper_id": "paper-1", "liked": True, "like_count": 4}
    assert store.indexes["likes"]["paper-1"] > 0
    assert store.registry_cleared == 1


def test_list_papers_supports_views_and_likes_sort(monkeypatch):
    list_calls = []

    class _FakeCommunityRepository:
        def count_public_papers(self, *, query=None):
            return 1

        def list_public_papers_page(self, *, sort, query, limit, offset):
            list_calls.append((sort, query, limit, offset))
            return [
                {
                    "id": "paper-sort",
                    "source": "arxiv",
                    "arxiv_id": "2501.99998",
                    "title": "Sorted paper",
                    "authors": [],
                    "categories": [],
                    "visibility": "public",
                    "status": "published",
                    "trans_status": "completed",
                    "created_by": "admin-1",
                    "trans_latest_task_id": "task-sort",
                    "trans_latest_asset_pdf_id": None,
                    "like_count": 3,
                    "favorite_count": 1,
                    "comment_count": 0,
                    "view_count": 9,
                    "download_count": 0,
                    "created_at": "2026-03-18T02:00:00+00:00",
                    "updated_at": "2026-03-18T02:00:00+00:00",
                    "community_status": "official",
                    "community_selected_task_id": "task-sort",
                    "community_selected_asset_id": None,
                    "official_published_at": "2026-03-18T04:00:00+00:00",
                }
            ]

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(paper_service, "_public_feed_store", _FakeSharedFeedStore(), raising=False)

    asyncio.run(paper_service.list_community_papers(sort="views", q=None, limit=12, offset=0))
    asyncio.run(paper_service.list_community_papers(sort="likes", q=None, limit=12, offset=0))

    assert list_calls == [("views", None, 12, 0), ("likes", None, 12, 0)]


def test_detail_reports_favorite_folder_count_in_viewer_state(monkeypatch):
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
    monkeypatch.setattr(paper_service, "_fetch_asset_map_for_paper", lambda **_kwargs: asyncio.sleep(0, result={}))
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda _paper_ids, user_id=None: asyncio.sleep(
            0,
            result={"paper-detail": {"liked": False, "favorited": True, "favorite_folder_count": 2}},
        ),
    )

    result = asyncio.run(
        paper_service.get_community_paper_detail(
            paper_id="paper-detail",
            viewer_user_id="user-1",
        )
    )

    assert result["paper"]["viewer_state"] == {
        "liked": False,
        "favorited": True,
        "favorite_folder_count": 2,
    }



