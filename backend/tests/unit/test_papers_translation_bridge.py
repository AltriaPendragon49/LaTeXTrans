import asyncio
import base64
import json
import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import papers as papers_route
from backend.app.api.routes.translate import TranslateRequest
from backend.app.services import paper_service


def _jwt_for(user_id: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": user_id}).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"header.{payload}.sig"


def _paper(**overrides):
    base = {
        "id": "paper-1",
        "source": "upload",
        "arxiv_id": None,
        "title": "Bridge paper",
        "authors": [],
        "categories": [],
        "abstract_raw": "raw abstract",
        "abstract_translated": "中文摘要",
        "community_status": "official",
        "trans_status": "not_started",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": "2026-03-18T02:00:00+00:00",
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


def test_translate_paper_route_allows_public_translation_without_auth(monkeypatch):
    monkeypatch.setattr(
        papers_route.paper_service,
        "start_paper_translation",
        lambda **kwargs: asyncio.sleep(
            0,
            result={
                "paper_id": kwargs["paper_id"],
                "task_id": "task-public",
                "status": "queued",
                "reused_existing_task": False,
                "processing_url": "/processing?taskId=task-public",
            },
        ),
    )

    result = asyncio.run(
        papers_route.translate_paper(
            paper_id="paper-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=None,
        )
    )

    assert result["paper_id"] == "paper-1"
    assert result["status"] == "queued"


def test_start_paper_translation_uses_null_user_for_public_runs(monkeypatch, tmp_path):
    created = {}
    source_dir = tmp_path / "source-paper"
    source_dir.mkdir()
    monkeypatch.setattr(paper_service.asyncio, "create_task", lambda coro: coro.close())
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper(source="upload")),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "source_archive": {
                    "id": "asset-source",
                    "paper_id": "paper-1",
                    "task_id": "task-upload",
                    "asset_type": "source_archive",
                    "file_path": str(source_dir),
                    "file_name": "source-paper",
                    "mime_type": "application/x-tex",
                    "created_at": "2026-03-18T00:00:00+00:00",
                }
            },
        ),
    )

    class _TaskManager:
        def create_task(self, **kwargs):
            created["create_task"] = kwargs
            return "task-public"

        def update_task(self, task_id, **kwargs):
            created["update_task"] = (task_id, kwargs)

        def persist_task_if_needed(self, task_id):
            created["persist_task"] = task_id
            return True

        def get_task(self, task_id):
            return {
                "task_id": task_id,
                "source_available": True,
                "status": "pending",
                "source_path": str(source_dir),
                "arxiv_id": None,
            }

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(
        paper_service,
        "_enqueue_existing_task_translation",
        lambda **kwargs: asyncio.sleep(0, result={"task_id": kwargs["task_id"], "status": "queued"}),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(
            0,
            result=_paper(
                id=paper_id,
                trans_status=payload.get("trans_status", "queued"),
                community_selected_task_id=payload.get("community_selected_task_id"),
                community_selected_asset_id=payload.get("community_selected_asset_id"),
            ),
        ),
    )

    result = asyncio.run(
        paper_service.start_paper_translation(
            paper_id="paper-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=None,
        )
    )

    assert created["create_task"]["user_id"] is None
    assert result["task_id"] == "task-public"


def test_start_paper_translation_reuses_active_selected_task(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "user-1", "roles": [], "is_admin": False}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(
                trans_status="processing",
                community_selected_task_id="task-active",
            ),
        ),
    )

    result = asyncio.run(
        paper_service.start_paper_translation(
            paper_id="paper-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
            current_user={"id": "user-1", "roles": ["user"]},
        )
    )

    assert result["paper_id"] == "paper-1"
    assert result["task_id"] == "task-active"
    assert result["status"] == "processing"
    assert result["reused_existing_task"] is True
    assert result["processing_url"].endswith("/processing?taskId=task-active")


