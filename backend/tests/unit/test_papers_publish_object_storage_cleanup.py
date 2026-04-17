import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_service
from backend.app.services import task_artifact_storage
from backend.app.services.storage_backend import StoredObjectRef


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


def test_publish_task_to_object_storage_clears_task_output_root(monkeypatch, tmp_path: Path):
    base_dir = tmp_path / "repo"
    data_dir = base_dir / "data"
    uploads_dir = data_dir / "uploads"
    outputs_dir = data_dir / "outputs"
    community_dir = data_dir / "community_papers"
    storage_temp_dir = data_dir / "tmp_storage"
    source_dir = uploads_dir / "arxiv_2503.01010"
    output_dir = outputs_dir / "task-1"
    source_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    storage_temp_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "main.tex").write_text("\\section{Intro}", encoding="utf-8")
    translated_pdf = output_dir / "paper_translated.pdf"
    translated_pdf.write_text("pdf-bytes", encoding="utf-8")
    (output_dir / "sections_map.json").write_text(
        json.dumps(
            [
                {
                    "section": "1",
                    "content": "\\section{Intro}\nBody",
                    "trans_content": "\\section{Introduction}\nTranslated body",
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
    monkeypatch.setattr(paper_service.settings, "data_dir", data_dir)
    monkeypatch.setattr(paper_service.settings, "uploads_dir", uploads_dir)
    monkeypatch.setattr(paper_service.settings, "outputs_dir", outputs_dir)
    monkeypatch.setattr(paper_service.settings, "community_papers_dir", community_dir, raising=False)
    monkeypatch.setattr(paper_service.settings, "storage_temp_dir", storage_temp_dir, raising=False)
    monkeypatch.setattr(paper_service.settings, "storage_backend_mode", "cos", raising=False)
    monkeypatch.setattr(paper_service.settings, "cos_base_prefix", "paperx", raising=False)

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

    class _FakeStorage:
        def put_file(self, *, local_path, object_key, content_type, delete_local):
            return type(
                "Stored",
                (),
                {
                    "storage_backend": "object_storage",
                    "object_key": object_key,
                    "content_type": content_type,
                    "size_bytes": local_path.stat().st_size if local_path.exists() else None,
                },
            )()

        def read_text(self, *, ref, encoding="utf-8"):
            raise AssertionError("preview read path is not part of this test")

    cleaned = []

    async def _fetch_paper_by_arxiv_id(_arxiv_id):
        return None

    async def _insert_paper(payload):
        return _paper(id="paper-1", **payload)

    async def _update_paper(paper_id, payload):
        return _paper(id=paper_id, **payload)

    async def _upsert_latest_asset(**kwargs):
        return {
            "id": f"asset-{kwargs['asset_type']}",
            "paper_id": kwargs["paper_id"],
            "task_id": kwargs["task_id"],
            "asset_type": kwargs["asset_type"],
            "storage_backend": kwargs["storage_backend"],
            "file_path": kwargs["file_path"],
            "file_name": kwargs["file_name"],
            "mime_type": kwargs.get("mime_type"),
            "created_at": "2026-03-18T00:00:00+00:00",
        }

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(paper_service, "_get_storage_backend", lambda: _FakeStorage())
    monkeypatch.setattr(paper_service, "_fetch_paper_by_arxiv_id", _fetch_paper_by_arxiv_id)
    monkeypatch.setattr(paper_service, "_insert_paper", _insert_paper)
    monkeypatch.setattr(paper_service, "_update_paper", _update_paper)
    monkeypatch.setattr(paper_service, "_upsert_latest_asset", _upsert_latest_asset)
    monkeypatch.setattr(
        paper_service,
        "clear_cached_runtime_artifacts",
        lambda task_id, retained_paths: cleaned.append((task_id, tuple(str(path) for path in retained_paths))),
    )

    asyncio.run(paper_service.ensure_task_published_to_community_library(task_id="task-1"))

    assert any(str(output_dir) in paths for _task_id, paths in cleaned)


def test_publish_task_recovers_translated_pdf_from_object_storage_manifest(monkeypatch, tmp_path: Path):
    base_dir = tmp_path / "repo"
    data_dir = base_dir / "data"
    uploads_dir = data_dir / "uploads"
    outputs_dir = data_dir / "outputs"
    community_dir = data_dir / "community_papers"
    storage_temp_dir = data_dir / "tmp_storage"
    source_dir = uploads_dir / "arxiv_2503.01010"
    source_dir.mkdir(parents=True, exist_ok=True)
    storage_temp_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "main.tex").write_text("\\section{Intro}", encoding="utf-8")

    manifest = {
        "translated_pdf": "paper/main.pdf",
        "translated_source_archive": None,
        "terminology_csv": None,
        "logs": [],
    }
    payloads = {
        "data/outputs/task-1/storage_manifest.json": json.dumps(manifest).encode("utf-8"),
        "data/outputs/task-1/paper/main.pdf": b"%PDF-1.4\\nremote-pdf",
    }

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
    monkeypatch.setattr(paper_service.settings, "data_dir", data_dir)
    monkeypatch.setattr(paper_service.settings, "uploads_dir", uploads_dir)
    monkeypatch.setattr(paper_service.settings, "outputs_dir", outputs_dir)
    monkeypatch.setattr(paper_service.settings, "community_papers_dir", community_dir, raising=False)
    monkeypatch.setattr(paper_service.settings, "storage_temp_dir", storage_temp_dir, raising=False)
    monkeypatch.setattr(paper_service.settings, "storage_backend_mode", "cos", raising=False)
    monkeypatch.setattr(paper_service.settings, "cos_base_prefix", "paperx", raising=False)
    monkeypatch.setattr(task_artifact_storage.settings, "base_dir", base_dir)
    monkeypatch.setattr(task_artifact_storage.settings, "data_dir", data_dir, raising=False)
    monkeypatch.setattr(task_artifact_storage.settings, "uploads_dir", uploads_dir)
    monkeypatch.setattr(task_artifact_storage.settings, "outputs_dir", outputs_dir)
    monkeypatch.setattr(task_artifact_storage.settings, "storage_temp_dir", storage_temp_dir, raising=False)
    monkeypatch.setattr(task_artifact_storage.settings, "storage_backend_mode", "cos", raising=False)
    monkeypatch.setattr(task_artifact_storage.settings, "cos_base_prefix", "paperx", raising=False)

    class _TaskManager:
        def get_task(self, task_id):
            assert task_id == "task-1"
            return {
                "task_id": task_id,
                "status": "completed_with_warnings",
                "source_type": "arxiv",
                "arxiv_id": "2503.01010",
                "user_id": "user-1",
                "source_available": True,
                "source_path": str(source_dir),
                "output_path": "data/outputs/task-1",
            }

    class _FakeStorage:
        def put_file(self, *, local_path, object_key, content_type, delete_local):
            return StoredObjectRef(
                storage_backend="object_storage",
                object_key=object_key,
                content_type=content_type,
                size_bytes=local_path.stat().st_size if local_path.exists() else None,
            )

        def read_text(self, *, ref, encoding="utf-8"):
            return payloads[ref.object_key].decode(encoding)

        def download_file(self, *, object_key, local_path):
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(payloads[object_key])
            return local_path

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
            "storage_backend": kwargs["storage_backend"],
            "file_path": kwargs["file_path"],
            "file_name": kwargs["file_name"],
            "mime_type": kwargs.get("mime_type"),
            "created_at": "2026-03-18T00:00:00+00:00",
        }

    fake_storage = _FakeStorage()
    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(paper_service, "_get_storage_backend", lambda: fake_storage)
    monkeypatch.setattr(task_artifact_storage, "_get_storage_backend", lambda: fake_storage)
    monkeypatch.setattr(paper_service, "_fetch_paper_by_arxiv_id", _fetch_paper_by_arxiv_id)
    monkeypatch.setattr(paper_service, "_insert_paper", _insert_paper)
    monkeypatch.setattr(paper_service, "_update_paper", _update_paper)
    monkeypatch.setattr(paper_service, "_upsert_latest_asset", _upsert_latest_asset)

    result = asyncio.run(paper_service.ensure_task_published_to_community_library(task_id="task-1"))

    assert result["paper"]["id"] == "paper-1"
    assert inserted["community_status"] == "user_fallback"
    assert "translated_pdf" in upserted
    assert upserted["translated_pdf"]["storage_backend"] == "object_storage"
    assert upserted["translated_pdf"]["file_path"].startswith("paperx/data/community_papers/paper-1/")
