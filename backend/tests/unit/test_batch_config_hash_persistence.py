import asyncio
import base64
import json
import os
import sqlite3
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from fastapi.security import HTTPAuthorizationCredentials

from backend.app.core.config import get_settings
from backend.app.api.routes import translate as translate_route
from backend.app.models.config_models import AdvancedConfig, FormattingConfig
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


class _DuplicateInsertQuery:
    def __init__(self, inserted_records, updated_records):
        self._inserted_records = inserted_records
        self._updated_records = updated_records
        self._update_payload = None
        self._task_id = None

    def insert(self, record):
        self._inserted_records.append(record)
        self._update_payload = None
        return self

    def update(self, record):
        self._update_payload = record
        return self

    def eq(self, field, value):
        assert field == "task_id"
        self._task_id = value
        return self

    def execute(self):
        if self._update_payload is not None:
            self._updated_records.append((self._task_id, self._update_payload))

            class _Result:
                data = [{"ok": True}]

            return _Result()

        raise Exception(
            'duplicate key value violates unique constraint "translation_tasks_task_id_key"'
        )


class _InsertClient:
    def __init__(self, inserted_records):
        self._inserted_records = inserted_records

    def table(self, table_name):
        assert table_name == "translation_tasks"
        return _InsertQuery(self._inserted_records)


class _DuplicateInsertClient:
    def __init__(self, inserted_records, updated_records):
        self._inserted_records = inserted_records
        self._updated_records = updated_records

    def table(self, table_name):
        assert table_name == "translation_tasks"
        return _DuplicateInsertQuery(self._inserted_records, self._updated_records)


class _CapturingTaskRepository:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}
        self.upserts: list[tuple[str, dict]] = []

    def get_task(self, task_id: str):
        row = self.rows.get(task_id)
        return dict(row) if row is not None else None

    def upsert_task(self, task_id: str, payload: dict):
        current = dict(self.rows.get(task_id, {}))
        current.update(payload)
        self.rows[task_id] = current
        self.upserts.append((task_id, dict(payload)))
        return dict(current)