def test_start_paper_translation_does_not_reuse_stale_intake_task(monkeypatch, tmp_path):
    created = {}
    source_dir = tmp_path / "source-paper"
    source_dir.mkdir()
    monkeypatch.setattr(paper_service.asyncio, "create_task", lambda coro: coro.close())

    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "user-1", "roles": [], "is_admin": False}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(
                trans_status="not_started",
                community_selected_task_id="task-upload",
            ),
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "source_archive": {
                    "id": "asset-source",
                    "paper_id": "paper-1",
                    "task_id": "task-upload",
                    "asset_type": "source_archive",
                    "file_path": str(source_dir),
                    "file_name": "source-paper",
                    "mime_type": "application/x-tex",
                    "created_at": "2026-03-18T00:00:00+00:00",
                }
            },
        ),
    )

    class _TaskManager:
        def create_task(self, **kwargs):
            created["create_task"] = kwargs
            return "task-new"

        def update_task(self, task_id, **kwargs):
            created["update_task"] = (task_id, kwargs)

        def persist_task_if_needed(self, task_id):
            created["persist_task"] = task_id
            return True

        def get_task(self, task_id):
            return {
                "task_id": task_id,
                "source_available": True,
                "status": "pending",
                "source_path": str(source_dir),
                "arxiv_id": None,
            }

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(
        paper_service,
        "_enqueue_existing_task_translation",
        lambda **kwargs: asyncio.sleep(0, result={"task_id": kwargs["task_id"], "status": "queued"}),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(
            0,
            result=_paper(
                id=paper_id,
                trans_status=payload.get("trans_status", "queued"),
                community_selected_task_id=payload.get("community_selected_task_id"),
                community_selected_asset_id=payload.get("community_selected_asset_id"),
            ),
        ),
    )

    result = asyncio.run(
        paper_service.start_paper_translation(
            paper_id="paper-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
            current_user={"id": "user-1", "roles": ["user"]},
        )
    )

    assert created["create_task"]["source_type"] == "upload"
    assert result["task_id"] == "task-new"
    assert result["reused_existing_task"] is False


def test_start_paper_translation_creates_task_from_latest_source_asset(monkeypatch, tmp_path):
    created = {}
    source_dir = tmp_path / "source-paper"
    source_dir.mkdir()
    monkeypatch.setattr(paper_service.asyncio, "create_task", lambda coro: coro.close())

    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "user-1", "roles": [], "is_admin": False}),
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
                "source_archive": {
                    "id": "asset-source",
                    "paper_id": "paper-1",
                    "task_id": None,
                    "asset_type": "source_archive",
                    "file_path": str(source_dir),
                    "file_name": "source-paper",
                    "mime_type": "application/x-tex",
                    "created_at": "2026-03-18T00:00:00+00:00",
                }
            },
        ),
    )

    class _TaskManager:
        def create_task(self, **kwargs):
            created["create_task"] = kwargs
            return "task-new"

        def update_task(self, task_id, **kwargs):
            created["update_task"] = (task_id, kwargs)

        def persist_task_if_needed(self, task_id):
            created["persist_task"] = task_id
            return True

        def get_task(self, task_id):
            return {
                "task_id": task_id,
                "source_available": True,
                "status": "pending",
                "source_path": str(source_dir),
                "arxiv_id": None,
            }

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(
        paper_service,
        "_enqueue_existing_task_translation",
        lambda **kwargs: asyncio.sleep(0, result={"task_id": kwargs["task_id"], "status": "queued"}),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(
            0,
            result=_paper(
                id=paper_id,
                trans_status=payload.get("trans_status", "queued"),
                community_selected_task_id=payload.get("community_selected_task_id"),
                community_selected_asset_id=payload.get("community_selected_asset_id"),
            ),
        ),
    )

    result = asyncio.run(
        paper_service.start_paper_translation(
            paper_id="paper-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
            current_user={"id": "user-1", "roles": ["user"]},
        )
    )

    assert created["create_task"]["source_type"] == "upload"
    assert created["update_task"][0] == "task-new"
    assert created["update_task"][1]["source_available"] is True
    assert created["update_task"][1]["source_path"] == str(source_dir).replace("\\", "/")
    assert result["task_id"] == "task-new"
    assert result["status"] == "queued"
    assert result["reused_existing_task"] is False


