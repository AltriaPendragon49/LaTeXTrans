import asyncio

import pytest

import backend.app.services.task_manager as task_manager_module
from backend.app.services.task_manager import TaskQueue, set_runtime_shutting_down


@pytest.mark.asyncio
async def test_task_queue_uses_single_key_llm_capacity(monkeypatch):
    updates = []
    started = []
    release = asyncio.Event()

    monkeypatch.setattr(
        task_manager_module.task_manager,
        "update_task",
        lambda task_id, **kwargs: updates.append((task_id, dict(kwargs))) or True,
        raising=False,
    )

    queue = TaskQueue(max_concurrent=3)
    await queue.initialize()
    set_runtime_shutting_down(False)

    async def _work(task_id: str) -> None:
        started.append(task_id)
        await release.wait()

    for task_id in ("task-a", "task-b"):
        await queue.enqueue(
            task_id=task_id,
            coro_factory=lambda task_id=task_id: _work(task_id),
            user_id=None,
            token_hash="same-system-pool",
            llm_capacity=1,
        )

    await asyncio.sleep(0.2)
    assert started == ["task-a"]

    release.set()
    await asyncio.sleep(0.2)
    assert started == ["task-a", "task-b"]

    set_runtime_shutting_down(True)
    worker = queue._workers["same-system-pool"]
    worker.cancel()
    await asyncio.wait_for(worker, timeout=1)
    set_runtime_shutting_down(False)
