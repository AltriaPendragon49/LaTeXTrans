import asyncio

from backend.app.services import paper_service


def test_wait_for_task_terminal_state_ignores_persistent_store_errors(monkeypatch):
    sleep_calls: list[int] = []
    get_task_calls = {"count": 0}

    def _fake_get_task(_task_id: str):
        get_task_calls["count"] += 1
        if get_task_calls["count"] < 3:
            return None
        return {"task_id": "task-1", "status": "completed"}

    async def _fake_sleep(_seconds: int):
        sleep_calls.append(1)

    async def _fake_run_db_blocking(_operation):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(paper_service.task_manager, "get_task", _fake_get_task)
    monkeypatch.setattr(paper_service.asyncio, "sleep", _fake_sleep)
    monkeypatch.setattr(paper_service, "run_db_blocking", _fake_run_db_blocking)

    result = asyncio.run(paper_service._wait_for_task_terminal_state("task-1"))

    assert result["status"] == "completed"
    assert len(sleep_calls) == 2
