import asyncio
from datetime import datetime

import httpx
import pytest

from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


class _FakeTranslationTaskRepository:
    def __init__(self) -> None:
        self.deleted_task_ids: list[tuple[str, str]] = []
        self.tasks = {
            "task-local-1": {
                "task_id": "task-local-1",
                "user_id": "usr_local_1",
                "source_type": "arxiv",
                "arxiv_id": "2501.00001",
                "translation_mode": "full",
                "status": "completed",
                "progress": 100,
                "created_at": "2026-04-09T00:00:00",
                "completed_at": "2026-04-09T00:10:00",
                "source_language": "en",
                "target_language": "zh",
                "compile_strategy": "auto",
                "translation_model": "demo-model",
                "generate_glossary": True,
                "use_author_api": True,
                "formatting": {"font_size": 12},
                "stage": "done",
                "message": "finished",
                "error": None,
                "source_path": "data/uploads/task-local-1",
                "output_path": "data/outputs/task-local-1",
            }
        }

    def list_tasks_for_user(self, user_id: str, *, page: int, page_size: int, status_filter: str | None):
        assert user_id == "usr_local_1"
        assert page == 1
        assert page_size == 10
        assert status_filter is None
        return [self.tasks["task-local-1"]], 1

    def get_task_for_user(self, user_id: str, task_id: str):
        assert user_id == "usr_local_1"
        task = self.tasks.get(task_id)
        if task and task["user_id"] == user_id:
            return task
        return None

    def delete_task_for_user(self, user_id: str, task_id: str) -> bool:
        self.deleted_task_ids.append((user_id, task_id))
        return self.tasks.pop(task_id, None) is not None

    def update_task(self, task_id: str, updates: dict) -> bool:
        if task_id not in self.tasks:
            return False
        self.tasks[task_id].update(updates)
        return True


class _FakeTaskManager:
    def __init__(self) -> None:
        self.cancelled: list[str] = []
        self.deleted: list[str] = []

    def cancel_task(self, task_id: str) -> None:
        self.cancelled.append(task_id)

    def delete_task_full(self, task_id: str) -> dict:
        self.deleted.append(task_id)
        return {"success": True, "deleted_dirs": [f"data/outputs/{task_id}"], "errors": []}


def test_history_routes_use_local_current_user_and_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.api.routes import history as history_route
    from backend.app.services import task_manager as task_manager_module

    fake_repo = _FakeTranslationTaskRepository()
    fake_task_manager = _FakeTaskManager()

    monkeypatch.setattr(history_route, "get_translation_task_repository", lambda: fake_repo)
    monkeypatch.setattr(task_manager_module, "get_task_manager", lambda: fake_task_manager)
    app.dependency_overrides[history_route.require_current_user] = lambda: {"id": "usr_local_1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            list_response = await client.get("/api/history?page=1&page_size=10")
            detail_response = await client.get("/api/history/task-local-1")
            delete_response = await client.delete("/api/history/task-local-1")
            return list_response, detail_response, delete_response

    list_response, detail_response, delete_response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["tasks"][0]["task_id"] == "task-local-1"

    assert detail_response.status_code == 200
    assert detail_response.json()["task_id"] == "task-local-1"
    assert detail_response.json()["status"] == "completed"

    assert delete_response.status_code == 200
    assert delete_response.json()["task_id"] == "task-local-1"
    assert fake_repo.deleted_task_ids == [("usr_local_1", "task-local-1")]
    assert fake_task_manager.deleted == ["task-local-1"]


def test_task_detail_reconciles_non_terminal_local_status(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from backend.app.api.routes import history as history_route

    fake_repo = _FakeTranslationTaskRepository()
    fake_repo.tasks["task-local-1"]["status"] = "processing"
    fake_repo.tasks["task-local-1"]["progress"] = 42

    output_dir = tmp_path / "task-local-1"
    output_dir.mkdir(parents=True)
    (output_dir / "task_log.json").write_text('[{"event":"compilation_completed"}]', encoding="utf-8")
    fake_repo.tasks["task-local-1"]["output_path"] = str(output_dir)

    monkeypatch.setattr(history_route, "get_translation_task_repository", lambda: fake_repo)
    app.dependency_overrides[history_route.require_current_user] = lambda: {"id": "usr_local_1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/history/task-local-1")

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["progress"] == 100


def test_history_routes_serialize_datetime_completed_at(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.api.routes import history as history_route

    fake_repo = _FakeTranslationTaskRepository()
    fake_repo.tasks["task-local-1"]["completed_at"] = datetime(2026, 4, 9, 0, 10, 0)

    monkeypatch.setattr(history_route, "get_translation_task_repository", lambda: fake_repo)
    app.dependency_overrides[history_route.require_current_user] = lambda: {"id": "usr_local_1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            list_response = await client.get("/api/history?page=1&page_size=10")
            detail_response = await client.get("/api/history/task-local-1")
            return list_response, detail_response

    list_response, detail_response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json()["tasks"][0]["completed_at"] == "2026-04-09 00:10:00"

    assert detail_response.status_code == 200
    assert detail_response.json()["completed_at"] == "2026-04-09 00:10:00"
