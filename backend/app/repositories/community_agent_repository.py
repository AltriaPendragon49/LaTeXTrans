from __future__ import annotations

import json
from typing import Any, Optional

from backend.app.db import db_connection, get_database_dialect


def _placeholder(_index: int) -> str:
    return "?" if get_database_dialect() == "sqlite" else "%s"


def _fetchone(cursor) -> Optional[dict[str, Any]]:
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {key: row[key] for key in row.keys()}


def _fetchall(cursor) -> list[dict[str, Any]]:
    rows = cursor.fetchall() or []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(dict(row))
        else:
            normalized.append({key: row[key] for key in row.keys()})
    return normalized


def _decode_turns(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [dict(item) for item in parsed if isinstance(item, dict)]
    return []


class CommunityAgentConversationRepository:
    def _normalize_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if row is None:
            return None
        return {
            "id": str(row.get("conversation_id") or row.get("id") or "").strip(),
            "title": str(row.get("title") or "New chat").strip() or "New chat",
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
            "turns": _decode_turns(row.get("turns")),
        }

    def _serialize_turns(self, turns: Any) -> str:
        normalized = [dict(item) for item in (turns or []) if isinstance(item, dict)]
        return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))

    def list_conversations_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select conversation_id, title, created_at, updated_at, turns "
                    f"from community_agent_conversations where user_id = {_placeholder(0)} "
                    "order by updated_at desc"
                ),
                (user_id,),
            )
            return [
                normalized
                for normalized in (self._normalize_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def get_conversation_for_user(self, user_id: str, conversation_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select conversation_id, title, created_at, updated_at, turns "
                    f"from community_agent_conversations where user_id = {_placeholder(0)} "
                    f"and conversation_id = {_placeholder(1)} limit 1"
                ),
                (user_id, conversation_id),
            )
            return self._normalize_row(_fetchone(cursor))

    def upsert_conversation_for_user(self, user_id: str, record: dict[str, Any]) -> dict[str, Any]:
        conversation_id = str(record.get("id") or "").strip()
        if not conversation_id:
            raise ValueError("conversation id is required")

        payload = {
            "conversation_id": conversation_id,
            "title": str(record.get("title") or "New chat").strip() or "New chat",
            "created_at": str(record.get("created_at") or ""),
            "updated_at": str(record.get("updated_at") or ""),
            "turns": self._serialize_turns(record.get("turns") or []),
        }

        existing = self.get_conversation_for_user(user_id, conversation_id)
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            if existing is None:
                cursor.execute(
                    (
                        "insert into community_agent_conversations "
                        "(conversation_id, user_id, title, created_at, updated_at, turns) "
                        f"values ({_placeholder(0)}, {_placeholder(1)}, {_placeholder(2)}, "
                        f"{_placeholder(3)}, {_placeholder(4)}, {_placeholder(5)})"
                    ),
                    (
                        payload["conversation_id"],
                        user_id,
                        payload["title"],
                        payload["created_at"],
                        payload["updated_at"],
                        payload["turns"],
                    ),
                )
            else:
                cursor.execute(
                    (
                        "update community_agent_conversations "
                        f"set title = {_placeholder(0)}, created_at = {_placeholder(1)}, "
                        f"updated_at = {_placeholder(2)}, turns = {_placeholder(3)} "
                        f"where user_id = {_placeholder(4)} and conversation_id = {_placeholder(5)}"
                    ),
                    (
                        payload["title"],
                        payload["created_at"],
                        payload["updated_at"],
                        payload["turns"],
                        user_id,
                        payload["conversation_id"],
                    ),
                )

        saved = self.get_conversation_for_user(user_id, conversation_id)
        return saved or {
            "id": payload["conversation_id"],
            "title": payload["title"],
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
            "turns": _decode_turns(payload["turns"]),
        }

    def delete_conversation_for_user(self, user_id: str, conversation_id: str) -> bool:
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "delete from community_agent_conversations "
                    f"where user_id = {_placeholder(0)} and conversation_id = {_placeholder(1)}"
                ),
                (user_id, conversation_id),
            )
            return bool(cursor.rowcount)
