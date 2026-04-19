import asyncio

from backend.app.services import paper_service


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