def test_start_paper_translation_uses_arxiv_bridge_when_source_asset_missing(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "user-1", "roles": [], "is_admin": False}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper(source="arxiv", arxiv_id="2503.01010")),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(0, result={}),
    )
    monkeypatch.setattr(
        paper_service,
        "_start_arxiv_paper_translation",
        lambda **_kwargs: asyncio.sleep(0, result={"task_id": "task-arxiv", "status": "queued"}),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(0, result=_paper(id=paper_id, **payload)),
    )

    result = asyncio.run(
        paper_service.start_paper_translation(
            paper_id="paper-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
            current_user={"id": "user-1", "roles": ["user"]},
        )
    )

    assert result["task_id"] == "task-arxiv"
    assert result["reused_existing_task"] is False


def test_start_paper_translation_uses_arxiv_bridge_when_source_asset_path_is_missing(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "user-1", "roles": [], "is_admin": False}),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(
            0,
            result=_paper(source="arxiv", arxiv_id="2503.01010"),
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "source_archive": {
                    "id": "asset-source",
                    "paper_id": "paper-1",
                    "task_id": "task-stale",
                    "asset_type": "source_archive",
                    "file_path": "D:/tmp/missing-source-paper",
                    "file_name": "missing-source-paper",
                    "mime_type": "application/x-tex",
                    "created_at": "2026-03-18T00:00:00+00:00",
                }
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_start_arxiv_paper_translation",
        lambda **_kwargs: asyncio.sleep(0, result={"task_id": "task-arxiv", "status": "queued"}),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(0, result=_paper(id=paper_id, **payload)),
    )

    result = asyncio.run(
        paper_service.start_paper_translation(
            paper_id="paper-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
            current_user={"id": "user-1", "roles": ["user"]},
        )
    )

    assert result["task_id"] == "task-arxiv"
    assert result["reused_existing_task"] is False


def test_sync_task_assets_for_paper_stops_after_source_ready_intake(monkeypatch):
    captured = {}

    class _TaskManager:
        def get_task(self, task_id):
            assert task_id == "task-intake"
            return {
                "task_id": task_id,
                "status": "pending",
                "source_available": True,
                "source_path": "D:/tmp/source-paper",
            }

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(
        paper_service,
        "_create_source_asset",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={"id": "asset-source"},
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(
            0,
            result={"id": paper_id, **payload},
        ),
    )

    result = asyncio.run(
        paper_service._sync_task_assets_for_paper(
            paper_id="paper-1",
            task_id="task-intake",
            promote_to_official=False,
        )
    )

    assert result["done"] is True
    assert result["status"] == "pending"
    assert result["paper"]["trans_status"] == "not_started"
    assert result["paper"]["community_selected_asset_id"] == "asset-source"


def test_create_source_asset_is_noop_when_source_already_in_community_library(tmp_path, monkeypatch):
    monkeypatch.setattr(paper_service.settings, "base_dir", tmp_path)
    monkeypatch.setattr(paper_service.settings, "community_papers_dir", tmp_path / "community_papers")

    source_dir = tmp_path / "community_papers" / "paper-1" / "source" / "2508.18791"
    source_dir.mkdir(parents=True)
    tex_file = source_dir / "main.tex"
    tex_file.write_text("\\documentclass{article}")

    captured = {}

    async def _fake_upsert_latest_asset(**kwargs):
        captured.update(kwargs)
        return {
            "id": "asset-source",
            "paper_id": kwargs["paper_id"],
            "task_id": kwargs["task_id"],
            "asset_type": kwargs["asset_type"],
            "file_path": kwargs["file_path"],
            "file_name": kwargs["file_name"],
            "mime_type": "application/x-tex",
            "created_at": "2026-03-18T00:00:00+00:00",
        }

    monkeypatch.setattr(paper_service, "_upsert_latest_asset", _fake_upsert_latest_asset)

    asset = asyncio.run(
        paper_service._create_source_asset(
            paper_id="paper-1",
            task_id="task-translate",
            source_path=str(source_dir),
        )
    )

    assert asset["id"] == "asset-source"
    assert source_dir.is_dir()
    assert tex_file.exists()
    assert captured["file_path"] == "community_papers/paper-1/source/2508.18791.zip"


