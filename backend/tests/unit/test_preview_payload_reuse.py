import asyncio
import os
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_preview_service, paper_service


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "arxiv",
        "arxiv_id": "2503.01010",
        "title": "Preview cache paper",
        "authors": [],
        "categories": [],
        "abstract_raw": "",
        "abstract_translated": None,
        "community_status": "official",
        "trans_status": "completed",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": "2026-03-18T02:00:00+00:00",
        "community_selected_task_id": "task-1",
        "community_selected_asset_id": "asset-preview",
        "visibility": "public",
        "status": "published",
    }
    base.update(overrides)
    return base


def test_preview_route_reuses_cached_payload_for_unchanged_asset(monkeypatch, tmp_path):
    if hasattr(paper_service, "_preview_payload_cache"):
        paper_service._preview_payload_cache.clear()

    preview_path = tmp_path / "preview.html"
    preview_path.write_text(
        (
            f'<article data-reader-version="{paper_preview_service.PREVIEW_READER_VERSION}">'
            "<h2>Ready</h2><p>Cached html</p></article>"
        ),
        encoding="utf-8",
    )

    read_count = {"count": 0}
    original_read_text = Path.read_text

    def counted_read_text(self: Path, *args, **kwargs):
        if self == preview_path:
            read_count["count"] += 1
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counted_read_text)
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
                    "file_path": str(preview_path),
                    "file_name": "preview.html",
                    "mime_type": "text/html",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )

    first = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))
    second = asyncio.run(paper_service.get_paper_preview(paper_id="paper-1"))

    assert first["html_content"] == second["html_content"]
    assert read_count["count"] == 1
