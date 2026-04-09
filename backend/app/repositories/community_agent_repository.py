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


def _decode_json_dict(value: Any) -> dict[str, Any] | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return dict(parsed)
    return None


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


class CommunityAgentRunRepository:
    def _normalize_run_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if row is None:
            return None
        return {
            "run_id": str(row.get("run_id") or "").strip(),
            "user_id": str(row.get("user_id") or "").strip() or None,
            "conversation_id": str(row.get("conversation_id") or "").strip() or None,
            "status": str(row.get("status") or "queued"),
            "intent": str(row.get("intent") or "answer"),
            "mode": str(row.get("mode") or "chat"),
            "message": row.get("message"),
            "summary": row.get("summary"),
            "error": row.get("error"),
            "report": _decode_json_dict(row.get("report")),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
            "completed_at": str(row.get("completed_at") or "") or None,
        }

    def _serialize_json_dict(self, payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select run_id, user_id, conversation_id, status, intent, mode, "
                    "message, summary, error, report, created_at, updated_at, completed_at "
                    f"from community_agent_runs where run_id = {_placeholder(0)} limit 1"
                ),
                (run_id,),
            )
            return self._normalize_run_row(_fetchone(cursor))

    def upsert_run(self, record: dict[str, Any]) -> dict[str, Any]:
        run_id = str(record.get("run_id") or "").strip()
        if not run_id:
            raise ValueError("run_id is required")

        payload = {
            "run_id": run_id,
            "user_id": str(record.get("user_id") or "").strip() or None,
            "conversation_id": str(record.get("conversation_id") or "").strip() or None,
            "status": str(record.get("status") or "queued"),
            "intent": str(record.get("intent") or "answer"),
            "mode": str(record.get("mode") or "chat"),
            "message": record.get("message"),
            "summary": record.get("summary"),
            "error": record.get("error"),
            "report": self._serialize_json_dict(record.get("report")),
            "created_at": str(record.get("created_at") or ""),
            "updated_at": str(record.get("updated_at") or ""),
            "completed_at": str(record.get("completed_at") or "") or None,
        }

        existing = self.get_run(run_id)
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            if existing is None:
                cursor.execute(
                    (
                        "insert into community_agent_runs "
                        "(run_id, user_id, conversation_id, status, intent, mode, message, "
                        "summary, error, report, created_at, updated_at, completed_at) "
                        f"values ({_placeholder(0)}, {_placeholder(1)}, {_placeholder(2)}, "
                        f"{_placeholder(3)}, {_placeholder(4)}, {_placeholder(5)}, {_placeholder(6)}, "
                        f"{_placeholder(7)}, {_placeholder(8)}, {_placeholder(9)}, {_placeholder(10)}, "
                        f"{_placeholder(11)}, {_placeholder(12)})"
                    ),
                    (
                        payload["run_id"],
                        payload["user_id"],
                        payload["conversation_id"],
                        payload["status"],
                        payload["intent"],
                        payload["mode"],
                        payload["message"],
                        payload["summary"],
                        payload["error"],
                        payload["report"],
                        payload["created_at"],
                        payload["updated_at"],
                        payload["completed_at"],
                    ),
                )
            else:
                cursor.execute(
                    (
                        "update community_agent_runs set "
                        f"user_id = {_placeholder(0)}, conversation_id = {_placeholder(1)}, "
                        f"status = {_placeholder(2)}, intent = {_placeholder(3)}, mode = {_placeholder(4)}, "
                        f"message = {_placeholder(5)}, summary = {_placeholder(6)}, error = {_placeholder(7)}, "
                        f"report = {_placeholder(8)}, created_at = {_placeholder(9)}, "
                        f"updated_at = {_placeholder(10)}, completed_at = {_placeholder(11)} "
                        f"where run_id = {_placeholder(12)}"
                    ),
                    (
                        payload["user_id"],
                        payload["conversation_id"],
                        payload["status"],
                        payload["intent"],
                        payload["mode"],
                        payload["message"],
                        payload["summary"],
                        payload["error"],
                        payload["report"],
                        payload["created_at"],
                        payload["updated_at"],
                        payload["completed_at"],
                        payload["run_id"],
                    ),
                )

        return self.get_run(run_id) or {
            "run_id": payload["run_id"],
            "user_id": payload["user_id"],
            "conversation_id": payload["conversation_id"],
            "status": payload["status"],
            "intent": payload["intent"],
            "mode": payload["mode"],
            "message": payload["message"],
            "summary": payload["summary"],
            "error": payload["error"],
            "report": _decode_json_dict(payload["report"]),
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
            "completed_at": payload["completed_at"],
        }

    def append_event(self, run_id: str, sequence_no: int, event: dict[str, Any]) -> None:
        payload = json.dumps(dict(event), ensure_ascii=False, separators=(",", ":"))
        event_type = str(event.get("type") or "status")
        created_at = str(event.get("timestamp") or "")

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id from community_agent_events "
                    f"where run_id = {_placeholder(0)} and sequence_no = {_placeholder(1)} limit 1"
                ),
                (run_id, int(sequence_no)),
            )
            existing = _fetchone(cursor)
            if existing is None:
                cursor.execute(
                    (
                        "insert into community_agent_events "
                        "(run_id, sequence_no, event_type, payload, created_at) "
                        f"values ({_placeholder(0)}, {_placeholder(1)}, {_placeholder(2)}, "
                        f"{_placeholder(3)}, {_placeholder(4)})"
                    ),
                    (run_id, int(sequence_no), event_type, payload, created_at),
                )
            else:
                cursor.execute(
                    (
                        "update community_agent_events set "
                        f"event_type = {_placeholder(0)}, payload = {_placeholder(1)}, "
                        f"created_at = {_placeholder(2)} where run_id = {_placeholder(3)} "
                        f"and sequence_no = {_placeholder(4)}"
                    ),
                    (event_type, payload, created_at, run_id, int(sequence_no)),
                )

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select sequence_no, payload "
                    f"from community_agent_events where run_id = {_placeholder(0)} "
                    "order by sequence_no asc"
                ),
                (run_id,),
            )
            events: list[dict[str, Any]] = []
            for row in _fetchall(cursor):
                payload = _decode_json_dict(row.get("payload"))
                if payload is None:
                    continue
                payload.setdefault("sequence", int(row.get("sequence_no") or 0))
                events.append(payload)
            return events
