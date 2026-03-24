from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from postgrest.exceptions import APIError
from supabase import Client

from backend.app.services import paper_service
from backend.app.services.community_agent import run_agent
from backend.app.core.auth import clone_supabase_client_with_same_auth
from backend.app.utils.async_blocking import run_db_blocking

_RUNTIME_AGENT_RUNS: Dict[str, Dict[str, Any]] = {}
_CONVERSATIONS_TABLE = "community_agent_conversations"


async def create_agent_run(
    input_text: str,
    context: Dict[str, Any] | None = None,
    skill_toggles: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload = await run_agent(input_text=input_text, context=context, skill_toggles=skill_toggles)
    run_id = f"run-{payload.get('intent', 'answer')}-{uuid.uuid4().hex[:10]}"
    finalized = {
        "run_id": run_id,
        "status": payload.get("status", "completed"),
        "intent": payload.get("intent", "answer"),
        "message": payload.get("message") or payload.get("summary"),
        "summary": payload.get("summary") or payload.get("message"),
        "tool_trace": payload.get("tool_trace") or [],
        "citations": payload.get("citations") or [],
        "provider_state": payload.get("provider_state"),
        "action": payload.get("action"),
        "events": payload.get("events") or [],
    }
    _RUNTIME_AGENT_RUNS[run_id] = finalized
    return finalized


async def get_agent_run(run_id: str) -> Dict[str, Any]:
    payload = _RUNTIME_AGENT_RUNS.get(run_id)
    if payload:
        return payload
    return {
        "run_id": run_id,
        "status": "failed",
        "intent": "answer",
        "message": None,
        "summary": None,
        "tool_trace": [],
        "citations": [],
        "provider_state": {
            "internal_search": "enabled",
            "external_search": "unknown",
            "reasoning": "unknown",
            "translation_bridge": "enabled",
        },
        "action": None,
        "events": [],
    }


async def stream_agent_events(run_id: str) -> List[Dict[str, Any]]:
    payload = await get_agent_run(run_id)
    events = payload.get("events")
    return events if isinstance(events, list) else []


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
