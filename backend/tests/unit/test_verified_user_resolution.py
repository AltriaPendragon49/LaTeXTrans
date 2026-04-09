import asyncio
import base64
import json
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.routes import arxiv as arxiv_route
from backend.app.api.routes import translate as translate_route
from backend.app.api.routes import upload as upload_route
from backend.app.api.routes.translate import BatchTranslateRequest, TranslateRequest
from backend.app.core.auth import resolve_current_user_id


def _jwt_for(user_id: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": user_id}).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    return f"header.{payload}.sig"


def test_resolve_current_user_id_ignores_unverified_bearer_token() -> None:
    credentials = SimpleNamespace(credentials=_jwt_for("usr_forged"))

    assert resolve_current_user_id(None, credentials) is None


def test_batch_translate_rejects_credentials_without_verified_user(monkeypatch) -> None:
    class _TaskManager:
        def create_task(self, **_kwargs):
            raise AssertionError("batch translation should not create tasks without a verified user")

    monkeypatch.setattr(translate_route, "task_manager", _TaskManager())

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            translate_route.batch_translate(
                BatchTranslateRequest(arxiv_ids=["2508.18791"]),
                credentials=HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials=_jwt_for("usr_forged"),
                ),
                current_user=None,
            )
        )

    assert exc_info.value.status_code == 401


def test_start_translation_treats_unverified_bearer_token_as_guest(monkeypatch) -> None:
    persisted_hashes: list[tuple[str, str]] = []
    scheduled: list[tuple[str, str | None]] = []

    class _TaskManager:
        def get_task(self, task_id):
            return {
                "task_id": task_id,
                "status": "pending",
                "source_available": True,
                "source_path": "data/uploads/task-guest",
                "arxiv_id": None,
            }

        def update_task(self, *args, **kwargs):
            return True

        def persist_task_if_needed(self, _task_id):
            return True

    class _Queue:
        def __init__(self) -> None:
            self.user_calls: list[str | None] = []

        def get_user_active_count(self, user_id):
            self.user_calls.append(user_id)
            return 0

        async def enqueue(self, *args, **kwargs):
            return None

    queue = _Queue()

    async def _build_llm_config_async(*args, **kwargs):
        return {"api_key": "demo-key"}

    async def _persist_task_config_hash(task_id: str, config_hash: str) -> bool:
        persisted_hashes.append((task_id, config_hash))
        return True

    def _schedule_watch(task_id: str, user_id: str | None) -> None:
        if user_id is None:
            return
        scheduled.append((task_id, user_id))

    monkeypatch.setattr(translate_route, "task_manager", _TaskManager())
    monkeypatch.setattr(translate_route, "get_task_queue", lambda: queue)
    monkeypatch.setattr(translate_route, "build_llm_config_async", _build_llm_config_async)
    monkeypatch.setattr(translate_route, "persist_task_config_hash", _persist_task_config_hash)
    monkeypatch.setattr(translate_route, "_schedule_community_publish_watch", _schedule_watch)

    response = asyncio.run(
        translate_route.start_translation(
            task_id="task-guest",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=SimpleNamespace(credentials=_jwt_for("usr_forged")),
            current_user=None,
        )
    )

    assert response.task_id == "task-guest"
    assert queue.user_calls == []
    assert persisted_hashes == []
    assert scheduled == []


def test_upload_file_ignores_unverified_bearer_token_for_task_owner(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class _TaskManager:
        def create_task(self, **kwargs):
            captured["create_task"] = kwargs
            return "task-upload-1"

        def update_task(self, *args, **kwargs):
            return True

        def get_task(self, _task_id):
            return None

    class _Validation:
        is_valid = True
        main_file = "paper.tex"
        tex_files = ["paper.tex"]
        warnings = []
        errors = []

        def model_dump(self):
            return {
                "is_valid": True,
                "main_file": "paper.tex",
                "tex_files": ["paper.tex"],
                "warnings": [],
                "errors": [],
            }

    monkeypatch.setattr(upload_route, "task_manager", _TaskManager())
    monkeypatch.setattr(upload_route.settings, "uploads_dir", tmp_path / "uploads")
    monkeypatch.setattr(upload_route.settings, "allowed_extensions", {".tex"})
    monkeypatch.setattr(upload_route, "validate_latex_directory", lambda _path: _Validation())

    response = asyncio.run(
        upload_route.upload_file(
            file=UploadFile(filename="paper.tex", file=BytesIO(b"\\documentclass{article}\n")),
            credentials=SimpleNamespace(credentials=_jwt_for("usr_forged")),
            current_user=None,
        )
    )

    assert response.task_id == "task-upload-1"
    assert captured["create_task"]["user_id"] is None


def test_download_arxiv_ignores_unverified_bearer_token_for_task_owner(monkeypatch) -> None:
    captured: dict[str, object] = {}
    scheduled = []

    class _TaskManager:
        def create_task(self, **kwargs):
            captured["create_task"] = kwargs
            return "task-arxiv-1"

        def update_task(self, *args, **kwargs):
            return True

    def _fake_create_task(coro):
        scheduled.append(coro)
        coro.close()
        return None

    monkeypatch.setattr(arxiv_route, "task_manager", _TaskManager())
    monkeypatch.setattr(arxiv_route, "extract_arxiv_ids", lambda values: values)
    monkeypatch.setattr(arxiv_route.asyncio, "create_task", _fake_create_task)

    response = asyncio.run(
        arxiv_route.download_arxiv(
            request=arxiv_route.ArxivRequest(arxiv_id="2508.18791"),
            credentials=SimpleNamespace(credentials=_jwt_for("usr_forged")),
            current_user=None,
        )
    )

    assert response.task_id == "task-arxiv-1"
    assert captured["create_task"]["user_id"] is None
