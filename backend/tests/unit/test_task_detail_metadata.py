import json
import os
import asyncio
from datetime import datetime

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import task as task_route
from backend.app.services.latex.utils import DownloadProgressCallback
from backend.app.services.task_detail import infer_task_detail
from backend.app.services.task_manager import TaskManager


def _make_task_manager(monkeypatch) -> TaskManager:
    return TaskManager()


def test_update_task_infers_translation_detail(monkeypatch):
    task_manager = _make_task_manager(monkeypatch)
    task_id = task_manager.create_task(source_type="upload")

    task_manager.update_task(
        task_id,
        status="processing",
        stage="translating",
        progress=42,
        message="Translated 3/10",
    )

    task = task_manager.get_task(task_id)
    assert task["detail_code"] == "translation_running"
    assert task["detail_params"] == {"current": 3, "total": 10}


def test_infer_task_detail_detects_rate_limit_retry():
    detail_code, detail_params = infer_task_detail(
        status="processing",
        stage="translating",
        message="API rate limited, waiting 12s before retry",
        progress=60,
    )

    assert detail_code == "task_rate_limited_retrying"
    assert detail_params == {"retry_in_seconds": 12}


def test_download_progress_callback_emits_structured_detail():
    captured = []

    class StubTaskManager:
        def update_task(self, **kwargs):
            captured.append(kwargs)

    callback = DownloadProgressCallback(
        task_manager=StubTaskManager(),
        task_id="task-download-test",
        stage="downloading_pdf",
    )

    callback.update(50, 100)

    assert captured[-1]["stage"] == "downloading_pdf"
    assert captured[-1]["detail_code"] == "download_pdf_progress"
    assert captured[-1]["detail_params"] == {"percent": 50}


def test_task_routes_expose_detail_fields(monkeypatch):
    fake_task = {
        "task_id": "task-route-test",
        "status": "completed",
        "progress": 100,
        "stage": "done",
        "message": "done",
        "detail_code": "compile_complete",
        "detail_params": None,
        "error": None,
        "warnings": None,
        "failure_reason_code": None,
        "failure_class": None,
        "guard_phase": None,
        "replay_bundle_ref": None,
        "evidence_chain_broken": False,
        "source_available": True,
        "created_at": "2026-03-16T00:00:00",
        "completed_at": "2026-03-16T00:10:00",
        "advanced_config": None,
    }

    class FakeTaskManager:
        def get_task(self, task_id):
            return fake_task if task_id == fake_task["task_id"] else None

        def get_all_tasks(self):
            return {fake_task["task_id"]: fake_task}

        def delete_task(self, task_id):
            return task_id == fake_task["task_id"]

    monkeypatch.setattr(task_route, "task_manager", FakeTaskManager())

    payload = asyncio.run(task_route.get_task_status(fake_task["task_id"])).model_dump()
    assert payload["detail_code"] == "compile_complete"
    assert payload["detail_params"] is None

    stream_response = asyncio.run(task_route.stream_task_status(fake_task["task_id"]))

    async def _collect_stream(response):
        parts = []
        async for chunk in response.body_iterator:
            parts.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
        return "".join(parts)

    body = asyncio.run(_collect_stream(stream_response))

    update_line = next(
        line for line in body.splitlines() if line.startswith("data: ") and '"type": "update"' in line
    )
    update_payload = json.loads(update_line.removeprefix("data: "))
    assert update_payload["detail_code"] == "compile_complete"
    assert update_payload["stage"] == "done"


def test_task_routes_expose_persist_failed_field(monkeypatch):
    fake_task = {
        "task_id": "task-route-persist-failed",
        "status": "failed",
        "progress": 100,
        "stage": "done",
        "message": "done",
        "detail_code": None,
        "detail_params": None,
        "error": None,
        "warnings": None,
        "failure_reason_code": None,
        "failure_class": None,
        "guard_phase": None,
        "replay_bundle_ref": None,
        "evidence_chain_broken": False,
        "source_available": True,
        "created_at": "2026-03-16T00:00:00",
        "completed_at": "2026-03-16T00:10:00",
        "advanced_config": None,
        "persist_failed": True,
    }

    class FakeTaskManager:
        def get_task(self, task_id):
            return fake_task if task_id == fake_task["task_id"] else None

        def delete_task_full(self, task_id):
            return {"deleted_dirs": [], "errors": []}

    monkeypatch.setattr(task_route, "task_manager", FakeTaskManager())

    payload = asyncio.run(
        task_route.get_task_status(
            fake_task["task_id"],
            current_user=None,
        )
    ).model_dump()
    assert payload["persist_failed"] is True


def test_task_routes_normalize_recovered_datetime_timestamps(monkeypatch):
    fake_task = {
        "task_id": "task-route-datetime-recovered",
        "status": "queued",
        "progress": 100,
        "stage": "downloading",
        "message": "Task queued, waiting for available slot",
        "detail_code": "task_queued",
        "detail_params": None,
        "error": None,
        "warnings": None,
        "failure_reason_code": None,
        "failure_class": None,
        "guard_phase": None,
        "replay_bundle_ref": None,
        "evidence_chain_broken": False,
        "source_available": True,
        "created_at": datetime(2026, 4, 19, 16, 5, 0),
        "completed_at": None,
        "advanced_config": None,
        "persist_failed": False,
    }

    class FakeTaskManager:
        def get_task(self, task_id):
            return fake_task if task_id == fake_task["task_id"] else None

    monkeypatch.setattr(task_route, "task_manager", FakeTaskManager())

    payload = asyncio.run(
        task_route.get_task_status(
            fake_task["task_id"],
            current_user=None,
        )
    ).model_dump()

    assert payload["created_at"] == "2026-04-19T16:05:00"


def test_authenticated_task_requires_matching_owner(monkeypatch):
    fake_task = {
        "task_id": "task-auth-owned",
        "status": "completed",
        "progress": 100,
        "stage": "done",
        "message": "done",
        "detail_code": None,
        "detail_params": None,
        "error": None,
        "warnings": None,
        "failure_reason_code": None,
        "failure_class": None,
        "guard_phase": None,
        "replay_bundle_ref": None,
        "evidence_chain_broken": False,
        "source_available": True,
        "created_at": "2026-03-16T00:00:00",
        "completed_at": "2026-03-16T00:10:00",
        "advanced_config": None,
        "user_id": "owner-1",
    }

    class FakeTaskManager:
        def get_task(self, task_id):
            return fake_task if task_id == fake_task["task_id"] else None

    monkeypatch.setattr(task_route, "task_manager", FakeTaskManager())

    try:
        asyncio.run(task_route.get_task_status(fake_task["task_id"], current_user=None))
        raise AssertionError("expected unauthorized")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 401

    owned = asyncio.run(
        task_route.get_task_status(
            fake_task["task_id"],
            current_user={"id": "owner-1", "roles": ["user"]},
        )
    )
    assert owned.task_id == fake_task["task_id"]

