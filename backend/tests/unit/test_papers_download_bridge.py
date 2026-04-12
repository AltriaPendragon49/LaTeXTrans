import asyncio
import base64
import json
import os
from pathlib import Path

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
        "title": "Downloadable paper",
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


def test_create_download_session_returns_short_lived_signed_url(monkeypatch):
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
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-1",
                    "asset_type": "translated_pdf",
                    "file_path": "D:/outputs/task-1/translated.pdf",
                    "file_name": "translated.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )

    result = asyncio.run(paper_service.create_paper_download_session(paper_id="paper-1"))

    assert result["paper_id"] == "paper-1"
    assert result["asset_id"] == "asset-pdf"
    assert "token=" in result["download_url"]
    assert result["expires_at"]


def test_create_download_session_recovers_missing_pdf_asset_from_completed_output(monkeypatch, tmp_path):
    base_dir = tmp_path / "repo"
    output_dir = base_dir / "data" / "outputs" / "task-translate"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "paper_translated.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%mock\n")
    (output_dir / "task_log.json").write_text(
        json.dumps(
            [
                {
                    "event": "compilation_completed",
                    "pdf_path": str(pdf_path),
                }
            ]
        ),
        encoding="utf-8",
    )

    paper = _paper(
        trans_latest_task_id="task-translate",
        community_selected_task_id="task-translate",
    )

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
    monkeypatch.setattr(paper_service.settings, "community_papers_dir", base_dir / "data" / "community_papers")
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=paper),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={}),
    )

    class _TaskManager:
        def get_task(self, task_id):
            assert task_id == "task-translate"
            return {"task_id": task_id, "output_path": str(output_dir)}

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(0, result={**paper, "id": paper_id, **payload}),
    )

    async def _upsert_latest_asset(**kwargs):
        return {
            "id": "asset-pdf-recovered",
            "paper_id": kwargs["paper_id"],
            "task_id": kwargs["task_id"],
            "asset_type": kwargs["asset_type"],
            "file_path": kwargs["file_path"],
            "file_name": kwargs["file_name"],
            "mime_type": kwargs["mime_type"],
            "created_at": "2026-03-19T00:00:00+00:00",
        }

    monkeypatch.setattr(paper_service, "_upsert_latest_asset", _upsert_latest_asset)

    result = asyncio.run(paper_service.create_paper_download_session(paper_id="paper-1"))

    assert result["asset_id"] == "asset-pdf-recovered"
    assert "token=" in result["download_url"]


def test_resolve_paper_download_rejects_tampered_token(monkeypatch):
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
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-1",
                    "asset_type": "translated_pdf",
                    "file_path": "D:/outputs/task-1/translated.pdf",
                    "file_name": "translated.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )

    session = asyncio.run(paper_service.create_paper_download_session(paper_id="paper-1"))
    token = session["download_url"].split("token=", 1)[1] + "tamper"

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(paper_service.resolve_paper_download(paper_id="paper-1", token=token))

    assert exc_info.value.status_code == 403


def test_resolve_paper_download_increments_count_on_success(monkeypatch, tmp_path):
    increments = []
    pdf_path = tmp_path / "translated.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%mock\n")

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
                    "translated_pdf": {
                        "id": "asset-pdf",
                        "task_id": "task-1",
                        "asset_type": "translated_pdf",
                        "file_path": str(pdf_path),
                        "file_name": "translated.pdf",
                        "mime_type": "application/pdf",
                        "created_at": "2026-03-18T02:00:00+00:00",
                    }
                },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_increment_paper_download_count",
        lambda paper_id: asyncio.sleep(0, result=increments.append(paper_id)),
    )

    session = asyncio.run(paper_service.create_paper_download_session(paper_id="paper-1"))
    token = session["download_url"].split("token=", 1)[1]
    result = asyncio.run(paper_service.resolve_paper_download(paper_id="paper-1", token=token))

    assert result["paper_id"] == "paper-1"
    assert result["asset"]["id"] == "asset-pdf"
    assert increments == ["paper-1"]


def test_resolve_paper_download_supports_relative_library_path(monkeypatch, tmp_path):
    increments = []
    base_dir = tmp_path / "repo"
    pdf_path = base_dir / "data" / "community_papers" / "paper-1" / "translated" / "translated.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"%PDF-1.4\n%mock\n")

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
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
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-1",
                    "asset_type": "translated_pdf",
                    "file_path": "data/community_papers/paper-1/translated/translated.pdf",
                    "file_name": "translated.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_increment_paper_download_count",
        lambda paper_id: asyncio.sleep(0, result=increments.append(paper_id)),
    )

    session = asyncio.run(paper_service.create_paper_download_session(paper_id="paper-1"))
    token = session["download_url"].split("token=", 1)[1]
    result = asyncio.run(paper_service.resolve_paper_download(paper_id="paper-1", token=token))

    assert Path(result["file_path"]) == pdf_path
    assert increments == ["paper-1"]


