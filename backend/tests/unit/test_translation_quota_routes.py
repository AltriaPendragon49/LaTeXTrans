import asyncio
import io
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import UploadFile

from backend.app.api.routes import upload as upload_route
from backend.app.api.routes import translate as translate_route
from backend.app.api.routes.translate import BatchTranslateRequest, TranslateRequest
from backend.app.models.config_models import LatexValidation
from backend.app.services.translation_quota_service import (
    DailyQuotaExceededError,
    LatexQuotaSnapshot,
)


def _quota_snapshot(*, used: int, remaining: int) -> LatexQuotaSnapshot:
    return LatexQuotaSnapshot(
        limit=3,
        used=used,
        remaining=remaining,
        quota_date="2026-05-06",
        reset_timezone="Asia/Shanghai",
    )


class _TaskManager:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.updated: list[tuple[str, dict[str, object]]] = []
        self.tasks: dict[str, dict[str, object]] = {}

    def get_task(self, task_id):
        return self.tasks.get(task_id) or {
            "task_id": task_id,
            "status": "pending",
            "source_available": True,
            "source_path": "data/uploads/task-1",
            "arxiv_id": "1709.01015",
        }

    def update_task(self, task_id, **kwargs):
        self.updated.append((task_id, kwargs))
        self.tasks.setdefault(task_id, {"task_id": task_id}).update(kwargs)
        return True

    def persist_task_if_needed(self, _task_id):
        return True

    def create_task(self, **kwargs):
        self.created.append(kwargs)
        task_id = f"task-{len(self.created)}"
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "source_available": False,
            "source_path": None,
            "arxiv_id": kwargs.get("arxiv_id"),
            "source_type": kwargs.get("source_type"),
            "user_id": kwargs.get("user_id"),
        }
        return task_id


class _Queue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[object, ...]] = []

    def get_user_active_count(self, _user_id):
        return 0

    async def enqueue(self, *args, **kwargs):
        self.enqueued.append((*args, kwargs))


class _QuotaService:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.reserved: list[tuple[str, int]] = []
        self.released: list[tuple[str, int]] = []

    def reserve_latex_translation(self, *, user_id: str, requested_count: int):
        if self.fail:
            raise DailyQuotaExceededError(
                snapshot=_quota_snapshot(used=3, remaining=0),
                requested_count=requested_count,
            )
        self.reserved.append((user_id, requested_count))
        return _quota_snapshot(used=requested_count, remaining=3 - requested_count)

    def release_latex_translation(self, *, user_id: str, count: int):
        self.released.append((user_id, count))
        return _quota_snapshot(used=0, remaining=3)


async def _fake_build_llm_config_async(*args, **kwargs):
    return {"api_key": "demo-key"}


async def _fake_persist_task_config_hash(*args, **kwargs):
    return True


def _upload_file(filename: str) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(b"\\documentclass{article}\\begin{document}Hi\\end{document}"),
    )


def _valid_latex_validation() -> LatexValidation:
    return LatexValidation(is_valid=True, main_file="main.tex", tex_files=["main.tex"])


def test_start_translation_reserves_one_daily_latex_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    quota_service = _QuotaService()
    queue = _Queue()

    monkeypatch.setattr(translate_route, "task_manager", _TaskManager())
    monkeypatch.setattr(translate_route, "get_task_queue", lambda: queue)
    monkeypatch.setattr(translate_route, "build_llm_config_async", _fake_build_llm_config_async)
    monkeypatch.setattr(translate_route, "persist_task_config_hash", _fake_persist_task_config_hash)
    monkeypatch.setattr(translate_route, "get_translation_quota_service", lambda: quota_service)

    response = asyncio.run(
        translate_route.start_translation(
            task_id="task-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=SimpleNamespace(credentials="local-token"),
            current_user={"id": "usr_123"},
        )
    )

    assert response.task_id == "task-1"
    assert quota_service.reserved == [("usr_123", 1)]
    assert quota_service.released == []
    assert queue.enqueued


def test_start_translation_returns_stable_quota_exceeded_error(monkeypatch: pytest.MonkeyPatch) -> None:
    quota_service = _QuotaService(fail=True)
    task_manager = _TaskManager()

    monkeypatch.setattr(translate_route, "task_manager", task_manager)
    monkeypatch.setattr(translate_route, "get_task_queue", lambda: _Queue())
    monkeypatch.setattr(translate_route, "get_translation_quota_service", lambda: quota_service)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            translate_route.start_translation(
                task_id="task-1",
                request=TranslateRequest(source_language="en", target_language="zh"),
                credentials=SimpleNamespace(credentials="local-token"),
                current_user={"id": "usr_123"},
            )
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == {
        "code": "DAILY_LATEX_QUOTA_EXCEEDED",
        "message": "Daily LaTeX translation quota exceeded.",
        "requested_count": 1,
        "limit": 3,
        "used": 3,
        "remaining": 0,
        "quota_date": "2026-05-06",
        "reset_timezone": "Asia/Shanghai",
    }
    assert task_manager.updated == []


