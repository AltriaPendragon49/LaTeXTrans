import asyncio

import httpx

from backend.app.api.routes import task as task_route
from backend.app.main import app
from backend.app.services import task_runtime_client


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


def test_delete_task_signals_worker_runtime_before_local_delete(monkeypatch) -> None:
    calls: list[tuple] = []

    monkeypatch.setattr(
        task_route.task_manager,
        "get_task",
        lambda _task_id: {
            "task_id": "task-delete-1",
            "user_id": None,
            "status": "processing",
            "progress": 50,
            "stage": "translating",
            "message": "running",
            "source_available": True,
            "created_at": "2026-04-27T00:00:00Z",
        },
    )
    monkeypatch.setattr(
        task_route,
        "request_worker_task_cancel",
        lambda task_id, **kwargs: _async_return(
            calls.append(("worker_cancel", task_id, kwargs)) or {"sent": True, "cancelled": True}
        ),
    )
    monkeypatch.setattr(
        task_route.task_manager,
        "cancel_task",
        lambda task_id, **kwargs: calls.append(("local_cancel", task_id, kwargs)) or True,
    )
    monkeypatch.setattr(
        task_route.task_manager,
        "delete_task_full",
        lambda task_id: calls.append(("delete_full", task_id)) or {"deleted_dirs": [], "errors": []},
    )

    async def _call():
        async with _make_client() as client:
            return await client.delete("/api/task/task-delete-1")

    response = asyncio.run(_call())

    assert response.status_code == 200
    assert response.json()["cancelled"] is True
    assert calls == [
        ("worker_cancel", "task-delete-1", {"terminal_reason": "task_deleted"}),
        ("local_cancel", "task-delete-1", {"terminal_reason": "task_deleted"}),
        ("delete_full", "task-delete-1"),
    ]


def test_internal_cancel_endpoint_requires_signed_runtime_request(monkeypatch) -> None:
    cancelled: list[tuple] = []
    timestamp = "1800000000"
    terminal_reason = "task_deleted"
    signature = task_runtime_client._sign_internal_request(
        action=task_runtime_client.INTERNAL_TASK_CANCEL_ACTION,
        task_id="task-internal-1",
        timestamp=timestamp,
        terminal_reason=terminal_reason,
    )

    monkeypatch.setattr(task_runtime_client.time, "time", lambda: int(timestamp))
    monkeypatch.setattr(
        task_route.task_manager,
        "cancel_task",
        lambda task_id, **kwargs: cancelled.append((task_id, kwargs)) or True,
    )

    async def _call(headers):
        async with _make_client() as client:
            return await client.post(
                "/api/internal/task/task-internal-1/cancel",
                params={"terminal_reason": terminal_reason},
                headers=headers,
            )

    unauthorized = asyncio.run(_call({}))
    response = asyncio.run(
        _call(
            {
                "x-latextrans-runtime-timestamp": timestamp,
                "x-latextrans-runtime-signature": signature,
            }
        )
    )

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.json()["cancelled"] is True
    assert cancelled == [("task-internal-1", {"terminal_reason": terminal_reason})]


async def _async_return(value):
    return value
