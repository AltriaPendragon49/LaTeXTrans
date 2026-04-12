import asyncio
import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_preview_service, paper_service


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2503.01010",
        "title": "Previewable paper",
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


def test_get_paper_preview_reads_object_storage_asset(monkeypatch):
    html = (
        f'<article class="paper-preview" data-reader-version="{paper_preview_service.PREVIEW_READER_VERSION}">'
        "<section><h2>Introduction</h2><p>Preview content loaded from object storage.</p></section>"
        "</article>"
    )

    class _FakeBackend:
        def read_text(self, *, ref, encoding="utf-8"):
            assert ref.storage_backend == "object_storage"
            assert ref.object_key == "paperx/data/community_papers/paper-1/preview/preview.html"
            assert encoding == "utf-8"
            return html

    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper()),
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
                    "storage_backend": "object_storage",
                    "file_path": "paperx/data/community_papers/paper-1/preview/preview.html",
                    "file_name": "preview.html",
                    "mime_type": "text/html",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(paper_service, "_get_storage_backend", lambda: _FakeBackend())

    result = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert result["paper_id"] == "paper-1"
    assert result["asset"]["id"] == "asset-preview"
    assert "Preview content loaded from object storage." in result["html_content"]


def test_get_paper_preview_reuses_cached_object_storage_payload(monkeypatch):
    if hasattr(paper_service, "_preview_payload_cache"):
        paper_service._preview_payload_cache.clear()
    if hasattr(paper_service, "_preview_html_cache"):
        paper_service._preview_html_cache.clear()

    read_count = {"count": 0}
    html = (
        f'<article class="paper-preview" data-reader-version="{paper_preview_service.PREVIEW_READER_VERSION}">'
        "<section><h2>Introduction</h2><p>Preview content loaded from object storage.</p></section>"
        "</article>"
    )

    class _FakeBackend:
        def read_text(self, *, ref, encoding="utf-8"):
            read_count["count"] += 1
            assert ref.storage_backend == "object_storage"
            assert ref.object_key == "paperx/data/community_papers/paper-1/preview/preview-cached.html"
            assert encoding == "utf-8"
            return html

    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper()),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "preview_html": {
                    "id": "asset-preview-cached",
                    "task_id": "task-1",
                    "asset_type": "preview_html",
                    "storage_backend": "object_storage",
                    "file_path": "paperx/data/community_papers/paper-1/preview/preview-cached.html",
                    "file_name": "preview-cached.html",
                    "mime_type": "text/html",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(paper_service, "_get_storage_backend", lambda: _FakeBackend())

    first = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))
    second = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert first["html_content"] == second["html_content"]
    assert read_count["count"] == 1