def test_detail_returns_public_asset_map_without_file_paths(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=_paper(community_selected_asset_id="asset-preview")),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_map_for_paper",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "source_archive": {
                    "id": "asset-source",
                    "task_id": "task-0",
                    "asset_type": "source_archive",
                    "file_path": "D:/secret/source.zip",
                    "file_name": "source.zip",
                    "mime_type": "application/zip",
                    "created_at": "2026-03-18T00:00:00+00:00",
                },
                "translated_pdf": {
                    "id": "asset-pdf",
                    "task_id": "task-1",
                    "asset_type": "translated_pdf",
                    "file_path": "D:/secret/translated.pdf",
                    "file_name": "translated.pdf",
                    "mime_type": "application/pdf",
                    "created_at": "2026-03-18T02:00:00+00:00",
                },
                "preview_html": {
                    "id": "asset-preview",
                    "task_id": "task-1",
                    "asset_type": "preview_html",
                    "file_path": "D:/secret/preview.html",
                    "file_name": "preview.html",
                    "mime_type": "text/html",
                    "created_at": "2026-03-18T02:05:00+00:00",
                },
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_viewer_state",
        lambda paper_ids, user_id=None: asyncio.sleep(
            0,
            result={paper_ids[0]: {"liked": False, "favorited": False}},
        ),
    )

    result = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper-1"))

    assert result["paper"]["latest_asset"]["asset_type"] == "preview_html"
    assert result["paper"]["assets"]["preview_html"]["file_name"] == "preview.html"
    assert "file_path" not in result["paper"]["assets"]["preview_html"]


def test_start_paper_translation_ignores_unverified_bearer_token_without_verified_user(monkeypatch, tmp_path):
    created = {}
    source_dir = tmp_path / "source-paper"
    source_dir.mkdir()
    monkeypatch.setattr(paper_service.asyncio, "create_task", lambda coro: coro.close())
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
                "source_archive": {
                    "id": "asset-source",
                    "paper_id": "paper-1",
                    "task_id": None,
                    "asset_type": "source_archive",
                    "file_path": str(source_dir),
                    "file_name": "source-paper",
                    "mime_type": "application/x-tex",
                    "created_at": "2026-03-18T00:00:00+00:00",
                }
            },
        ),
    )

    class _TaskManager:
        def create_task(self, **kwargs):
            created["create_task"] = kwargs
            return "task-guest"

        def update_task(self, task_id, **kwargs):
            created["update_task"] = (task_id, kwargs)

        def persist_task_if_needed(self, task_id):
            created["persist_task"] = task_id
            return True

        def get_task(self, task_id):
            return {
                "task_id": task_id,
                "source_available": True,
                "status": "pending",
                "source_path": str(source_dir),
                "arxiv_id": None,
            }

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(
        paper_service,
        "_enqueue_existing_task_translation",
        lambda **kwargs: asyncio.sleep(0, result={"task_id": kwargs["task_id"], "status": "queued"}),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(0, result=_paper(id=paper_id, **payload)),
    )

    result = asyncio.run(
        paper_service.start_paper_translation(
            paper_id="paper-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=SimpleNamespace(credentials=_jwt_for("forged-user")),
            current_user=None,
        )
    )

    assert created["create_task"]["user_id"] is None
    assert result["task_id"] == "task-guest"
