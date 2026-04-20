import asyncio
import inspect

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
async def test_task_queue_does_not_retry_explicit_cancel_during_immediate_cleanup(monkeypatch):
    updates = []
    started = asyncio.Event()
    cancelled = asyncio.Event()
    attempts = {"count": 0}

    monkeypatch.setattr(
        task_manager_module.task_manager,
        "update_task",
        lambda task_id, **kwargs: updates.append((task_id, kwargs)) or True,
        raising=False,
    )

    queue = TaskQueue(max_concurrent=1)
    await queue.initialize()
    set_runtime_shutting_down(False)
    monkeypatch.setattr(task_manager_module, "task_queue", queue, raising=False)

    task_id = "explicit-cancel-task"
    task_manager_module.task_manager._tasks[task_id] = {
        "task_id": task_id,
        "status": "processing",
        "progress": 50,
        "message": "running",
    }
    task_manager_module.task_manager._cancelled_tasks.discard(task_id)

    async def long_running_coro():
        attempts["count"] += 1
        started.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    await queue.enqueue(
        task_id=task_id,
        coro_factory=lambda: long_running_coro(),
        user_id=None,
        token_hash="explicit-cancel-token",
    )

    await asyncio.wait_for(started.wait(), timeout=2)
    assert task_manager_module.task_manager.cancel_task(task_id) is True
    task_manager_module.task_manager.delete_task_full(task_id)
    await asyncio.wait_for(cancelled.wait(), timeout=2)
    await asyncio.sleep(0.2)

    assert attempts["count"] == 1
    assert not any(
        payload.get("detail_code") == "task_retry_after_cancel"
        for _task_id, payload in updates
    )
    assert task_id not in queue._active_tasks

    set_runtime_shutting_down(True)
    queue._workers["explicit-cancel-token"].cancel()
    await asyncio.wait_for(queue._workers["explicit-cancel-token"], timeout=1)
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


@pytest.mark.asyncio
async def test_task_queue_keeps_distinct_coro_factory_per_running_task(monkeypatch):
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

    original_create_task = asyncio.create_task
    run_gate = asyncio.Event()
    running_task_creations = {"count": 0}
    execution_order: list[str] = []
    both_finished = asyncio.Event()

    def _patched_create_task(coro, *args, **kwargs):
        code = getattr(coro, "cr_code", None)
        if inspect.iscoroutine(coro) and code and code.co_name == "_run_with_cancel_retry":
            running_task_creations["count"] += 1
            creation_index = running_task_creations["count"]

            async def _delayed():
                if creation_index == 1:
                    await run_gate.wait()
                result = await coro
                if len(execution_order) >= 2:
                    both_finished.set()
                return result

            task = original_create_task(_delayed(), *args, **kwargs)
            if creation_index >= 2:
                run_gate.set()
            return task
        return original_create_task(coro, *args, **kwargs)

    monkeypatch.setattr(task_manager_module.asyncio, "create_task", _patched_create_task)

    async def first_coro():
        execution_order.append("first")

    async def second_coro():
        execution_order.append("second")

    queue = TaskQueue(max_concurrent=2)
    await queue.initialize()
    set_runtime_shutting_down(False)

    token_hash = "distinct-coro-factory-token"
    await queue.enqueue(
        task_id="distinct-factory-task-1",
        coro_factory=lambda: first_coro(),
        user_id=None,
        token_hash=token_hash,
    )
    await queue.enqueue(
        task_id="distinct-factory-task-2",
        coro_factory=lambda: second_coro(),
        user_id=None,
        token_hash=token_hash,
    )

    await asyncio.wait_for(both_finished.wait(), timeout=5)
    await asyncio.sleep(0.1)

    assert execution_order == ["first", "second"]

    set_runtime_shutting_down(True)
    queue._workers[token_hash].cancel()
    await asyncio.wait_for(queue._workers[token_hash], timeout=1)
    set_runtime_shutting_down(False)
