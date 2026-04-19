import asyncio

from backend.app.services import paper_service
from backend.app.services.task_manager import TaskManager


def test_wait_for_task_terminal_state_uses_persistent_terminal_fallback(monkeypatch):
    class _Repo:
        def get_task(self, _task_id: str):
            return {
                "task_id": "task-db-terminal",
                "status": "completed",
                "progress": 100,
                "message": "done",
                "error": None,
                "completed_at": "2026-04-19T10:00:00",
            }

    monkeypatch.setattr(paper_service.task_manager, "get_task", lambda _task_id: None)
    monkeypatch.setattr(paper_service, "_get_translation_task_repository", lambda: _Repo())

    result = asyncio.run(paper_service._wait_for_task_terminal_state("task-db-terminal"))

    assert result["status"] == "completed"
    assert result["completed_at"] == "2026-04-19T10:00:00"


def test_wait_for_task_terminal_state_updates_worker_runtime_cache_from_persistent_terminal_state(monkeypatch):
    task_id = "task-db-terminal-cache"
    tm = TaskManager()
    tm._tasks[task_id] = {
        "task_id": task_id,
        "status": "processing",
        "progress": 97,
        "stage": "compiling",
        "message": "Compiling PDF document",
        "error": None,
        "user_id": "user-1",
        "output_path": "data/outputs/task-db-terminal-cache",
    }

    class _Repo:
        def get_task(self, requested_task_id: str):
            assert requested_task_id == task_id
            return {
                "task_id": task_id,
                "status": "completed_with_warnings",
                "progress": 100,
                "stage": "done",
                "message": "Translation completed with compilation warnings",
                "error": None,
                "completed_at": "2026-04-19T10:00:00",
                "output_path": "data/outputs/task-db-terminal-cache",
                "user_id": "user-1",
            }

    async def _run_db_blocking(operation):
        return operation()

    monkeypatch.setattr(paper_service, "task_manager", tm)
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_settings",
        lambda: type("Settings", (), {"backend_runtime_role": "worker"})(),
    )
    monkeypatch.setattr(paper_service, "_get_translation_task_repository", lambda: _Repo())
    monkeypatch.setattr(paper_service, "run_db_blocking", _run_db_blocking)

    result = asyncio.run(paper_service._wait_for_task_terminal_state(task_id))

    assert result["status"] == "completed_with_warnings"
    cached = tm.get_task(task_id)
    assert cached is not None
    assert cached["status"] == "completed_with_warnings"
    assert cached["completed_at"] == "2026-04-19T10:00:00"
