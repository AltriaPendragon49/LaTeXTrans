import asyncio

import httpx

from backend.app.api.routes import task as task_route
from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def test_task_status_exposes_terminal_reason(monkeypatch) -> None:
    monkeypatch.setattr(
        task_route.task_manager,
        "get_task",
        lambda _task_id: {
            "task_id": "task-1",
            "user_id": None,
            "status": "failed",
            "progress": 100,
            "stage": "done",
            "message": "Execution timeout",
            "detail_code": "task_execution_timeout",
            "error": "Execution timeout",
            "warnings": None,
            "failure_reason_code": None,
            "failure_class": None,
            "guard_phase": None,
            "replay_bundle_ref": None,
            "evidence_chain_broken": False,
            "source_available": True,
            "created_at": "2026-04-21T00:00:00Z",
            "completed_at": "2026-04-21T00:30:00Z",
            "advanced_config": None,
            "persist_failed": False,
        },
    )

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/task/task-1")

    response = asyncio.run(_call())

    assert response.status_code == 200
    assert response.json()["terminal_reason"] == "task_execution_timeout"
