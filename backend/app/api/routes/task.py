"""Task status routes with guest-safe access and authenticated ownership checks."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import asyncio
import json
from datetime import datetime

from backend.app.core.auth import optional_current_user
from backend.app.policies import authorize
from backend.app.repositories import TranslationTaskRepository
from backend.app.services.task_manager import get_task_manager

logger = logging.getLogger(__name__)
router = APIRouter()
task_manager = get_task_manager()


class TaskStatusResponse(BaseModel):
    """Task status response"""
    task_id: str
    status: str
    progress: int
    stage: str
    message: str
    detail_code: Optional[str] = None
    detail_params: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    warnings: Optional[str] = None
    failure_reason_code: Optional[str] = None
    failure_class: Optional[str] = None
    guard_phase: Optional[str] = None
    replay_bundle_ref: Optional[str] = None
    evidence_chain_broken: Optional[bool] = None
    source_available: bool
    created_at: str
    completed_at: Optional[str] = None
    advanced_config: Optional[Dict[str, Any]] = None
    persist_failed: bool = False


def get_translation_task_repository() -> TranslationTaskRepository:
    return TranslationTaskRepository()


def _resolve_translation_task_repository() -> TranslationTaskRepository:
    return get_translation_task_repository()


def _serialize_optional_timestamp(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _is_guest_task(task: Dict[str, Any]) -> bool:
    return not str(task.get("user_id") or "").strip()


def _authorize_authenticated_task(
    *,
    task: Dict[str, Any],
    current_user: Optional[Dict[str, Any]],
    action: str,
) -> None:
    owner_user_id = str(task.get("user_id") or "").strip() or None
    decision = authorize(
        current_user,
        "task",
        action,
        {"owner_user_id": owner_user_id},
    )
    if decision.allowed:
        return
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_SESSION_INVALID", "message": decision.reason},
            headers={"WWW-Authenticate": "Bearer"},
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "AUTH_FORBIDDEN", "message": decision.reason},
    )


def _load_authorized_task(
    *,
    task_id: str,
    current_user: Optional[Dict[str, Any]],
    action: str,
) -> Dict[str, Any]:
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    if _is_guest_task(task):
        return task
    _authorize_authenticated_task(task=task, current_user=current_user, action=action)
    return task


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
):
    """
    Get task status and progress
    
    Args:
        task_id: Task ID
    
    Returns:
        Task status information
    
    Raises:
        HTTPException: If task not found
    """
    logger.info(f"Getting status for task: {task_id}")
    
    task = _load_authorized_task(task_id=task_id, current_user=current_user, action="view")
    
    return TaskStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        stage=task["stage"],
        message=task["message"],
        detail_code=task.get("detail_code"),
        detail_params=task.get("detail_params"),
        error=task.get("error"),
        warnings=task.get("warnings"),
        failure_reason_code=task.get("failure_reason_code"),
        failure_class=task.get("failure_class"),
        guard_phase=task.get("guard_phase"),
        replay_bundle_ref=task.get("replay_bundle_ref"),
        evidence_chain_broken=task.get("evidence_chain_broken"),
        source_available=task["source_available"],
        created_at=_serialize_optional_timestamp(task["created_at"]) or "",
        completed_at=_serialize_optional_timestamp(task.get("completed_at")),
        advanced_config=task.get("advanced_config"),
        persist_failed=bool(task.get("persist_failed")),
    )


@router.get("/tasks")
async def list_all_tasks():
    """
    List all tasks (for debugging)
    
    Returns:
        Dictionary of all tasks
    """
    logger.info("Listing all tasks")
    return task_manager.get_all_tasks()


@router.delete("/task/{task_id}")
async def delete_task(
    task_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    repository: TranslationTaskRepository = Depends(_resolve_translation_task_repository),
):
    """
    Delete a task
    
    Args:
        task_id: Task ID
    
    Returns:
        Deletion status
    
    Raises:
        HTTPException: If task not found
    """
    logger.info(f"Deleting task: {task_id}")
    
    task = _load_authorized_task(task_id=task_id, current_user=current_user, action="delete")
    owner_user_id = str(task.get("user_id") or "").strip() or None

    if owner_user_id:
        requester_id = str((current_user or {}).get("id") or "").strip()
        if requester_id and requester_id == owner_user_id:
            repository.delete_task_for_user(requester_id, task_id)
        else:
            repository.delete_task(task_id)

    deletion_result = task_manager.delete_task_full(task_id)
    
    return {
        "task_id": task_id,
        "status": "deleted",
        "message": "Task deleted successfully",
        "deleted_dirs": deletion_result.get("deleted_dirs", []),
        "errors": deletion_result.get("errors", []),
    }


@router.get("/task/{task_id}/stream")
async def stream_task_status(
    task_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
):
    """
    SSE endpoint for real-time task status updates.
    
    Streams task status updates to the client using Server-Sent Events.
    Automatically closes when task reaches terminal state (completed/failed).
    
    Args:
        task_id: Task ID to monitor
        
    Returns:
        StreamingResponse with SSE events
        
    Raises:
        HTTPException: If task not found
    """
    # Validate task exists
    _load_authorized_task(task_id=task_id, current_user=current_user, action="view")
    
    async def event_generator():
        """Generate SSE events for task status updates."""
        last_progress = -1
        last_status = ""
        heartbeat_interval = 15  # seconds
        poll_interval = 0.5  # seconds
        heartbeat_counter = 0
        
        try:
            while True:
                try:
                    task = _load_authorized_task(task_id=task_id, current_user=current_user, action="view")
                except HTTPException as exc:
                    if exc.status_code == 404:
                        event_data = {
                            "type": "deleted",
                            "task_id": task_id,
                            "message": "Task was deleted"
                        }
                        yield f"event: deleted\ndata: {json.dumps(event_data)}\n\n"
                        break
                    if exc.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
                        error_data = {"type": "error", "message": "Task access denied"}
                        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                        break
                    raise
                
                current_progress = task.get("progress", 0)
                current_status = task.get("status", "")
                current_stage = task.get("stage", "")
                current_message = task.get("message", "")
                
                # Send update if progress or status changed
                if current_progress != last_progress or current_status != last_status:
                    event_data = {
                        "type": "update",
                        "task_id": task_id,
                        "status": current_status,
                        "progress": current_progress,
                        "stage": current_stage,
                        "message": current_message,
                        "detail_code": task.get("detail_code"),
                        "detail_params": task.get("detail_params"),
                        "error": task.get("error"),
                        "warnings": task.get("warnings"),
                        "failure_reason_code": task.get("failure_reason_code"),
                        "failure_class": task.get("failure_class"),
                        "guard_phase": task.get("guard_phase"),
                        "replay_bundle_ref": task.get("replay_bundle_ref"),
                        "evidence_chain_broken": task.get("evidence_chain_broken"),
                        "source_available": task.get("source_available", False),
                        "persist_failed": bool(task.get("persist_failed")),
                    }
                    yield f"event: update\ndata: {json.dumps(event_data)}\n\n"
                    
                    last_progress = current_progress
                    last_status = current_status
                    heartbeat_counter = 0  # Reset heartbeat after update
                
                # Check for terminal states
                if current_status in ("completed", "completed_with_warnings", "failed_compilation", "structure_invalid", "failed"):
                    event_data = {
                        "type": "complete",
                        "task_id": task_id,
                        "status": current_status,
                        "progress": current_progress,
                        "stage": current_stage,
                        "message": current_message,
                        "detail_code": task.get("detail_code"),
                        "detail_params": task.get("detail_params"),
                        "failure_reason_code": task.get("failure_reason_code"),
                        "failure_class": task.get("failure_class"),
                        "guard_phase": task.get("guard_phase"),
                        "replay_bundle_ref": task.get("replay_bundle_ref"),
                        "evidence_chain_broken": task.get("evidence_chain_broken"),
                        "persist_failed": bool(task.get("persist_failed")),
                    }
                    yield f"event: complete\ndata: {json.dumps(event_data)}\n\n"
                    break
                
                # Send heartbeat to keep connection alive
                heartbeat_counter += poll_interval
                if heartbeat_counter >= heartbeat_interval:
                    yield f"event: heartbeat\ndata: {json.dumps({'type': 'heartbeat'})}\n\n"
                    heartbeat_counter = 0
                
                await asyncio.sleep(poll_interval)
                
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for task: {task_id}")
            raise
        except Exception as e:
            logger.error(f"SSE stream error for task {task_id}: {e}")
            error_data = {"type": "error", "message": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    
    logger.info(f"Starting SSE stream for task: {task_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
