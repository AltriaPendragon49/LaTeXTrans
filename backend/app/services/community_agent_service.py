from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.policies import authorize
from backend.app.services.community_agent import run_agent
from backend.app.repositories import CommunityAgentConversationRepository
from backend.app.repositories.community_agent_repository import CommunityAgentRunRepository
from backend.app.utils.async_blocking import run_blocking

_RUNTIME_AGENT_RUNS: Dict[str, "_RunRecord"] = {}


class RunNotFoundError(KeyError):
    """Raised when an agent run cannot be found."""


@dataclass
class _RunRecord:
    run_id: str
    owner_user_id: str | None
    conversation_id: str | None = None
    status: str = "queued"
    intent: str = "answer"
    mode: str = "chat"
    message: str | None = None
    summary: str | None = None
    tool_trace: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    provider_state: Dict[str, str] | None = None
    action: Dict[str, Any] | None = None
    report: Dict[str, Any] | None = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    completed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    thread: threading.Thread | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_provider_state() -> Dict[str, str]:
    return {
        "internal_search": "enabled",
        "external_search": "unknown",
        "reasoning": "unknown",
        "translation_bridge": "enabled",
    }


def _should_persist_run(record: _RunRecord) -> bool:
    return bool(record.owner_user_id)


def _authorize_run_access(
    *,
    actor_user_id: str | None,
    owner_user_id: str | None,
    action: str,
) -> None:
    actor = {"id": actor_user_id, "roles": []} if actor_user_id else None
    context: Dict[str, Any] = {}
    if owner_user_id:
        context["owner_user_id"] = owner_user_id
    decision = authorize(
        actor,
        "community_run",
        action,
        context,
    )
    if not decision.allowed:
        raise PermissionError(decision.reason)


def _save_run_to_repository(record: _RunRecord) -> None:
    if not _should_persist_run(record):
        return
    with record.lock:
        payload = {
            "run_id": record.run_id,
            "user_id": record.owner_user_id,
            "conversation_id": record.conversation_id,
            "status": record.status,
            "intent": record.intent,
            "mode": record.mode,
            "message": record.message,
            "summary": record.summary,
            "error": record.error,
            "report": record.report if isinstance(record.report, dict) else None,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "completed_at": record.completed_at,
        }
    try:
        CommunityAgentRunRepository().upsert_run(payload)
    except Exception:
        return


def _save_event_to_repository(record: _RunRecord, event: Dict[str, Any]) -> None:
    if not _should_persist_run(record):
        return
    try:
        CommunityAgentRunRepository().append_event(
            record.run_id,
            int(event.get("sequence") or 0),
            event,
        )
    except Exception:
        return


def _load_run_record_from_repository(
    run_id: str,
    *,
    owner_user_id: str | None,
) -> _RunRecord | None:
    if not owner_user_id:
        return None

    try:
        repository = CommunityAgentRunRepository()
        row = repository.get_run(run_id)
    except Exception:
        return None

    if row is None:
        return None

    expected_owner = str(row.get("user_id") or "").strip()
    _authorize_run_access(
        actor_user_id=owner_user_id,
        owner_user_id=expected_owner or None,
        action="read",
    )

    try:
        events = repository.list_events(run_id)
    except Exception:
        events = []

    snapshot: Dict[str, Any] | None = None
    for event in reversed(events):
        if str(event.get("type") or "") != "complete":
            continue
        data = event.get("data")
        if not isinstance(data, dict):
            continue
        loaded = data.get("snapshot")
        if isinstance(loaded, dict):
            snapshot = loaded
            break

    report = row.get("report") if isinstance(row.get("report"), dict) else None
    if snapshot and isinstance(snapshot.get("report"), dict):
        report = dict(snapshot["report"])

    status = str(row.get("status") or (snapshot or {}).get("status") or "failed")
    completed_at = str(row.get("completed_at") or "").strip() or None
    completed = bool(completed_at or status in {"completed", "failed"})

    return _RunRecord(
        run_id=str(row.get("run_id") or run_id),
        owner_user_id=expected_owner,
        conversation_id=str(row.get("conversation_id") or "").strip() or None,
        status=status,
        intent=str(row.get("intent") or (snapshot or {}).get("intent") or "answer"),
        mode=str(row.get("mode") or (snapshot or {}).get("mode") or "chat"),
        message=row.get("message") or (snapshot or {}).get("message"),
        summary=row.get("summary") or (snapshot or {}).get("summary"),
        tool_trace=list((snapshot or {}).get("tool_trace") or []),
        citations=list((snapshot or {}).get("citations") or []),
        provider_state=dict((snapshot or {}).get("provider_state") or _default_provider_state()),
        action=(snapshot or {}).get("action") if isinstance((snapshot or {}).get("action"), dict) else None,
        report=report,
        events=list(events),
        error=row.get("error"),
        completed=completed,
        created_at=str(row.get("created_at") or "") or _now_iso(),
        updated_at=str(row.get("updated_at") or "") or _now_iso(),
        completed_at=completed_at,
    )


