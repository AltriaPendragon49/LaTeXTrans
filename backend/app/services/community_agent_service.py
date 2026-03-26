from __future__ import annotations

import asyncio
import hashlib
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from postgrest.exceptions import APIError
from supabase import Client

from backend.app.services import paper_service
from backend.app.services.community_agent import run_agent
from backend.app.core.auth import clone_supabase_client_with_same_auth
from backend.app.utils.async_blocking import run_db_blocking

_RUNTIME_AGENT_RUNS: Dict[str, "_RunRecord"] = {}
_CONVERSATIONS_TABLE = "community_agent_conversations"


@dataclass
class _RunRecord:
    run_id: str
    auth_token_hash: str | None
    status: str = "queued"
    intent: str = "answer"
    message: str | None = None
    summary: str | None = None
    tool_trace: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    provider_state: Dict[str, str] | None = None
    action: Dict[str, Any] | None = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    completed: bool = False
    thread: threading.Thread | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


def _hash_access_token(access_token: str | None) -> str | None:
    if not access_token:
        return None
    return hashlib.sha256(access_token.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_provider_state() -> Dict[str, str]:
    return {
        "internal_search": "enabled",
        "external_search": "unknown",
        "reasoning": "unknown",
        "translation_bridge": "enabled",
    }


def _build_snapshot(record: _RunRecord, *, include_urls: bool = False) -> Dict[str, Any]:
    with record.lock:
        payload = {
            "run_id": record.run_id,
            "status": record.status,
            "intent": record.intent,
            "message": record.message,
            "summary": record.summary,
            "tool_trace": list(record.tool_trace),
            "citations": list(record.citations),
            "provider_state": dict(record.provider_state or _default_provider_state()),
            "action": dict(record.action) if isinstance(record.action, dict) else record.action,
            "events": list(record.events),
        }
    if include_urls:
        payload["stream_url"] = f"/api/community-agent/runs/{record.run_id}/events"
        payload["result_url"] = f"/api/community-agent/runs/{record.run_id}"
    return payload


def _publish_stream_event(record: _RunRecord, event: Dict[str, Any]) -> Dict[str, Any]:
    with record.lock:
        payload = {
            "type": str(event.get("type") or "status"),
            "run_id": record.run_id,
            "sequence": len(record.events) + 1,
            "timestamp": _now_iso(),
            "data": event.get("data") if isinstance(event.get("data"), dict) else {},
        }
        record.events.append(payload)
        return payload


def _set_status(record: _RunRecord, status: str, *, phase: str | None = None) -> None:
    with record.lock:
        record.status = status
    data: Dict[str, Any] = {"status": status}
    if phase:
        data["phase"] = phase
    _publish_stream_event(record, {"type": "status", "data": data})


def _require_run_record(run_id: str, access_token: str | None = None) -> _RunRecord:
    record = _RUNTIME_AGENT_RUNS.get(run_id)
    if record is None:
        raise KeyError(run_id)

    expected_hash = record.auth_token_hash
    if expected_hash and _hash_access_token(access_token) != expected_hash:
        raise PermissionError("Authentication required")
    return record


async def _run_agent_once(
    record: _RunRecord,
    *,
    input_text: str,
    context: Dict[str, Any] | None,
    skill_toggles: Dict[str, Any] | None,
) -> None:
    try:
        _set_status(record, "running", phase="planner")
        payload = await run_agent(
            input_text=input_text,
            context=context,
            skill_toggles=skill_toggles,
            event_callback=lambda event: _publish_stream_event(record, event),
        )
    except Exception as exc:
        with record.lock:
            record.status = "failed"
            record.intent = "answer"
            record.message = str(exc)
            record.summary = str(exc)
            record.provider_state = _default_provider_state()
            record.error = str(exc)
            record.completed = True
        _publish_stream_event(record, {"type": "error", "data": {"message": str(exc)}})
        _publish_stream_event(record, {"type": "complete", "data": {"snapshot": _build_snapshot(record)}})
        return

    with record.lock:
        record.status = str(payload.get("status") or "completed")
        record.intent = str(payload.get("intent") or "answer")
        record.message = payload.get("message") or payload.get("summary")
        record.summary = payload.get("summary") or payload.get("message")
        record.tool_trace = list(payload.get("tool_trace") or [])
        record.citations = list(payload.get("citations") or [])
        record.provider_state = dict(payload.get("provider_state") or _default_provider_state())
        record.action = payload.get("action") if isinstance(payload.get("action"), dict) else payload.get("action")
        record.completed = True

    _publish_stream_event(record, {"type": "complete", "data": {"snapshot": _build_snapshot(record)}})


def _start_background_run(
    record: _RunRecord,
    *,
    input_text: str,
    context: Dict[str, Any] | None,
    skill_toggles: Dict[str, Any] | None,
) -> None:
    def _runner() -> None:
        asyncio.run(
            _run_agent_once(
                record,
                input_text=input_text,
                context=context,
                skill_toggles=skill_toggles,
            )
        )

    thread = threading.Thread(target=_runner, name=f"community-agent-{record.run_id}", daemon=True)
    record.thread = thread
    thread.start()


async def create_agent_run(
    input_text: str,
    context: Dict[str, Any] | None = None,
    skill_toggles: Dict[str, Any] | None = None,
    *,
    execution_mode: str = "blocking",
    access_token: str | None = None,
) -> Dict[str, Any]:
    run_id = f"run-{uuid.uuid4().hex[:10]}"
    record = _RunRecord(
        run_id=run_id,
        auth_token_hash=_hash_access_token(access_token),
        provider_state={
            "internal_search": "enabled",
            "external_search": "enabled"
            if (skill_toggles or {}).get("external_search")
            else "disabled_by_user",
            "reasoning": "enabled",
            "translation_bridge": "enabled",
        },
    )
    _RUNTIME_AGENT_RUNS[run_id] = record

    if execution_mode == "async":
        with record.lock:
            record.status = "accepted"
        _publish_stream_event(record, {"type": "status", "data": {"status": "accepted", "phase": "accepted"}})
        _start_background_run(record, input_text=input_text, context=context, skill_toggles=skill_toggles)
        return _build_snapshot(record, include_urls=True)

    await _run_agent_once(record, input_text=input_text, context=context, skill_toggles=skill_toggles)
    return _build_snapshot(record)


async def get_agent_run(run_id: str, *, access_token: str | None = None) -> Dict[str, Any]:
    try:
        record = _require_run_record(run_id, access_token)
    except KeyError:
        return {
            "run_id": run_id,
            "status": "failed",
            "intent": "answer",
            "message": None,
            "summary": None,
            "tool_trace": [],
            "citations": [],
            "provider_state": _default_provider_state(),
            "action": None,
            "events": [],
        }
    return _build_snapshot(record)


async def stream_agent_events(run_id: str, *, access_token: str | None = None) -> List[Dict[str, Any]]:
    record = _require_run_record(run_id, access_token)
    with record.lock:
        return list(record.events)


async def wait_for_new_events(
    run_id: str,
    *,
    last_sequence: int,
    access_token: str | None = None,
    timeout: float = 15.0,
) -> List[Dict[str, Any]]:
    record = _require_run_record(run_id, access_token)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with record.lock:
            if len(record.events) > last_sequence:
                return list(record.events[last_sequence:])
            if record.completed:
                return []
        await asyncio.sleep(0.05)
    return []


def _normalize_turn(entry: Any) -> Dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None

    role = str(entry.get("role") or "").strip()
    content = " ".join(str(entry.get("content") or "").split()).strip()
    if role not in {"user", "assistant"} or not content:
        return None

    return {
        "id": str(entry.get("id") or f"turn-{uuid.uuid4().hex[:8]}").strip(),
        "role": role,
        "content": content,
        "created_at": str(entry.get("created_at") or ""),
        "run": entry.get("run") if isinstance(entry.get("run"), dict) else None,
        "status": str(entry.get("status") or "completed"),
        "error": entry.get("error"),
    }


def _normalize_conversation_record(record: Dict[str, Any]) -> Dict[str, Any]:
    turns = [
        normalized
        for normalized in (_normalize_turn(entry) for entry in (record.get("turns") or []))
        if normalized is not None
    ]
    return {
        "id": str(record.get("conversation_id") or record.get("id") or "").strip(),
        "title": str(record.get("title") or "New chat").strip() or "New chat",
        "created_at": str(record.get("created_at") or ""),
        "updated_at": str(record.get("updated_at") or ""),
        "turns": turns,
    }


async def list_conversations(*, supabase_client: Client) -> List[Dict[str, Any]]:
    def _shared_call():
        return (
            supabase_client.table(_CONVERSATIONS_TABLE)
            .select("conversation_id,title,created_at,updated_at,turns")
            .order("updated_at", desc=True)
            .execute()
        )

    def _per_call():
        cloned = clone_supabase_client_with_same_auth(supabase_client)
        client = cloned or supabase_client
        return (
            client.table(_CONVERSATIONS_TABLE)
            .select("conversation_id,title,created_at,updated_at,turns")
            .order("updated_at", desc=True)
            .execute()
        )

    result = await run_db_blocking(_shared_call, per_call_client_call=_per_call)
    return [_normalize_conversation_record(item) for item in (result.data or [])]


async def upsert_conversation(*, supabase_client: Client, record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_conversation_record(record)
    if not normalized["id"]:
        raise ValueError("conversation id is required")

    payload = {
        "conversation_id": normalized["id"],
        "title": normalized["title"],
        "updated_at": normalized["updated_at"],
        "turns": normalized["turns"],
    }
    if normalized["created_at"]:
        payload["created_at"] = normalized["created_at"]

    def _select_existing(client: Client):
        return (
            client.table(_CONVERSATIONS_TABLE)
            .select("conversation_id")
            .eq("conversation_id", normalized["id"])
            .limit(1)
            .execute()
        )

    def _insert(client: Client):
        return client.table(_CONVERSATIONS_TABLE).insert(payload).execute()

    def _update(client: Client):
        return (
            client.table(_CONVERSATIONS_TABLE)
            .update(payload)
            .eq("conversation_id", normalized["id"])
            .execute()
        )

    def _insert_or_update_on_conflict(client: Client):
        try:
            return _insert(client)
        except APIError as error:
            code = str(getattr(error, "code", "") or "")
            message = str(getattr(error, "message", "") or "")
            if code == "23505" or "duplicate key value violates unique constraint" in message.lower():
                return _update(client)
            raise

    def _shared_call():
        existing = _select_existing(supabase_client)
        if existing.data:
            return _update(supabase_client)
        return _insert_or_update_on_conflict(supabase_client)

    def _per_call():
        client = clone_supabase_client_with_same_auth(supabase_client) or supabase_client
        existing = _select_existing(client)
        if existing.data:
            return _update(client)
        return _insert_or_update_on_conflict(client)

    result = await run_db_blocking(_shared_call, per_call_client_call=_per_call)
    rows = result.data or []
    if rows:
        return _normalize_conversation_record(rows[0])
    return normalized


async def delete_conversation(*, supabase_client: Client, conversation_id: str) -> Dict[str, Any]:
    normalized_id = str(conversation_id or "").strip()
    if not normalized_id:
        raise ValueError("conversation id is required")

    def _shared_call():
        return (
            supabase_client.table(_CONVERSATIONS_TABLE)
            .delete()
            .eq("conversation_id", normalized_id)
            .execute()
        )

    def _per_call():
        client = clone_supabase_client_with_same_auth(supabase_client) or supabase_client
        return client.table(_CONVERSATIONS_TABLE).delete().eq("conversation_id", normalized_id).execute()

    result = await run_db_blocking(_shared_call, per_call_client_call=_per_call)
    deleted = bool(result.data)
    return {"deleted": deleted, "conversation_id": normalized_id}
