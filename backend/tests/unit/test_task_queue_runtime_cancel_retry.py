import asyncio

import pytest

import backend.app.services.task_manager as task_manager_module
from backend.app.services.task_manager import TaskQueue, set_runtime_shutting_down


@pytest.mark.asyncio
async def test_task_queue_retries_unexpected_cancelled_error(monkeypatch):
    updates = []
    attempts = {"count": 0}
    finished = asyncio.Event()

    monkeypatch.setattr(
        task_manager_module.task_manager,
        "update_task",
        lambda task_id, **kwargs: updates.append((task_id, kwargs)) or True,
        raising=False,
    )
    monkeypatch.setattr(
        task_manager_module.task_manager,
        "is_cancelled",
        lambda _task_id: False,
        raising=False,
    )

    async def flaky_coro():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise asyncio.CancelledError()
        finished.set()

    queue = TaskQueue(max_concurrent=1)
    await queue.initialize()
    set_runtime_shutting_down(False)

    await queue.enqueue(
        task_id="retry-after-cancel-task",
        coro_factory=lambda: flaky_coro(),
        user_id=None,
        token_hash="runtime-cancel-token",
    )

    await asyncio.wait_for(finished.wait(), timeout=5)
    await asyncio.sleep(0.1)

    assert attempts["count"] == 2
    assert any(
        payload.get("detail_code") == "task_retry_after_cancel"
        for _task_id, payload in updates
    )
    assert "retry-after-cancel-task" not in queue._active_tasks

    set_runtime_shutting_down(True)
    worker = queue._workers["runtime-cancel-token"]
    worker.cancel()
    await asyncio.wait_for(worker, timeout=1)
    set_runtime_shutting_down(False)


@pytest.mark.asyncio
async def test_task_queue_worker_continues_after_unexpected_worker_cancel(monkeypatch):
    monkeypatch.setattr(
        task_manager_module.task_manager,
        "update_task",
        lambda task_id=None, **_kwargs: True,
        raising=False,
    )
    monkeypatch.setattr(
        task_manager_module.task_manager,
        "is_cancelled",
        lambda _task_id: False,
        raising=False,
    )

    first_started = asyncio.Event()
    allow_first_finish = asyncio.Event()
    second_finished = asyncio.Event()
    execution_order = []

    async def first_coro():
        first_started.set()
        await allow_first_finish.wait()
        execution_order.append("first")

    async def second_coro():
        execution_order.append("second")
        second_finished.set()

    queue = TaskQueue(max_concurrent=1)
    await queue.initialize()
    set_runtime_shutting_down(False)

    token_hash = "worker-cancel-token"
    await queue.enqueue(
        task_id="worker-cancel-task-1",
        coro_factory=lambda: first_coro(),
        user_id=None,
        token_hash=token_hash,
    )
    await asyncio.wait_for(first_started.wait(), timeout=2)

    worker = queue._workers[token_hash]
    worker.cancel()

    allow_first_finish.set()
    await asyncio.sleep(0.1)

    await queue.enqueue(
        task_id="worker-cancel-task-2",
        coro_factory=lambda: second_coro(),
        user_id=None,
        token_hash=token_hash,
    )

    await asyncio.wait_for(second_finished.wait(), timeout=5)
    assert execution_order == ["first", "second"]

    set_runtime_shutting_down(True)
    queue._workers[token_hash].cancel()
    await asyncio.wait_for(queue._workers[token_hash], timeout=1)
    set_runtime_shutting_down(False)


@pytest.mark.asyncio
async def test_task_queue_respawns_after_unexpected_idle_worker_cancel(monkeypatch):
    monkeypatch.setattr(
        task_manager_module.task_manager,
        "update_task",
        lambda task_id=None, **_kwargs: True,
        raising=False,
    )
    monkeypatch.setattr(
        task_manager_module.task_manager,
        "is_cancelled",
        lambda _task_id: False,
        raising=False,
    )

    first_finished = asyncio.Event()
    second_finished = asyncio.Event()

    async def first_coro():
        first_finished.set()

    async def second_coro():
        second_finished.set()

    queue = TaskQueue(max_concurrent=1)
    await queue.initialize()
    set_runtime_shutting_down(False)

    token_hash = "idle-worker-cancel-token"
    await queue.enqueue(
        task_id="idle-cancel-task-1",
        coro_factory=lambda: first_coro(),
        user_id=None,
        token_hash=token_hash,
    )
    await asyncio.wait_for(first_finished.wait(), timeout=2)
    await asyncio.sleep(0.1)

    cancelled_worker = queue._workers[token_hash]
    cancelled_worker.cancel()
    await asyncio.sleep(0.1)

    replacement_worker = queue._workers[token_hash]
    assert replacement_worker is not cancelled_worker
    assert not replacement_worker.done()

    await queue.enqueue(
        task_id="idle-cancel-task-2",
        coro_factory=lambda: second_coro(),
        user_id=None,
        token_hash=token_hash,
    )
    await asyncio.wait_for(second_finished.wait(), timeout=5)

    set_runtime_shutting_down(True)
    queue._workers[token_hash].cancel()
    await asyncio.wait_for(queue._workers[token_hash], timeout=1)
    set_runtime_shutting_down(False)