def test_resolve_paper_download_supports_windows_absolute_library_path(monkeypatch, tmp_path):
    increments = []
    base_dir = tmp_path / "backend"
    pdf_path = base_dir / "data" / "community_papers" / "paper-1" / "translated" / "translated.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"%PDF-1.4\n%mock\n")

    monkeypatch.setattr(paper_service.settings, "base_dir", base_dir)
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
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-1",
                    "asset_type": "translated_pdf",
                    "file_path": r"D:\future\antigravity\LaTexTrans\backend\data\community_papers\paper-1\translated\translated.pdf",
                    "file_name": "translated.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_increment_paper_download_count",
        lambda paper_id: asyncio.sleep(0, result=increments.append(paper_id)),
    )

    session = asyncio.run(paper_service.create_paper_download_session(paper_id="paper-1"))
    token = session["download_url"].split("token=", 1)[1]
    result = asyncio.run(paper_service.resolve_paper_download(paper_id="paper-1", token=token))

    assert Path(result["file_path"]) == pdf_path
    assert increments == ["paper-1"]


def test_resolve_paper_download_does_not_fail_when_download_count_increment_errors(monkeypatch, tmp_path):
    pdf_path = tmp_path / "translated.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%mock\n")

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
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-1",
                    "asset_type": "translated_pdf",
                    "file_path": str(pdf_path),
                    "file_name": "translated.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )

    async def _raise_increment(_paper_id: str):
        raise RuntimeError("schema cache miss")

    monkeypatch.setattr(paper_service, "_increment_paper_download_count", _raise_increment)

    session = asyncio.run(paper_service.create_paper_download_session(paper_id="paper-1"))
    token = session["download_url"].split("token=", 1)[1]
    result = asyncio.run(paper_service.resolve_paper_download(paper_id="paper-1", token=token))

    assert result["paper_id"] == "paper-1"
    assert result["asset"]["id"] == "asset-pdf"


def test_resolve_paper_translated_pdf_preview_returns_signed_url_for_object_storage(monkeypatch):
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
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-1",
                    "asset_type": "translated_pdf",
                    "storage_backend": "object_storage",
                    "file_path": "https://cos.example.com/paper.pdf?sign=abc",
                    "file_name": "translated.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )

    result = asyncio.run(paper_service.resolve_paper_translated_pdf_preview(paper_id="paper-1"))

    assert result["paper_id"] == "paper-1"
    assert result["signed_url"].startswith("https://cos.example.com/")


def test_resolve_paper_download_returns_signed_url_for_object_storage(monkeypatch):
    increments = []

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
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-1",
                    "asset_type": "translated_pdf",
                    "storage_backend": "object_storage",
                    "file_path": "https://cos.example.com/paper.pdf?sign=abc",
                    "file_name": "translated.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_increment_paper_download_count",
        lambda paper_id: asyncio.sleep(0, result=increments.append(paper_id)),
    )

    session = asyncio.run(paper_service.create_paper_download_session(paper_id="paper-1"))
    token = session["download_url"].split("token=", 1)[1]
    result = asyncio.run(paper_service.resolve_paper_download(paper_id="paper-1", token=token))

    assert result["paper_id"] == "paper-1"
    assert result["signed_url"].startswith("https://cos.example.com/")
    assert increments == ["paper-1"]


def test_resolve_paper_download_builds_signed_url_from_object_key(monkeypatch):
    increments = []

    class _FakeStorageBackend:
        def build_download_url(self, *, object_key: str, expires_in: int):
            assert object_key == "paperx/data/community_papers/paper-1/translated/translated.pdf"
            assert expires_in == 600
            return "https://cos.example.com/generated.pdf?sign=xyz"

    monkeypatch.setattr(
        paper_service,
        "_get_storage_backend",
        lambda: _FakeStorageBackend(),
    )
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
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-1",
                    "asset_type": "translated_pdf",
                    "storage_backend": "object_storage",
                    "file_path": "paperx/data/community_papers/paper-1/translated/translated.pdf",
                    "file_name": "translated.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_increment_paper_download_count",
        lambda paper_id: asyncio.sleep(0, result=increments.append(paper_id)),
    )

    session = asyncio.run(paper_service.create_paper_download_session(paper_id="paper-1"))
    token = session["download_url"].split("token=", 1)[1]
    result = asyncio.run(paper_service.resolve_paper_download(paper_id="paper-1", token=token))

    assert result["signed_url"] == "https://cos.example.com/generated.pdf?sign=xyz"
    assert increments == ["paper-1"]
