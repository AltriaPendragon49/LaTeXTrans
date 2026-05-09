import asyncio
import os
from pathlib import Path

from fastapi import Request

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import papers as papers_route
from backend.app.services import paper_service


def _request_with_headers(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/papers/paper-1/source-pdf",
            "headers": raw_headers,
            "query_string": b"",
            "scheme": "https",
            "server": ("testserver", 443),
            "client": ("127.0.0.1", 12345),
        }
    )


def test_resolve_source_pdf_prefers_object_storage_asset(monkeypatch):
    source_asset = {
        "id": "asset-source-pdf",
        "paper_id": "paper-1",
        "task_id": "task-1",
        "asset_type": "source_pdf",
        "storage_backend": "object_storage",
        "file_path": "latextrans-prod/data/community_papers/paper-1/source_pdf/2501.12345.pdf",
        "file_name": "2501.12345.pdf",
        "mime_type": "application/pdf",
    }

    async def _fake_public_paper(paper_id: str):
        assert paper_id == "paper-1"
        return {
            "id": paper_id,
            "source": "arxiv",
            "arxiv_id": "2501.12345",
            "visibility": "public",
            "status": "published",
        }

    async def _fake_asset_map(*, paper_id: str):
        assert paper_id == "paper-1"
        return {"source_pdf": source_asset}

    def _fake_signed_url(asset, *, expires_in: int, response_params=None):
        assert asset is source_asset
        assert expires_in == 300
        assert response_params["response-content-disposition"].startswith("inline;")
        assert response_params["response-content-type"] == "application/pdf"
        return "https://cos.example.com/source.pdf?sign=abc"

    monkeypatch.setattr(paper_service, "_ensure_public_paper", _fake_public_paper)
    monkeypatch.setattr(paper_service, "_fetch_asset_map_for_paper", _fake_asset_map)
    monkeypatch.setattr(paper_service, "_resolve_object_storage_signed_url", _fake_signed_url)

    result = asyncio.run(paper_service.resolve_paper_source_pdf_preview(paper_id="paper-1"))

    assert result["paper_id"] == "paper-1"
    assert result["asset"] is source_asset
    assert result["signed_url"] == "https://cos.example.com/source.pdf?sign=abc"
    assert result["filename"] == "2501.12345.pdf"
    assert "arxiv_id" not in result


def test_preview_source_pdf_redirects_to_signed_object_storage_url(monkeypatch):
    async def _fake_preview(*, paper_id: str, content_disposition: str = "inline"):
        assert paper_id == "paper-1"
        assert content_disposition == "inline"
        return {
            "paper_id": paper_id,
            "asset": {
                "id": "asset-source-pdf",
                "file_name": "source.pdf",
                "mime_type": "application/pdf",
            },
            "signed_url": "https://cos.example.com/source.pdf?sign=abc",
        }

    monkeypatch.setattr(papers_route.paper_service, "resolve_paper_source_pdf_preview", _fake_preview)

    response = asyncio.run(
        papers_route.preview_source_paper_pdf(
            "paper-1",
            _request_with_headers({"range": "bytes=0-1023"}),
        )
    )

    assert response.status_code == 307
    assert response.headers["location"] == "https://cos.example.com/source.pdf?sign=abc"


def test_download_source_pdf_redirects_to_attachment_signed_url(monkeypatch):
    async def _fake_preview(*, paper_id: str, content_disposition: str = "inline"):
        assert content_disposition == "attachment"
        return {
            "paper_id": paper_id,
            "asset": {"id": "asset-source-pdf", "file_name": "source.pdf"},
            "signed_url": "https://cos.example.com/source.pdf?download=1&sign=abc",
        }

    monkeypatch.setattr(papers_route.paper_service, "resolve_paper_source_pdf_preview", _fake_preview)

    response = asyncio.run(papers_route.download_source_paper_pdf("paper-1", _request_with_headers()))

    assert response.status_code == 307
    assert response.headers["location"] == "https://cos.example.com/source.pdf?download=1&sign=abc"


def test_persist_arxiv_source_pdf_registers_raw_cache_asset_without_download(monkeypatch):
    captured = {}

    async def _fake_asset_map(*, paper_id: str):
        assert paper_id == "paper-1"
        return {}

    def _unexpected_download(_arxiv_id: str):
        raise AssertionError("raw-cache-backed source_pdf should not download through backend")

    def _fake_raw_key(arxiv_id: str):
        assert arxiv_id == "2501.12345"
        return "arxiv/raw/pdf/2501.12345.pdf"

    def _fake_raw_enabled():
        return True

    async def _fake_upsert(**kwargs):
        captured["upsert"] = kwargs
        return {"id": "asset-source-pdf", **kwargs}

    monkeypatch.setattr(paper_service, "_fetch_asset_map_for_paper", _fake_asset_map)
    monkeypatch.setattr(paper_service, "_download_arxiv_source_pdf_to_temp", _unexpected_download)
    monkeypatch.setattr(paper_service.arxiv_raw_cache, "is_enabled", _fake_raw_enabled)
    monkeypatch.setattr(paper_service.arxiv_raw_cache, "raw_pdf_object_key", _fake_raw_key)
    monkeypatch.setattr(paper_service, "_upsert_latest_asset", _fake_upsert)

    result = asyncio.run(
        paper_service.persist_arxiv_source_pdf_asset(
            paper_id="paper-1",
            task_id="task-1",
            arxiv_id="2501.12345",
        )
    )

    assert result["asset_type"] == "source_pdf"
    assert captured["upsert"]["file_path"] == "arxiv/raw/pdf/2501.12345.pdf"
    assert captured["upsert"]["storage_backend"] == "object_storage"