def _make_fake_jwt(user_id: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": user_id}).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    return f"header.{payload}.signature"


def _create_sqlite_schema(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            create table users (
              id text primary key,
              external_provider text not null,
              external_user_id text not null,
              email text null,
              display_name text null,
              token_version integer not null default 1,
              status text not null default 'active',
              created_at text not null,
              updated_at text not null
            );

            create table translation_tasks (
              task_id text primary key,
              user_id text null,
              source_type text not null,
              arxiv_id text null,
              status text not null,
              stage text null,
              progress integer not null default 0,
              message text null,
              error text null,
              detail_code text null,
              source_language text not null,
              target_language text not null,
              translation_mode text not null,
              compile_strategy text not null,
              translation_model text null,
              config_hash text null,
              source_path text null,
              output_path text null,
              formatting text null,
              generate_glossary integer not null default 1,
              use_author_api integer not null default 1,
              email_notification integer not null default 0,
              created_at text not null,
              completed_at text null
            );
            """
        )
        cursor.execute(
            """
            insert into users (id, external_provider, external_user_id, email, display_name, token_version, status, created_at, updated_at)
            values ('usr_local_1', 'niutrans', '179017', 'alice@example.com', 'Alice', 1, 'active', '2026-04-09T00:00:00', '2026-04-09T00:00:00')
            """
        )
        connection.commit()
    finally:
        connection.close()


def _make_workspace_temp_root() -> Path:
    root = Path("data/__pytest_tmp__")
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def test_persist_task_if_needed_includes_config_hash(monkeypatch):
    fake_repository = _CapturingTaskRepository()
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_translation_task_repository",
        lambda: fake_repository,
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
    assert fake_repository.upserts[-1][1]["config_hash"] == "hash-batch-task"


def test_persist_task_if_needed_treats_duplicate_insert_as_success(monkeypatch):
    fake_repository = _CapturingTaskRepository()
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_translation_task_repository",
        lambda: fake_repository,
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
    assert fake_repository.rows[task_id]["config_hash"] == "hash-batch-task"

    task_manager.update_task(task_id=task_id, progress=42, message="updated")
    assert task_manager.persist_task_if_needed(task_id) is True
    assert fake_repository.rows[task_id]["task_id"] == task_id
    assert fake_repository.rows[task_id]["config_hash"] == "hash-batch-task"


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

    class _FakeQuotaService:
        def reserve_latex_translation(self, *, user_id: str, requested_count: int):
            assert user_id == "user-1"
            assert requested_count == 1
            return None

        def release_latex_translation(self, *, user_id: str, count: int):
            raise AssertionError("accepted batch tasks should not release reserved quota")

    monkeypatch.setattr(translate_route, "task_manager", _FakeTaskManager())
    monkeypatch.setattr(translate_route, "extract_arxiv_ids", lambda values: values)
    monkeypatch.setattr(translate_route, "build_llm_config_async", _fake_build_llm_config_async)
    monkeypatch.setattr(translate_route, "persist_task_config_hash", _fake_persist_task_config_hash)
    monkeypatch.setattr(translate_route, "get_translation_quota_service", lambda: _FakeQuotaService())
    monkeypatch.setattr(translate_route.asyncio, "create_task", _fake_create_task)
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_task_queue",
        lambda: None,
    )

    formatting = FormattingConfig(font_size=12.0, line_spacing=1.0, paragraph_indent=True)
    request = translate_route.BatchTranslateRequest(
        arxiv_ids=["2508.18791"],
        source_language="en",
        target_language="zh",
        advanced_config=AdvancedConfig(formatting=formatting),
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=_make_fake_jwt("user-1"),
    )

    response = asyncio.run(
        translate_route.batch_translate(
            request,
            credentials,
            current_user={"id": "user-1"},
        )
    )

    assert response.task_ids == ["task-1"]
    assert len(captured_hashes) == 1
    task_id, config_hash = captured_hashes[0]
    assert task_id == "task-1"
    assert config_hash == translate_route.compute_config_hash(
        arxiv_id="2508.18791",
        source_language="en",
        target_language="zh",
        translation_mode="full",
        compile_strategy="auto",
        formatting=formatting,
    )


def test_persist_task_config_hash_updates_local_database(monkeypatch):
    temp_root = _make_workspace_temp_root()
    database_path = temp_root / f"translate-route-{uuid4().hex}.db"
    try:
        _create_sqlite_schema(database_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path.resolve()}")

        connection = sqlite3.connect(str(database_path))
        try:
            connection.execute(
                """
                insert into translation_tasks (
                  task_id, user_id, source_type, arxiv_id, status, stage, progress, message, error, detail_code,
                  source_language, target_language, translation_mode, compile_strategy, translation_model, config_hash,
                  source_path, output_path, formatting, generate_glossary, use_author_api, email_notification,
                  created_at, completed_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "task-local-1",
                    "usr_local_1",
                    "arxiv",
                    "2501.00001",
                    "pending",
                    "idle",
                    0,
                    None,
                    None,
                    None,
                    "en",
                    "zh",
                    "full",
                    "auto",
                    None,
                    None,
                    None,
                    None,
                    None,
                    1,
                    1,
                    0,
                    "2026-04-09T00:00:00",
                    None,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        assert asyncio.run(
            translate_route.persist_task_config_hash("task-local-1", "cfg-local-1")
        ) is True

        connection = sqlite3.connect(str(database_path))
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute(
                "select config_hash from translation_tasks where task_id = ?",
                ("task-local-1",),
            ).fetchone()
        finally:
            connection.close()

        assert row is not None
        assert row["config_hash"] == "cfg-local-1"
    finally:
        database_path.unlink(missing_ok=True)


def test_find_reusable_output_reads_local_database(monkeypatch):
    temp_root = _make_workspace_temp_root()
    database_path = temp_root / f"translate-route-{uuid4().hex}.db"
    outputs_root = temp_root / f"translate-route-{uuid4().hex}-outputs"
    try:
        _create_sqlite_schema(database_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path.resolve()}")
        monkeypatch.setattr(settings, "outputs_dir", outputs_root)

        reusable_output = outputs_root / "task-existing"
        reusable_output.mkdir(parents=True)

        connection = sqlite3.connect(str(database_path))
        try:
            connection.execute(
                """
                insert into translation_tasks (
                  task_id, user_id, source_type, arxiv_id, status, stage, progress, message, error, detail_code,
                  source_language, target_language, translation_mode, compile_strategy, translation_model, config_hash,
                  source_path, output_path, formatting, generate_glossary, use_author_api, email_notification,
                  created_at, completed_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "task-existing",
                    "usr_local_1",
                    "arxiv",
                    "2501.00001",
                    "completed",
                    "done",
                    100,
                    None,
                    None,
                    None,
                    "en",
                    "zh",
                    "full",
                    "auto",
                    None,
                    "cfg-local-1",
                    None,
                    str(reusable_output),
                    None,
                    1,
                    1,
                    0,
                    "2026-04-09T00:00:00",
                    "2026-04-09T00:10:00",
                ),
            )
            connection.commit()
        finally:
            connection.close()

        result = asyncio.run(
            translate_route.find_reusable_output("cfg-local-1", "task-current")
        )

        assert result == str(reusable_output)
    finally:
        database_path.unlink(missing_ok=True)
        rmtree(outputs_root, ignore_errors=True)
