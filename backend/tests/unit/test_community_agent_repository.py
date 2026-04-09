import sqlite3
from pathlib import Path

import pytest

from backend.app.core.config import get_settings
from backend.app.repositories import CommunityAgentConversationRepository


def _create_sqlite_schema(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            create table community_agent_conversations (
              conversation_id text not null,
              user_id text not null,
              title text not null,
              created_at text not null,
              updated_at text not null,
              turns text not null,
              primary key (conversation_id, user_id)
            );
            create index community_agent_conversations_user_updated_idx
              on community_agent_conversations (user_id, updated_at desc);
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_repository_scopes_listings_to_the_current_user(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "community-agent.db"
    _create_sqlite_schema(database_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")

    repository = CommunityAgentConversationRepository()
    repository.upsert_conversation_for_user(
        "usr-1",
        {
            "id": "conversation-1",
            "title": "User one",
            "created_at": "2026-04-09T10:00:00Z",
            "updated_at": "2026-04-09T10:01:00Z",
            "turns": [],
        },
    )
    repository.upsert_conversation_for_user(
        "usr-2",
        {
            "id": "conversation-1",
            "title": "User two",
            "created_at": "2026-04-09T11:00:00Z",
            "updated_at": "2026-04-09T11:01:00Z",
            "turns": [],
        },
    )

    result = repository.list_conversations_for_user("usr-1")

    assert len(result) == 1
    assert result[0]["title"] == "User one"


def test_repository_roundtrips_serialized_turns_and_updates_existing_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "community-agent.db"
    _create_sqlite_schema(database_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")

    repository = CommunityAgentConversationRepository()
    created = repository.upsert_conversation_for_user(
        "usr-1",
        {
            "id": "conversation-1",
            "title": "Grounded chat",
            "created_at": "2026-04-09T10:00:00Z",
            "updated_at": "2026-04-09T10:01:00Z",
            "turns": [
                {
                    "id": "turn-1",
                    "role": "user",
                    "content": "Explain this paper",
                    "created_at": "2026-04-09T10:00:00Z",
                }
            ],
        },
    )
    updated = repository.upsert_conversation_for_user(
        "usr-1",
        {
            "id": "conversation-1",
            "title": "Grounded chat updated",
            "created_at": "2026-04-09T10:00:00Z",
            "updated_at": "2026-04-09T10:02:00Z",
            "turns": [
                {
                    "id": "turn-1",
                    "role": "user",
                    "content": "Explain this paper",
                    "created_at": "2026-04-09T10:00:00Z",
                },
                {
                    "id": "turn-2",
                    "role": "assistant",
                    "content": "Here is the grounded answer",
                    "created_at": "2026-04-09T10:02:00Z",
                    "status": "completed",
                },
            ],
        },
    )

    assert created["turns"][0]["id"] == "turn-1"
    assert updated["title"] == "Grounded chat updated"
    assert len(updated["turns"]) == 2
    assert updated["turns"][1]["role"] == "assistant"


def test_repository_deletes_only_the_owned_conversation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "community-agent.db"
    _create_sqlite_schema(database_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")

    repository = CommunityAgentConversationRepository()
    repository.upsert_conversation_for_user(
        "usr-1",
        {
            "id": "conversation-1",
            "title": "Owned chat",
            "created_at": "2026-04-09T10:00:00Z",
            "updated_at": "2026-04-09T10:01:00Z",
            "turns": [],
        },
    )
    repository.upsert_conversation_for_user(
        "usr-2",
        {
            "id": "conversation-1",
            "title": "Someone else's chat",
            "created_at": "2026-04-09T10:00:00Z",
            "updated_at": "2026-04-09T10:01:00Z",
            "turns": [],
        },
    )

    deleted = repository.delete_conversation_for_user("usr-1", "conversation-1")

    assert deleted is True
    assert repository.get_conversation_for_user("usr-1", "conversation-1") is None
    assert repository.get_conversation_for_user("usr-2", "conversation-1") is not None
