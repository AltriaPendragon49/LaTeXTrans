import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

from backend.app.core.config import get_settings
from backend.app.repositories.community_agent_repository import CommunityAgentRunRepository


def _create_sqlite_schema(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            create table community_agent_runs (
              run_id text not null,
              user_id text null,
              conversation_id text null,
              status text not null,
              intent text not null,
              mode text not null,
              message text null,
              summary text null,
              error text null,
              report text null,
              created_at text not null,
              updated_at text not null,
              completed_at text null,
              primary key (run_id)
            );
            create table community_agent_events (
              id integer primary key autoincrement,
              run_id text not null,
              sequence_no integer not null,
              event_type text not null,
              payload text not null,
              created_at text not null,
              unique (run_id, sequence_no)
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_run_repository_upsert_get_and_event_replay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "community-agent-runs.db"
    _create_sqlite_schema(database_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")

    repository = CommunityAgentRunRepository()
    repository.upsert_run(
        {
            "run_id": "run-1",
            "user_id": "usr-1",
            "conversation_id": None,
            "status": "accepted",
            "intent": "answer",
            "mode": "chat",
            "message": None,
            "summary": None,
            "error": None,
            "report": None,
            "created_at": "2026-04-09T10:00:00+00:00",
            "updated_at": "2026-04-09T10:00:00+00:00",
            "completed_at": None,
        }
    )
    repository.append_event(
        "run-1",
        1,
        {
            "type": "status",
            "run_id": "run-1",
            "sequence": 1,
            "timestamp": "2026-04-09T10:00:00+00:00",
            "data": {"status": "accepted"},
        },
    )
    repository.upsert_run(
        {
            "run_id": "run-1",
            "user_id": "usr-1",
            "conversation_id": None,
            "status": "completed",
            "intent": "answer",
            "mode": "chat",
            "message": "done",
            "summary": "done",
            "error": None,
            "report": {"notes": "ok"},
            "created_at": "2026-04-09T10:00:00+00:00",
            "updated_at": "2026-04-09T10:00:01+00:00",
            "completed_at": "2026-04-09T10:00:01+00:00",
        }
    )
    repository.append_event(
        "run-1",
        2,
        {
            "type": "complete",
            "run_id": "run-1",
            "sequence": 2,
            "timestamp": "2026-04-09T10:00:01+00:00",
            "data": {"snapshot": {"run_id": "run-1", "status": "completed"}},
        },
    )

    loaded = repository.get_run("run-1")
    events = repository.list_events("run-1")

    assert loaded is not None
    assert loaded["user_id"] == "usr-1"
    assert loaded["status"] == "completed"
    assert loaded["message"] == "done"
    assert loaded["report"]["notes"] == "ok"
    assert [event["sequence"] for event in events] == [1, 2]
    assert events[1]["type"] == "complete"


def test_run_repository_normalizes_mysql_datetime_inputs_before_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded_calls: list[tuple[str, tuple[object, ...] | None]] = []

    class FakeCursor:
        rowcount = 1

        def execute(self, sql: str, params=None) -> None:  # type: ignore[no-untyped-def]
            normalized = tuple(params) if params is not None else None
            recorded_calls.append((sql, normalized))

        def fetchone(self):  # type: ignore[no-untyped-def]
            return None

    class FakeConnection:
        def cursor(self) -> FakeCursor:
            return FakeCursor()

    @contextmanager
    def fake_db_connection(*, commit: bool = False):  # type: ignore[no-untyped-def]
        del commit
        yield FakeConnection()

    repository = CommunityAgentRunRepository()
    load_count = {"value": 0}

    def fake_get_run(run_id: str):  # type: ignore[no-untyped-def]
        load_count["value"] += 1
        if load_count["value"] == 1:
            return None
        return {
            "run_id": run_id,
            "user_id": "usr-1",
            "conversation_id": "conversation-1",
            "status": "completed",
            "intent": "answer",
            "mode": "chat",
            "message": "done",
            "summary": "done",
            "error": None,
            "report": {"notes": "ok"},
            "created_at": "2026-04-09 10:00:00",
            "updated_at": "2026-04-09 10:00:01",
            "completed_at": "2026-04-09 10:00:02",
        }

    monkeypatch.setattr(
        "backend.app.repositories.community_agent_repository.get_database_dialect",
        lambda: "mysql",
    )
    monkeypatch.setattr(
        "backend.app.repositories.community_agent_repository.db_connection",
        fake_db_connection,
    )
    monkeypatch.setattr(repository, "get_run", fake_get_run)

    saved = repository.upsert_run(
        {
            "run_id": "run-1",
            "user_id": "usr-1",
            "conversation_id": "conversation-1",
            "status": "completed",
            "intent": "answer",
            "mode": "chat",
            "message": "done",
            "summary": "done",
            "error": None,
            "report": {"notes": "ok"},
            "created_at": "2026-04-09T10:00:00Z",
            "updated_at": "2026-04-09T10:00:01.250Z",
            "completed_at": "2026-04-09T10:00:02+00:00",
        }
    )

    repository.append_event(
        "run-1",
        1,
        {
            "type": "status",
            "run_id": "run-1",
            "sequence": 1,
            "timestamp": "2026-04-09T10:00:03.999Z",
            "data": {"status": "completed"},
        },
    )

    run_insert_calls = [params for sql, params in recorded_calls if sql.lower().startswith("insert into community_agent_runs")]
    event_insert_calls = [params for sql, params in recorded_calls if sql.lower().startswith("insert into community_agent_events")]

    assert run_insert_calls
    assert run_insert_calls[0] is not None
    assert run_insert_calls[0][10] == "2026-04-09 10:00:00"
    assert run_insert_calls[0][11] == "2026-04-09 10:00:01"
    assert run_insert_calls[0][12] == "2026-04-09 10:00:02"

    assert event_insert_calls
    assert event_insert_calls[0] is not None
    assert event_insert_calls[0][4] == "2026-04-09 10:00:03"
    assert saved["created_at"] == "2026-04-09 10:00:00"
    assert saved["updated_at"] == "2026-04-09 10:00:01"
    assert saved["completed_at"] == "2026-04-09 10:00:02"
