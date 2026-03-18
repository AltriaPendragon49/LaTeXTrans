import asyncio
import json
import os
from pathlib import Path

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
        "abstract_raw": None,
        "abstract_translated": None,
        "community_status": "user_fallback",
        "trans_status": "not_started",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": None,
        "community_selected_task_id": None,
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


def test_publish_task_to_community_library_copies_assets_with_relative_paths(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    data_dir = base_dir / "data"
    uploads_dir = data_dir / "uploads"
    outputs_dir = data_dir / "outputs"
    community_dir = data_dir / "community_papers"
    source_dir = uploads_dir / "arxiv_2503.01010"
    output_dir = outputs_dir / "task-1"
    source_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "main.tex").write_text("\\section{Intro}", encoding="utf-8")
    (output_dir / "paper_translated.pdf").write_text("pdf-bytes", encoding="utf-8")
    (output_dir / "sections_map.json").write_text(
        json.dumps(
            [
                {
                    "section": "1",
                    "content": "\\section{Intro}\nBody",
                    "trans_content": "\\section{引言}\n中文正文",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
    monkeypatch.setattr(paper_service.settings, "data_dir", data_dir)
    monkeypatch.setattr(paper_service.settings, "uploads_dir", uploads_dir)
    monkeypatch.setattr(paper_service.settings, "outputs_dir", outputs_dir)
    monkeypatch.setattr(paper_service.settings, "community_papers_dir", community_dir, raising=False)

    class _TaskManager:
        def get_task(self, task_id):
            assert task_id == "task-1"
            return {
                "task_id": task_id,
                "status": "completed",
                "source_type": "arxiv",
                "arxiv_id": "2503.01010",
                "user_id": "user-1",
                "source_available": True,
                "source_path": str(source_dir),
                "output_path": str(output_dir),
            }

    inserted = {}
    updated = []
    upserted = {}

    async def _fetch_paper_by_arxiv_id(_arxiv_id):
        return None

    async def _insert_paper(payload):
        inserted.update(payload)
        return _paper(id="paper-1", **payload)

    async def _update_paper(paper_id, payload):
        updated.append((paper_id, payload))
        return _paper(id=paper_id, **payload)

    async def _upsert_latest_asset(**kwargs):
        upserted[kwargs["asset_type"]] = kwargs
        return {
            "id": f"asset-{kwargs['asset_type']}",
            "paper_id": kwargs["paper_id"],
            "task_id": kwargs["task_id"],
            "asset_type": kwargs["asset_type"],
            "file_path": kwargs["file_path"],
            "file_name": kwargs["file_name"],
            "mime_type": kwargs.get("mime_type"),
            "created_at": "2026-03-18T00:00:00+00:00",
        }

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(paper_service, "_fetch_paper_by_arxiv_id", _fetch_paper_by_arxiv_id)
    monkeypatch.setattr(paper_service, "_insert_paper", _insert_paper)
    monkeypatch.setattr(paper_service, "_update_paper", _update_paper)
    monkeypatch.setattr(paper_service, "_upsert_latest_asset", _upsert_latest_asset)

    result = asyncio.run(
        paper_service.ensure_task_published_to_community_library(
            task_id="task-1",
        )
    )

    assert result["paper"]["id"] == "paper-1"
    assert inserted["source"] == "arxiv"
    assert inserted["arxiv_id"] == "2503.01010"
    assert inserted["community_status"] == "user_fallback"
    assert set(upserted) == {"source_archive", "translated_pdf", "preview_html"}
    for asset_type, payload in upserted.items():
        stored_path = Path(payload["file_path"])
        assert not stored_path.is_absolute(), asset_type
        assert payload["file_path"].startswith("data/community_papers/paper-1/")
        assert (base_dir / payload["file_path"]).exists(), asset_type

    assert source_dir.exists()
    assert (source_dir / "main.tex").read_text(encoding="utf-8") == "\\section{Intro}"
    assert output_dir.exists()
    assert (output_dir / "paper_translated.pdf").read_text(encoding="utf-8") == "pdf-bytes"
    assert (output_dir / "sections_map.json").exists()


def test_publish_task_reuses_existing_paper_for_same_arxiv(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    data_dir = base_dir / "data"
    uploads_dir = data_dir / "uploads"
    outputs_dir = data_dir / "outputs"
    community_dir = data_dir / "community_papers"
    source_dir = uploads_dir / "arxiv_2503.01010"
    output_dir = outputs_dir / "task-1"
    source_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "main.tex").write_text("\\section{Intro}", encoding="utf-8")
    (output_dir / "paper_translated.pdf").write_text("pdf-bytes", encoding="utf-8")
    (output_dir / "sections_map.json").write_text(
        json.dumps(
            [
                {
                    "section": "1",
                    "content": "\\section{Intro}\nBody",
                    "trans_content": "\\section{引言}\n中文正文",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
    monkeypatch.setattr(paper_service.settings, "data_dir", data_dir)
    monkeypatch.setattr(paper_service.settings, "uploads_dir", uploads_dir)
    monkeypatch.setattr(paper_service.settings, "outputs_dir", outputs_dir)
    monkeypatch.setattr(paper_service.settings, "community_papers_dir", community_dir, raising=False)

    class _TaskManager:
        def get_task(self, task_id):
            return {
                "task_id": task_id,
                "status": "completed",
                "source_type": "arxiv",
                "arxiv_id": "2503.01010",
                "user_id": "user-1",
                "source_available": True,
                "source_path": str(source_dir),
                "output_path": str(output_dir),
            }

    inserted = {"called": False}
    updated = []

    async def _fetch_paper_by_arxiv_id(_arxiv_id):
        return _paper(id="paper-existing", trans_status="queued")

    async def _insert_paper(payload):
        inserted["called"] = True
        return _paper(id="paper-new", **payload)

    async def _update_paper(paper_id, payload):
        updated.append((paper_id, payload))
        return _paper(id=paper_id, **payload)

    async def _upsert_latest_asset(**kwargs):
        return {
            "id": f"asset-{kwargs['asset_type']}",
            "paper_id": kwargs["paper_id"],
            "task_id": kwargs["task_id"],
            "asset_type": kwargs["asset_type"],
            "file_path": kwargs["file_path"],
            "file_name": kwargs["file_name"],
            "mime_type": kwargs.get("mime_type"),
            "created_at": "2026-03-18T00:00:00+00:00",
        }

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(paper_service, "_fetch_paper_by_arxiv_id", _fetch_paper_by_arxiv_id)
    monkeypatch.setattr(paper_service, "_insert_paper", _insert_paper)
    monkeypatch.setattr(paper_service, "_update_paper", _update_paper)
    monkeypatch.setattr(paper_service, "_upsert_latest_asset", _upsert_latest_asset)

    result = asyncio.run(
        paper_service.ensure_task_published_to_community_library(
            task_id="task-1",
        )
    )

    assert inserted["called"] is False
    assert result["paper"]["id"] == "paper-existing"
    assert any(entry[0] == "paper-existing" for entry in updated)