def _build_snapshot(record: _RunRecord, *, include_urls: bool = False) -> Dict[str, Any]:
    with record.lock:
        payload = {
            "run_id": record.run_id,
            "status": record.status,
            "intent": record.intent,
            "mode": record.mode,
            "message": record.message,
            "summary": record.summary,
            "tool_trace": list(record.tool_trace),
            "citations": list(record.citations),
            "provider_state": dict(record.provider_state or _default_provider_state()),
            "action": dict(record.action) if isinstance(record.action, dict) else record.action,
            "report": dict(record.report) if isinstance(record.report, dict) else record.report,
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
    _save_event_to_repository(record, payload)
    return payload


def _set_status(record: _RunRecord, status: str, *, phase: str | None = None) -> None:
    with record.lock:
        record.status = status
        record.updated_at = _now_iso()
        if status in {"completed", "failed"} and not record.completed_at:
            record.completed_at = record.updated_at
            record.completed = True
    _save_run_to_repository(record)
    data: Dict[str, Any] = {"status": status}
    if phase:
        data["phase"] = phase
    _publish_stream_event(record, {"type": "status", "data": data})


def _require_run_record(
    run_id: str,
    *,
    owner_user_id: str | None = None,
    access_token: str | None = None,
) -> _RunRecord:
    del access_token
    record = _RUNTIME_AGENT_RUNS.get(run_id)
    if record is None:
        record = _load_run_record_from_repository(
            run_id,
            owner_user_id=owner_user_id,
        )
        if record is None:
            raise KeyError(run_id)
        _RUNTIME_AGENT_RUNS[run_id] = record

    expected_owner_user_id = record.owner_user_id
    if expected_owner_user_id:
        _authorize_run_access(
            actor_user_id=owner_user_id,
            owner_user_id=expected_owner_user_id,
            action="read",
        )
    return record


async def _run_agent_once(
    record: _RunRecord,
    *,
    input_text: str,
    context: Dict[str, Any] | None,
    skill_toggles: Dict[str, Any] | None,
    run_mode: str,
) -> None:
    try:
        _set_status(record, "running", phase="planner")
        payload = await run_agent(
            input_text=input_text,
            context=context,
            skill_toggles=skill_toggles,
            run_mode=run_mode,
            event_callback=lambda event: _publish_stream_event(record, event),
        )
    except Exception as exc:
        with record.lock:
            record.status = "failed"
            record.intent = "answer"
            record.mode = run_mode
            record.message = str(exc)
            record.summary = str(exc)
            record.provider_state = _default_provider_state()
            record.report = None
            record.error = str(exc)
            record.completed = True
            record.updated_at = _now_iso()
            record.completed_at = record.updated_at
        _save_run_to_repository(record)
        _publish_stream_event(record, {"type": "error", "data": {"message": str(exc)}})
        _publish_stream_event(record, {"type": "complete", "data": {"snapshot": _build_snapshot(record)}})
        return

    with record.lock:
        record.status = str(payload.get("status") or "completed")
        record.intent = str(payload.get("intent") or "answer")
        record.mode = str(payload.get("mode") or run_mode)
        record.message = payload.get("message") or payload.get("summary")
        record.summary = payload.get("summary") or payload.get("message")
        record.tool_trace = list(payload.get("tool_trace") or [])
        record.citations = list(payload.get("citations") or [])
        record.provider_state = dict(payload.get("provider_state") or _default_provider_state())
        record.action = payload.get("action") if isinstance(payload.get("action"), dict) else payload.get("action")
        record.report = payload.get("report") if isinstance(payload.get("report"), dict) else None
        record.completed = True
        record.updated_at = _now_iso()
        record.completed_at = record.updated_at
    _save_run_to_repository(record)

    _publish_stream_event(record, {"type": "complete", "data": {"snapshot": _build_snapshot(record)}})


def _start_background_run(
    record: _RunRecord,
    *,
    input_text: str,
    context: Dict[str, Any] | None,
    skill_toggles: Dict[str, Any] | None,
    run_mode: str,
) -> None:
    def _runner() -> None:
        asyncio.run(
            _run_agent_once(
                record,
                input_text=input_text,
                context=context,
                skill_toggles=skill_toggles,
                run_mode=run_mode,
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
    run_mode: str = "chat",
    owner_user_id: str | None = None,
    access_token: str | None = None,
) -> Dict[str, Any]:
    del access_token
    run_id = f"run-{uuid.uuid4().hex[:10]}"
    trusted_context = dict(context or {})
    if owner_user_id:
        trusted_context["user_id"] = owner_user_id
    conversation_id = str(trusted_context.get("conversation_id") or "").strip() or None

    record = _RunRecord(
        run_id=run_id,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        mode=run_mode,
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
    _save_run_to_repository(record)

    if execution_mode == "async":
        _set_status(record, "accepted", phase="accepted")
        _start_background_run(
            record,
            input_text=input_text,
            context=trusted_context,
            skill_toggles=skill_toggles,
            run_mode=run_mode,
        )
        return _build_snapshot(record, include_urls=True)

    await _run_agent_once(
        record,
        input_text=input_text,
        context=trusted_context,
        skill_toggles=skill_toggles,
        run_mode=run_mode,
    )
    return _build_snapshot(record)


async def get_agent_run(
    run_id: str,
    *,
    owner_user_id: str | None = None,
    access_token: str | None = None,
    strict: bool = False,
) -> Dict[str, Any]:
    try:
        record = _require_run_record(
            run_id,
            owner_user_id=owner_user_id,
            access_token=access_token,
        )
    except KeyError:
        if strict:
            raise RunNotFoundError(run_id)
        return {
            "run_id": run_id,
            "status": "failed",
            "intent": "answer",
            "mode": "chat",
            "message": None,
            "summary": None,
            "tool_trace": [],
            "citations": [],
            "provider_state": _default_provider_state(),
            "action": None,
            "report": None,
            "events": [],
        }
    return _build_snapshot(record)


async def stream_agent_events(
    run_id: str,
    *,
    owner_user_id: str | None = None,
    access_token: str | None = None,
) -> List[Dict[str, Any]]:
    record = _require_run_record(
        run_id,
        owner_user_id=owner_user_id,
        access_token=access_token,
    )
    with record.lock:
        return list(record.events)


async def wait_for_new_events(
    run_id: str,
    *,
    last_sequence: int,
    owner_user_id: str | None = None,
    access_token: str | None = None,
    timeout: float = 15.0,
) -> List[Dict[str, Any]]:
    record = _require_run_record(
        run_id,
        owner_user_id=owner_user_id,
        access_token=access_token,
    )
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


async def list_conversations(*, owner_user_id: str) -> List[Dict[str, Any]]:
    repository = CommunityAgentConversationRepository()
    return await run_blocking(lambda: repository.list_conversations_for_user(owner_user_id))


async def upsert_conversation(*, owner_user_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_conversation_record(record)
    if not normalized["id"]:
        raise ValueError("conversation id is required")
    repository = CommunityAgentConversationRepository()
    return await run_blocking(
        lambda: repository.upsert_conversation_for_user(owner_user_id, normalized)
    )


async def delete_conversation(*, owner_user_id: str, conversation_id: str) -> Dict[str, Any]:
    normalized_id = str(conversation_id or "").strip()
    if not normalized_id:
        raise ValueError("conversation id is required")
    repository = CommunityAgentConversationRepository()
    deleted = await run_blocking(
        lambda: repository.delete_conversation_for_user(owner_user_id, normalized_id)
    )
    return {"deleted": deleted, "conversation_id": normalized_id}
