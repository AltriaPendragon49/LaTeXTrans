import sqlite3
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