def test_persist_arxiv_source_pdf_uploads_and_upserts(monkeypatch, tmp_path: Path):
    downloaded_pdf = tmp_path / "downloaded.pdf"
    downloaded_pdf.write_bytes(b"%PDF-1.7\nsource")
    captured = {}

    async def _fake_asset_map(*, paper_id: str):
        assert paper_id == "paper-1"
        return {}

    def _fake_download(arxiv_id: str):
        assert arxiv_id == "2501.12345"
        return downloaded_pdf

    def _fake_persist(*, local_path: Path, paper_id: str, task_id: str | None, asset_type: str, source_name: str, content_type: str | None):
        captured["persist"] = {
            "local_path": local_path,
            "paper_id": paper_id,
            "task_id": task_id,
            "asset_type": asset_type,
            "source_name": source_name,
            "content_type": content_type,
        }
        return type(
            "StoredRef",
            (),
            {
                "storage_backend": "object_storage",
                "object_key": "latextrans-prod/data/community_papers/paper-1/source_pdf/2501.12345.pdf",
                "content_type": "application/pdf",
            },
        )(), "2501.12345.pdf"

    async def _fake_upsert(**kwargs):
        captured["upsert"] = kwargs
        return {"id": "asset-source-pdf", **kwargs}

    monkeypatch.setattr(paper_service, "_fetch_asset_map_for_paper", _fake_asset_map)
    monkeypatch.setattr(paper_service, "_download_arxiv_source_pdf_to_temp", _fake_download)
    monkeypatch.setattr(paper_service, "_persist_retained_artifact", _fake_persist)
    monkeypatch.setattr(paper_service, "_upsert_latest_asset", _fake_upsert)

    result = asyncio.run(
        paper_service.persist_arxiv_source_pdf_asset(
            paper_id="paper-1",
            task_id="task-1",
            arxiv_id="2501.12345",
        )
    )

    assert result["asset_type"] == "source_pdf"
    assert captured["persist"]["asset_type"] == "source_pdf"
    assert captured["persist"]["source_name"] == "2501.12345.pdf"
    assert captured["persist"]["content_type"] == "application/pdf"
    assert captured["upsert"]["storage_backend"] == "object_storage"
    assert captured["upsert"]["file_path"].endswith("/source_pdf/2501.12345.pdf")
    assert not downloaded_pdf.exists()


