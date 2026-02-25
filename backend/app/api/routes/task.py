"""
Task Status API Routes

Provides endpoints for querying task status and progress.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import asyncio
import json

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
    error: Optional[str] = None
    warnings: Optional[str] = None
    source_available: bool
    created_at: str
    completed_at: Optional[str] = None
    advanced_config: Optional[Dict[str, Any]] = None


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
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
    
    # Get task from manager
    task = task_manager.get_task(task_id)
    
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    return TaskStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        stage=task["stage"],
        message=task["message"],
        error=task.get("error"),
        warnings=task.get("warnings"),
        source_available=task["source_available"],
        created_at=task["created_at"],
        completed_at=task.get("completed_at"),
        advanced_config=task.get("advanced_config")
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
async def delete_task(task_id: str):
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
    
    success = task_manager.delete_task(task_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    return {
        "task_id": task_id,
        "status": "deleted",
        "message": "Task deleted successfully"
    }


@router.get("/task/{task_id}/stream")
async def stream_task_status(task_id: str):
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
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    async def event_generator():
        """Generate SSE events for task status updates."""
        last_progress = -1
        last_status = ""
        heartbeat_interval = 15  # seconds
        poll_interval = 0.5  # seconds
        heartbeat_counter = 0
        
        try:
            while True:
                task = task_manager.get_task(task_id)
                
                if task is None:
                    # Task was deleted
                    event_data = {
                        "type": "deleted",
                        "task_id": task_id,
                        "message": "Task was deleted"
                    }
                    yield f"event: deleted\ndata: {json.dumps(event_data)}\n\n"
                    break
                
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
                        "error": task.get("error"),
                        "warnings": task.get("warnings"),
                        "source_available": task.get("source_available", False)
                    }
                    yield f"event: update\ndata: {json.dumps(event_data)}\n\n"
                    
                    last_progress = current_progress
                    last_status = current_status
                    heartbeat_counter = 0  # Reset heartbeat after update
                
                # Check for terminal states
                if current_status in ("completed", "completed_with_warnings", "failed_compilation", "failed"):
                    event_data = {
                        "type": "complete",
                        "task_id": task_id,
                        "status": current_status,
                        "progress": current_progress,
                        "message": current_message
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
