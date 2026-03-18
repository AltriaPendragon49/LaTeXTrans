import asyncio
import base64
import json
import os
from types import SimpleNamespace

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import translate as translate_route
from backend.app.api.routes.translate import TranslateRequest


def _jwt_for(user_id: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": user_id}).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"header.{payload}.sig"


def test_start_translation_schedules_community_publish_watch_for_authenticated_user(monkeypatch):
    scheduled = []

    class _TaskManager:
        def get_task(self, task_id):
            return {
                "task_id": task_id,
                "status": "pending",
                "source_available": True,
                "source_path": "data/uploads/task-1",
                "arxiv_id": "2503.01010",
            }

        def update_task(self, *args, **kwargs):
            return True

        def persist_task_if_needed(self, task_id):
            return True

    class _Queue:
        def get_user_active_count(self, _user_id):
            return 0

        async def enqueue(self, *args, **kwargs):
            return None

    async def _build_llm_config_async(*args, **kwargs):
        return {"api_key": "demo-key"}

    async def _persist_task_config_hash(*args, **kwargs):
        return None

    def _schedule_watch(task_id, user_id):
        scheduled.append((task_id, user_id))

    monkeypatch.setattr(translate_route, "task_manager", _TaskManager())
    monkeypatch.setattr(translate_route, "get_task_queue", lambda: _Queue())
    monkeypatch.setattr(translate_route, "build_llm_config_async", _build_llm_config_async)
    monkeypatch.setattr(translate_route, "persist_task_config_hash", _persist_task_config_hash)
    monkeypatch.setattr(translate_route, "_schedule_community_publish_watch", _schedule_watch, raising=False)

    response = asyncio.run(
        translate_route.start_translation(
            task_id="task-1",
            request=TranslateRequest(source_language="en", target_language="zh"),
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
        )
    )

    assert response.task_id == "task-1"
    assert scheduled == [("task-1", "user-1")]
