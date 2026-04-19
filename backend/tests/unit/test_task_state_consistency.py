import asyncio

from backend.app.services.task_manager import TaskManager


def test_non_terminal_requeue_clears_completed_at():
    flush_calls = []

    tm = TaskManager()
    tm._persist_task_update = lambda tid, upd: flush_calls.append((tid, dict(upd)))

    task_id = tm.create_task(source_type="upload", user_id="user-1")
    tm.update_task(task_id, status="completed", message="done")
    tm._flusher.drain(timeout=2.0)

    assert tm.get_task(task_id)["completed_at"] is not None

    tm.update_task(task_id, status="queued", message="retrying")
    tm._flusher.drain(timeout=2.0)

    task = tm.get_task(task_id)
    assert task["status"] == "queued"
    assert task["completed_at"] is None
    assert any(
        payload.get("status") == "queued" and payload.get("completed_at") is None
        for _tid, payload in flush_calls
    )


def test_same_attempt_progress_callback_cannot_regress_terminal_state():
    tm = TaskManager()
    task_id = tm.create_task(source_type="upload", user_id="user-1")

    attempt_id = tm.begin_task_attempt(task_id)
    progress_callback = tm.create_progress_callback(task_id, attempt_id=attempt_id)

    tm.update_task(
        task_id,
        status="completed",
        progress=100,
        message="done",
        expected_attempt_id=attempt_id,
    )
    completed_at = tm.get_task(task_id)["completed_at"]

    progress_callback(42, "late stale update")

    task = tm.get_task(task_id)
    assert task["status"] == "completed"
    assert task["progress"] == 100
    assert task["message"] == "done"
    assert task["completed_at"] == completed_at


def test_recover_from_persistent_store_reconciles_non_terminal_completed_row(monkeypatch):
    updated = []

    class _MockRepository:
        def get_task(self, _task_id):
            return {
                "task_id": "task-inconsistent",
                "status": "processing",
                "progress": 73,
                "stage": "translating",
                "message": "still running",
                "error": None,
                "source_type": "upload",
                "source_path": "data/uploads/task-inconsistent",
                "output_path": "data/outputs/task-inconsistent",
                "translation_mode": "full",
                "compile_strategy": "auto",
                "translation_model": None,
                "generate_glossary": True,
                "use_author_api": True,
                "email_notification": False,
                "arxiv_id": None,
                "user_id": "user-test",
                "source_language": "en",
                "target_language": "zh",
                "created_at": "2026-01-01T00:00:00",
                "completed_at": "2026-01-01T00:01:00",
            }

        def update_task(self, task_id, updates):
            updated.append((task_id, dict(updates)))
            return True

    monkeypatch.setattr(
        "backend.app.services.task_manager.get_translation_task_repository",
        lambda: _MockRepository(),
    )

    tm = TaskManager()
    result = tm._recover_from_persistent_store("task-inconsistent")

    assert result is not None
    assert result["status"] == "failed"
    assert result["completed_at"] == "2026-01-01T00:01:00"
    assert any(
        task_id == "task-inconsistent"
        and payload.get("status") == "failed"
        and payload.get("detail_code") == "task_state_reconciled"
        for task_id, payload in updated
    )