def test_start_translation_releases_quota_when_preacceptance_enqueue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    quota_service = _QuotaService()

    async def _raising_build_llm_config_async(*args, **kwargs):
        raise RuntimeError("preacceptance failure")

    monkeypatch.setattr(translate_route, "task_manager", _TaskManager())
    monkeypatch.setattr(translate_route, "get_task_queue", lambda: _Queue())
    monkeypatch.setattr(translate_route, "build_llm_config_async", _raising_build_llm_config_async)
    monkeypatch.setattr(translate_route, "persist_task_config_hash", _fake_persist_task_config_hash)
    monkeypatch.setattr(translate_route, "get_translation_quota_service", lambda: quota_service)

    with pytest.raises(RuntimeError, match="preacceptance failure"):
        asyncio.run(
            translate_route.start_translation(
                task_id="task-1",
                request=TranslateRequest(source_language="en", target_language="zh"),
                credentials=SimpleNamespace(credentials="local-token"),
                current_user={"id": "usr_123"},
            )
        )

    assert quota_service.reserved == [("usr_123", 1)]
    assert quota_service.released == [("usr_123", 1)]


def test_batch_translate_rejects_whole_batch_before_task_creation_when_daily_quota_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    quota_service = _QuotaService(fail=True)
    task_manager = _TaskManager()

    monkeypatch.setattr(translate_route, "task_manager", task_manager)
    monkeypatch.setattr(translate_route, "get_task_queue", lambda: _Queue())
    monkeypatch.setattr(translate_route, "extract_arxiv_ids", lambda values: values)
    monkeypatch.setattr(translate_route, "get_translation_quota_service", lambda: quota_service)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            translate_route.batch_translate(
                BatchTranslateRequest(arxiv_ids=["1709.01015", "1709.01016"]),
                credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="local-token"),
                current_user={"id": "usr_123"},
            )
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["requested_count"] == 2
    assert exc_info.value.detail["remaining"] == 0
    assert task_manager.created == []


def test_batch_upload_translate_rejects_before_task_creation_when_daily_quota_exceeded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    quota_service = _QuotaService(fail=True)
    task_manager = _TaskManager()

    monkeypatch.setattr(upload_route.settings, "uploads_dir", tmp_path)
    monkeypatch.setattr(upload_route, "task_manager", task_manager)
    monkeypatch.setattr(translate_route, "task_manager", task_manager)
    monkeypatch.setattr(translate_route, "get_task_queue", lambda: _Queue())
    monkeypatch.setattr(translate_route, "get_translation_quota_service", lambda: quota_service)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            upload_route.batch_upload_translate(
                files=[_upload_file("paper-1.tex"), _upload_file("paper-2.tex")],
                source_language="en",
                target_language="zh",
                advanced_config=None,
                credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="local-token"),
                current_user={"id": "usr_123"},
            )
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["requested_count"] == 2
    assert task_manager.created == []


def test_batch_upload_translate_reserves_full_file_count_once_and_enqueues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    quota_service = _QuotaService()
    queue = _Queue()
    task_manager = _TaskManager()

    monkeypatch.setattr(upload_route.settings, "uploads_dir", tmp_path)
    monkeypatch.setattr(upload_route, "task_manager", task_manager)
    monkeypatch.setattr(upload_route, "validate_latex_directory", lambda _path: _valid_latex_validation())
    monkeypatch.setattr(translate_route, "task_manager", task_manager)
    monkeypatch.setattr(translate_route, "get_task_queue", lambda: queue)
    monkeypatch.setattr(translate_route, "build_llm_config_async", _fake_build_llm_config_async)
    monkeypatch.setattr(translate_route, "persist_task_config_hash", _fake_persist_task_config_hash)
    monkeypatch.setattr(translate_route, "get_translation_quota_service", lambda: quota_service)

    response = asyncio.run(
        upload_route.batch_upload_translate(
            files=[_upload_file("paper-1.tex"), _upload_file("paper-2.tex")],
            source_language="en",
            target_language="zh",
            advanced_config=None,
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="local-token"),
            current_user={"id": "usr_123"},
        )
    )

    assert response.queued_count == 2
    assert response.task_ids == ["task-1", "task-2"]
    assert quota_service.reserved == [("usr_123", 2)]
    assert quota_service.released == []
    assert len(queue.enqueued) == 2


def test_batch_upload_translate_releases_unaccepted_file_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    quota_service = _QuotaService()
    queue = _Queue()
    task_manager = _TaskManager()
    validations = [
        _valid_latex_validation(),
        LatexValidation(is_valid=False, errors=["missing main tex"]),
    ]

    monkeypatch.setattr(upload_route.settings, "uploads_dir", tmp_path)
    monkeypatch.setattr(upload_route, "task_manager", task_manager)
    monkeypatch.setattr(upload_route, "validate_latex_directory", lambda _path: validations.pop(0))
    monkeypatch.setattr(translate_route, "task_manager", task_manager)
    monkeypatch.setattr(translate_route, "get_task_queue", lambda: queue)
    monkeypatch.setattr(translate_route, "build_llm_config_async", _fake_build_llm_config_async)
    monkeypatch.setattr(translate_route, "persist_task_config_hash", _fake_persist_task_config_hash)
    monkeypatch.setattr(translate_route, "get_translation_quota_service", lambda: quota_service)

    response = asyncio.run(
        upload_route.batch_upload_translate(
            files=[_upload_file("paper-1.tex"), _upload_file("paper-2.tex")],
            source_language="en",
            target_language="zh",
            advanced_config=None,
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="local-token"),
            current_user={"id": "usr_123"},
        )
    )

    assert response.queued_count == 1
    assert response.task_ids == ["task-1"]
    assert quota_service.reserved == [("usr_123", 2)]
    assert quota_service.released == [("usr_123", 1)]
    assert len(queue.enqueued) == 1
