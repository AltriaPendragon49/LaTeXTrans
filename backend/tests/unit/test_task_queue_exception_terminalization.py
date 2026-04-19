import asyncio

import backend.app.services.task_manager as task_manager_module
from backend.app.services.task_manager import TaskQueue, set_runtime_shutting_down


def test_task_queue_marks_unexpected_exception_as_failed(monkeypatch):
    updates = []

    async def _run() -> None:
        monkeypatch.setattr(
            task_manager_module.task_manager,
            "update_task",
            lambda task_id, **kwargs: updates.append((task_id, dict(kwargs))) or True,
            raising=False,
        )
        monkeypatch.setattr(
            task_manager_module.task_manager,
            "get_task",
            lambda _task_id: {"task_id": "task-explode", "status": "processing", "progress": 40},
            raising=False,
        )
        monkeypatch.setattr(
            task_manager_module.task_manager,
            "is_cancelled",
            lambda _task_id: False,
            raising=False,
        )

        queue = TaskQueue(max_concurrent=1)
        await queue.initialize()
        set_runtime_shutting_down(False)

        async def exploding_coro():
            raise RuntimeError("boom")

        await queue.enqueue(
            task_id="task-explode",
            coro_factory=lambda: exploding_coro(),
            user_id=None,
            token_hash="unexpected-exception-token",
        )

        await asyncio.sleep(0.2)

        assert any(
            task_id == "task-explode"
            and payload.get("status") == "failed"
            and payload.get("detail_code") == "task_runtime_exception"
            for task_id, payload in updates
        )

        set_runtime_shutting_down(True)
        queue._workers["unexpected-exception-token"].cancel()
        await asyncio.wait_for(queue._workers["unexpected-exception-token"], timeout=1)
        set_runtime_shutting_down(False)

    asyncio.run(_run())
