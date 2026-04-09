import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.core.config import get_settings
from backend.app.services.task_manager import TaskManager


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


def test_task_manager_persists_authenticated_tasks_to_local_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temp_root = _make_workspace_temp_root()
    database_path = temp_root / f"translation-task-{uuid4().hex}.db"
    try:
        _create_sqlite_schema(database_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path.resolve()}")

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            source_type="arxiv",
            arxiv_id="2501.00001",
            user_id="usr_local_1",
            persist_to_db=False,
        )
        task_manager.update_task(
            task_id=task_id,
            source_language="en",
            target_language="zh",
            advanced_config={
                "translation_mode": "full",
                "compile_strategy": "auto",
                "translation_model": "demo-model",
                "generate_terminology_table": True,
                "use_author_api": False,
                "formatting": {"font_size": 12},
            },
            config_hash="cfg-local-1",
            source_path="data/uploads/task-local-1",
            output_path="data/outputs/task-local-1",
        )

        assert task_manager.persist_task_if_needed(task_id) is True

        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute(
                "select task_id, user_id, config_hash, translation_model, source_path, output_path from translation_tasks where task_id = ?",
                (task_id,),
            ).fetchone()
        finally:
            connection.close()

        assert row is not None
        assert row["task_id"] == task_id
        assert row["user_id"] == "usr_local_1"
        assert row["config_hash"] == "cfg-local-1"
        assert row["translation_model"] == "demo-model"
        assert row["source_path"] == "data/uploads/task-local-1"
        assert row["output_path"] == "data/outputs/task-local-1"
    finally:
        database_path.unlink(missing_ok=True)


def test_task_manager_flush_updates_local_translation_task_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temp_root = _make_workspace_temp_root()
    database_path = temp_root / f"translation-task-{uuid4().hex}.db"
    try:
        _create_sqlite_schema(database_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path.resolve()}")

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            source_type="upload",
            user_id="usr_local_1",
            persist_to_db=False,
        )
        assert task_manager.persist_task_if_needed(task_id) is True

        task_manager.update_task(
            task_id=task_id,
            status="processing",
            stage="translating",
            progress=55,
            message="Translating 55%",
            user_id="usr_local_1",
        )
        task_manager._flusher.drain(timeout=2.0)

        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute(
                "select status, stage, progress, message from translation_tasks where task_id = ?",
                (task_id,),
            ).fetchone()
        finally:
            connection.close()

        assert row is not None
        assert row["status"] == "processing"
        assert row["stage"] == "translating"
        assert row["progress"] == 55
        assert row["message"] == "Translating 55%"
    finally:
        database_path.unlink(missing_ok=True)
