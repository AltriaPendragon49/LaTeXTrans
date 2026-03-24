from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from supabase import Client

from backend.app.core.auth import get_supabase_client_from_request
from backend.app.services import community_agent_service

router = APIRouter(prefix="/community-agent")


class CommunityAgentSkillToggles(BaseModel):
    external_search: bool = False


class CommunityAgentRunRequest(BaseModel):
    input: str
    paper_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    skill_toggles: Optional[CommunityAgentSkillToggles] = None


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
    intent: str
    message: Optional[str] = None
    summary: Optional[str] = None
    tool_trace: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    provider_state: Optional[Dict[str, str]] = None
    action: Optional[Dict[str, Any]] = None


@router.post("/runs", response_model=CommunityAgentRunResponse)
async def create_agent_run(
    request: CommunityAgentRunRequest,
    supabase: Optional[Client] = Depends(get_supabase_client_from_request),
):
    if not request.input.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="input is required")
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    context = dict(request.context or {})
    if request.paper_id:
        context["paper_id"] = request.paper_id

    payload = await community_agent_service.create_agent_run(
        input_text=request.input,
        context=context,
        skill_toggles=request.skill_toggles.model_dump() if request.skill_toggles else None,
    )
    return payload


@router.get("/conversations", response_model=List[CommunityConversationRecordPayload])
async def list_agent_conversations(
    supabase: Optional[Client] = Depends(get_supabase_client_from_request),
):
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await community_agent_service.list_conversations(supabase_client=supabase)


@router.put("/conversations/{conversation_id}", response_model=CommunityConversationRecordPayload)
async def upsert_agent_conversation(
    conversation_id: str,
    request: CommunityConversationRecordPayload,
    supabase: Optional[Client] = Depends(get_supabase_client_from_request),
):
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if request.id != conversation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="conversation id mismatch")

    return await community_agent_service.upsert_conversation(
        supabase_client=supabase,
        record=request.model_dump(),
    )


@router.delete("/conversations/{conversation_id}", response_model=CommunityConversationDeleteResponse)
async def delete_agent_conversation(
    conversation_id: str,
    supabase: Optional[Client] = Depends(get_supabase_client_from_request),
):
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await community_agent_service.delete_conversation(
        supabase_client=supabase,
        conversation_id=conversation_id,
    )


@router.get("/runs/{run_id}", response_model=CommunityAgentRunResponse)
async def get_agent_run(run_id: str):
    return await community_agent_service.get_agent_run(run_id)


@router.get("/runs/{run_id}/events")
async def stream_agent_events(run_id: str):
    events = await community_agent_service.stream_agent_events(run_id)

    async def _event_stream():
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.03)

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
