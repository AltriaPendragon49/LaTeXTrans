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
