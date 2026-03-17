import asyncio
import base64
import json
import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.routes import translate as translate_route
from backend.app.models.config_models import AdvancedConfig
from backend.app.services.task_manager import TaskManager


class _InsertQuery:
    def __init__(self, inserted_records):
        self._inserted_records = inserted_records

    def insert(self, record):
        self._inserted_records.append(record)
        return self

    def execute(self):
        class _Result:
            data = [{"ok": True}]

        return _Result()


class _InsertClient:
    def __init__(self, inserted_records):
        self._inserted_records = inserted_records

    def table(self, table_name):
        assert table_name == "translation_tasks"
        return _InsertQuery(self._inserted_records)


def _make_fake_jwt(user_id: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": user_id}).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    return f"header.{payload}.signature"


def test_persist_task_if_needed_includes_config_hash(monkeypatch):
    inserted_records = []
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_supabase_admin_client",
        lambda: _InsertClient(inserted_records),
    )

    task_manager = TaskManager()
    task_id = task_manager.create_task(
        source_type="arxiv",
        arxiv_id="2508.18791",
        user_id="user-1",
        persist_to_db=False,
    )

    task_manager.update_task(
        task_id=task_id,
        source_language="en",
        target_language="zh",
        advanced_config={
            "translation_mode": "full",
            "compile_strategy": "auto",
        },
        config_hash="hash-batch-task",
    )

    assert task_manager.persist_task_if_needed(task_id) is True
    assert inserted_records[-1]["config_hash"] == "hash-batch-task"


def test_batch_translate_persists_config_hash(monkeypatch):
    captured_hashes = []
    scheduled_coroutines = []

    class _FakeTaskManager:
        def __init__(self):
            self.created = 0
            self.updates = []

        def create_task(self, **kwargs):
            self.created += 1
            return f"task-{self.created}"

        def update_task(self, task_id, **kwargs):
            self.updates.append((task_id, kwargs))
            return True

        def persist_task_if_needed(self, task_id):
            return True

    async def _fake_build_llm_config_async(_advanced_config, _user_id):
        return {"api_key": "batch-secret"}

    async def _fake_persist_task_config_hash(task_id: str, config_hash: str) -> bool:
        captured_hashes.append((task_id, config_hash))
        return True

    def _fake_create_task(coro):
        scheduled_coroutines.append(coro)
        coro.close()
        return None

    monkeypatch.setattr(translate_route, "task_manager", _FakeTaskManager())
    monkeypatch.setattr(translate_route, "extract_arxiv_ids", lambda values: values)
    monkeypatch.setattr(translate_route, "build_llm_config_async", _fake_build_llm_config_async)
    monkeypatch.setattr(translate_route, "persist_task_config_hash", _fake_persist_task_config_hash)
    monkeypatch.setattr(translate_route.asyncio, "create_task", _fake_create_task)
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_task_queue",
        lambda: None,
    )

    request = translate_route.BatchTranslateRequest(
        arxiv_ids=["2508.18791"],
        source_language="en",
        target_language="zh",
        advanced_config=AdvancedConfig(),
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=_make_fake_jwt("user-1"),
    )

    response = asyncio.run(translate_route.batch_translate(request, credentials))

    assert response.task_ids == ["task-1"]
    assert len(captured_hashes) == 1
    task_id, config_hash = captured_hashes[0]
    assert task_id == "task-1"
    assert config_hash
