"""
Task Manager Service

In-memory task status tracking with thread-safe operations.
Manages task state, progress updates, and status queries.
"""

import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from backend.app.core.config import TaskStatus, CompilationStage


class TaskManager:
    """
    Thread-safe in-memory task manager for tracking translation tasks
    """
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_task(self, source_type: str = "upload") -> str:
        """
        Create a new task and return its ID
        
        Args:
            source_type: "upload" or "arxiv"
        
        Returns:
            Task ID (UUID string)
        """
        task_id = str(uuid.uuid4())
        
        with self._lock:
            self._tasks[task_id] = {
                "task_id": task_id,
                "status": TaskStatus.PENDING.value,
                "progress": 0,
                "stage": CompilationStage.IDLE.value,
                "message": "Task created",
                "error": None,
                "warnings": None,
                "source_available": False,
                "created_at": datetime.utcnow().isoformat(),
                "completed_at": None,
                "source_type": source_type,
                "source_path": None,
                "output_path": None
            }
        
        return task_id
    
    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        warnings: Optional[str] = None,
        source_available: Optional[bool] = None,
        source_path: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> bool:
        """
        Update task fields
        
        Args:
            task_id: Task ID
            status: New status (optional)
            progress: Progress percentage 0-100 (optional)
            stage: Current stage (optional)
            message: Status message (optional)
            error: Error message (optional)
            warnings: Warning message (optional)
            source_available: Whether source is available (optional)
            source_path: Path to source files (optional)
            output_path: Path to output files (optional)
        
        Returns:
            True if task exists and was updated, False otherwise
        """
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            
            if status is not None:
                task["status"] = status
                # Auto-complete timestamp
                if status in [TaskStatus.COMPLETED.value, 
                             TaskStatus.COMPLETED_WITH_WARNINGS.value, 
                             TaskStatus.FAILED.value,
                             TaskStatus.FAILED_COMPILATION.value]:
                    task["completed_at"] = datetime.utcnow().isoformat()
            
            if progress is not None:
                task["progress"] = max(0, min(100, progress))
            
            if stage is not None:
                task["stage"] = stage
            
            if message is not None:
                task["message"] = message
            
            if error is not None:
                task["error"] = error
            
            if warnings is not None:
                task["warnings"] = warnings
            
            if source_available is not None:
                task["source_available"] = source_available
            
            if source_path is not None:
                task["source_path"] = source_path
            
            if output_path is not None:
                task["output_path"] = output_path
            
            return True
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID
        
        Args:
            task_id: Task ID
        
        Returns:
            Task dictionary or None if not found
        """
        with self._lock:
            return self._tasks.get(task_id, None).copy() if task_id in self._tasks else None
    
    def task_exists(self, task_id: str) -> bool:
        """Check if task exists"""
        with self._lock:
            return task_id in self._tasks
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task
        
        Args:
            task_id: Task ID
        
        Returns:
            True if task was deleted, False if not found
        """
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all tasks (for debugging)"""
        with self._lock:
            return {k: v.copy() for k, v in self._tasks.items()}
    
    def create_progress_callback(self, task_id: str) -> Callable:
        """
        Create a progress callback function for a specific task
        
        Args:
            task_id: Task ID
        
        Returns:
            Callback function with signature: on_progress(stage, percentage, message)
        """
        def on_progress(stage: str, percentage: int, message: str):
            """Progress callback"""
            self.update_task(
                task_id=task_id,
                status=TaskStatus.PROCESSING.value,
                progress=percentage,
                stage=stage,
                message=message
            )
        
        return on_progress


# Global task manager instance
task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """Get the global task manager instance"""
    return task_manager