def test_download_arxiv_source_pdf_prefers_raw_cache_url(monkeypatch, tmp_path: Path):
    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size: int):
            assert chunk_size == 1024 * 1024
            yield b"%PDF-1.7\nsource"

    def _fake_get(url: str, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return _FakeResponse()

    monkeypatch.setattr(paper_service, "_source_pdf_download_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(
        paper_service.arxiv_raw_cache,
        "build_pdf_download_url",
        lambda arxiv_id, **_kwargs: "https://cos.example.com/arxiv/raw/pdf/2501.12345.pdf?sign=abc",
    )
    monkeypatch.setattr(paper_service.requests, "get", _fake_get)

    downloaded_pdf = paper_service._download_arxiv_source_pdf_to_temp("2501.12345")

    assert captured["url"] == "https://cos.example.com/arxiv/raw/pdf/2501.12345.pdf?sign=abc"
    assert captured["kwargs"]["stream"] is True
    assert downloaded_pdf.read_bytes().startswith(b"%PDF")


def test_sync_completed_arxiv_task_persists_source_pdf(monkeypatch):
    captured = {}

    class _FakeTaskManager:
        def get_task(self, task_id: str):
            assert task_id == "task-1"
            return {
                "task_id": task_id,
                "status": "completed",
                "source_type": "arxiv",
                "arxiv_id": "2501.12345",
            }

    async def _fake_fetch_paper(paper_id: str):
        return {
            "id": paper_id,
            "source": "arxiv",
            "arxiv_id": "2501.12345",
            "trans_status": "processing",
        }

    async def _fake_persist_source_pdf(**kwargs):
        captured["source_pdf"] = kwargs
        return {"id": "asset-source-pdf", "asset_type": "source_pdf"}

    async def _fake_translated_asset(**kwargs):
        return {"id": "asset-translated", "storage_backend": "object_storage"}

    async def _fake_preview_asset(**kwargs):
        return None

    async def _fake_update_paper(paper_id: str, payload: dict):
        captured["paper_update"] = (paper_id, payload)
        return {"id": paper_id, **payload}

    monkeypatch.setattr(paper_service, "task_manager", _FakeTaskManager())
    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", _fake_fetch_paper)
    monkeypatch.setattr(paper_service, "_persist_source_pdf_for_paper_if_arxiv", _fake_persist_source_pdf)
    monkeypatch.setattr(paper_service, "_resolve_translated_pdf_asset", _fake_translated_asset)
    monkeypatch.setattr(paper_service, "_resolve_preview_html_asset", _fake_preview_asset)
    monkeypatch.setattr(paper_service, "_update_paper", _fake_update_paper)
    monkeypatch.setattr(paper_service, "clear_cached_runtime_artifacts", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(paper_service, "_schedule_public_thumbnail_warmup", lambda **_kwargs: None)

    result = asyncio.run(
        paper_service._sync_task_assets_for_paper(
            paper_id="paper-1",
            task_id="task-1",
            promote_to_official=False,
        )
    )

    assert result["status"] == "completed"
    assert result["source_pdf_asset"]["id"] == "asset-source-pdf"
    assert captured["source_pdf"]["paper_id"] == "paper-1"
    assert captured["source_pdf"]["task_id"] == "task-1"
    assert captured["source_pdf"]["paper"]["arxiv_id"] == "2501.12345"


def test_create_source_asset_materializes_missing_object_storage_source(monkeypatch, tmp_path: Path):
    source_dir = tmp_path / "materialized-source"
    source_dir.mkdir()
    (source_dir / "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
    captured = {}

    def _fake_materialize(stored_path: str, *, task_id: str | None, kind: str):
        assert stored_path == "data/uploads/arxiv_2501.12345/2501.12345"
        assert task_id == "task-1"
        assert kind == "source"
        return source_dir

    def _fake_persist(*, local_path: Path, paper_id: str, task_id: str | None, asset_type: str, source_name: str, content_type: str | None):
        captured["persist"] = {
            "local_path": local_path,
            "paper_id": paper_id,
            "task_id": task_id,
            "asset_type": asset_type,
            "source_name": source_name,
            "content_type": content_type,
        }
        return type(
            "StoredRef",
            (),
            {
                "storage_backend": "object_storage",
                "object_key": "latextrans-prod/data/community_papers/paper-1/source/source.zip",
                "content_type": "application/zip",
            },
        )(), "source.zip"

    async def _fake_upsert(**kwargs):
        captured["upsert"] = kwargs
        return {"id": "asset-source-archive", **kwargs}

    monkeypatch.setattr(paper_service, "_resolve_storage_path", lambda _path: tmp_path / "missing-source")
    monkeypatch.setattr(paper_service, "_materialize_task_directory_for_asset_recovery", _fake_materialize)
    monkeypatch.setattr(paper_service, "_persist_retained_artifact", _fake_persist)
    monkeypatch.setattr(paper_service, "_upsert_latest_asset", _fake_upsert)
    monkeypatch.setattr(paper_service, "clear_cached_runtime_artifacts", lambda *_args, **_kwargs: captured.setdefault("cleared", True))

    result = asyncio.run(
        paper_service._create_source_asset(
            paper_id="paper-1",
            task_id="task-1",
            source_path="data/uploads/arxiv_2501.12345/2501.12345",
        )
    )

    assert result["asset_type"] == "source_archive"
    assert captured["persist"]["local_path"] == source_dir
    assert captured["persist"]["asset_type"] == "source_archive"
    assert captured["upsert"]["storage_backend"] == "object_storage"
    assert captured["cleared"] is True


def test_candidate_output_directories_materializes_missing_object_storage_output(monkeypatch, tmp_path: Path):
    output_dir = tmp_path / "materialized-output"
    output_dir.mkdir()
    child_dir = output_dir / "zh_task"
    child_dir.mkdir()

    class _FakeTaskManager:
        def get_task(self, task_id: str):
            assert task_id == "task-1"
            return {"output_path": "data/outputs/task-1"}

    def _fake_resolve(_path: str):
        return tmp_path / "missing-output"

    def _fake_materialize(stored_path: str, *, task_id: str | None, kind: str):
        assert stored_path == "data/outputs/task-1"
        assert task_id == "task-1"
        assert kind == "output"
        return output_dir

    monkeypatch.setattr(paper_service, "task_manager", _FakeTaskManager())
    monkeypatch.setattr(paper_service, "_resolve_storage_path", _fake_resolve)
    monkeypatch.setattr(paper_service, "_materialize_task_directory_for_asset_recovery", _fake_materialize)
    monkeypatch.setattr(paper_service.settings, "outputs_dir", tmp_path / "outputs")

    result = paper_service._candidate_output_directories_for_task("task-1")

    assert result == [output_dir, child_dir]
