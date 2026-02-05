"""
Task Status API Routes

Provides endpoints for querying task status and progress.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

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
