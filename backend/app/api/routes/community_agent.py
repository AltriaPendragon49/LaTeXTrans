from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.app.core.auth import require_current_user
from backend.app.policies import authorize
from backend.app.services import community_agent_service

router = APIRouter(prefix="/community-agent")


class CommunityAgentSkillToggles(BaseModel):
    external_search: bool = False


class CommunityAgentRunRequest(BaseModel):
    input: str
    paper_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    skill_toggles: Optional[CommunityAgentSkillToggles] = None
    execution_mode: Literal["blocking", "async"] = "blocking"
    mode: Literal["chat", "deep_research"] = "chat"


class CommunityConversationTurnPayload(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: str
    run: Optional[Dict[str, Any]] = None
    status: Optional[str] = "completed"
    error: Optional[str] = None


class CommunityConversationRecordPayload(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    turns: List[CommunityConversationTurnPayload] = Field(default_factory=list)


class CommunityConversationDeleteResponse(BaseModel):
    deleted: bool
    conversation_id: str


class CommunityAgentRunResponse(BaseModel):
    run_id: str
    status: str
    intent: Optional[str] = None
    mode: Literal["chat", "deep_research"] = "chat"
    message: Optional[str] = None
    summary: Optional[str] = None
    tool_trace: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    provider_state: Optional[Dict[str, str]] = None
    action: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    stream_url: Optional[str] = None
    result_url: Optional[str] = None


def _ensure_community_agent_authorized(
    current_user: Dict[str, Any],
    *,
    resource: str,
    action: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    decision = authorize(
        current_user,
        resource,
        action,
        context or {},
    )
    if decision.allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=decision.reason,
    )


@router.post("/runs", response_model=CommunityAgentRunResponse)
async def create_agent_run(
    request: CommunityAgentRunRequest,
    current_user: Dict[str, Any] = Depends(require_current_user),
):
    _ensure_community_agent_authorized(
        current_user,
        resource="community_run",
        action="create",
        context={"owner_user_id": str(current_user.get("id") or "")},
    )
    if not request.input.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="input is required")

    context = dict(request.context or {})
    if request.paper_id:
        context["paper_id"] = request.paper_id

    payload = await community_agent_service.create_agent_run(
        input_text=request.input,
        context=context,
        skill_toggles=request.skill_toggles.model_dump() if request.skill_toggles else None,
        execution_mode=request.execution_mode,
        run_mode=request.mode,
        owner_user_id=str(current_user["id"]),
    )
    if request.execution_mode == "async":
        return JSONResponse(
            content=payload,
            status_code=status.HTTP_202_ACCEPTED,
        )
    return payload


@router.get("/conversations", response_model=List[CommunityConversationRecordPayload])
async def list_agent_conversations(
    current_user: Dict[str, Any] = Depends(require_current_user),
):
    _ensure_community_agent_authorized(
        current_user,
        resource="community_conversation",
        action="read",
        context={"owner_user_id": str(current_user.get("id") or "")},
    )
    return await community_agent_service.list_conversations(
        owner_user_id=str(current_user["id"]),
    )


@router.put("/conversations/{conversation_id}", response_model=CommunityConversationRecordPayload)
async def upsert_agent_conversation(
    conversation_id: str,
    request: CommunityConversationRecordPayload,
    current_user: Dict[str, Any] = Depends(require_current_user),
):
    _ensure_community_agent_authorized(
        current_user,
        resource="community_conversation",
        action="update",
        context={"owner_user_id": str(current_user.get("id") or "")},
    )
    if request.id != conversation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="conversation id mismatch")

    return await community_agent_service.upsert_conversation(
        owner_user_id=str(current_user["id"]),
        record=request.model_dump(),
    )


@router.delete("/conversations/{conversation_id}", response_model=CommunityConversationDeleteResponse)
async def delete_agent_conversation(
    conversation_id: str,
    current_user: Dict[str, Any] = Depends(require_current_user),
):
    _ensure_community_agent_authorized(
        current_user,
        resource="community_conversation",
        action="delete",
        context={"owner_user_id": str(current_user.get("id") or "")},
    )
    return await community_agent_service.delete_conversation(
        owner_user_id=str(current_user["id"]),
        conversation_id=conversation_id,
    )


@router.get("/runs/{run_id}", response_model=CommunityAgentRunResponse)
async def get_agent_run(
    run_id: str,
    current_user: Dict[str, Any] = Depends(require_current_user),
):
    _ensure_community_agent_authorized(
        current_user,
        resource="community_run",
        action="read",
        context={"owner_user_id": str(current_user.get("id") or "")},
    )
    try:
        return await community_agent_service.get_agent_run(
            run_id,
            owner_user_id=str(current_user["id"]),
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get("/runs/{run_id}/events")
async def stream_agent_events(
    run_id: str,
    current_user: Dict[str, Any] = Depends(require_current_user),
):
    _ensure_community_agent_authorized(
        current_user,
        resource="community_run",
        action="read",
        context={"owner_user_id": str(current_user.get("id") or "")},
    )
    owner_user_id = str(current_user["id"])

    async def _event_stream():
        last_sequence = 0
        heartbeat_interval = 15.0
        try:
            while True:
                events = await community_agent_service.wait_for_new_events(
                    run_id,
                    last_sequence=last_sequence,
                    owner_user_id=owner_user_id,
                    timeout=heartbeat_interval,
                )
                if not events:
                    yield f"event: heartbeat\ndata: {json.dumps({'type': 'heartbeat'})}\n\n"
                for event in events:
                    last_sequence = int(event.get("sequence") or last_sequence)
                    yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

                snapshot = await community_agent_service.get_agent_run(
                    run_id,
                    owner_user_id=owner_user_id,
                )
                if snapshot.get("status") in {"completed", "failed"}:
                    all_events = await community_agent_service.stream_agent_events(
                        run_id,
                        owner_user_id=owner_user_id,
                    )
                    if last_sequence >= len(all_events):
                        break
        except PermissionError as exc:
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
