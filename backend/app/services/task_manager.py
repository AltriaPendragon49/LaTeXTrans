"""
Task Manager Service

In-memory task status tracking with thread-safe operations.
Manages task state, progress updates, and status queries.

Supports dual-layer storage:
- In-memory cache for all tasks (guest + authenticated)
- Supabase persistence for authenticated users only
"""

import uuid
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Union
from backend.app.core.config import TaskStatus, CompilationStage
from backend.app.core.supabase_client import get_supabase_admin_client

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Thread-safe in-memory task manager for tracking translation tasks
    """
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._cancelled_tasks: set = set()  # Track cancelled tasks
        self._lock = threading.Lock()
    
    def create_task(
        self, 
        source_type: str = "upload", 
        advanced_config: Optional[Dict[str, Any]] = None, 
        arxiv_id: Optional[str] = None,
        user_id: Optional[str] = None,
        source_language: str = "en",
        target_language: str = "zh",
        persist_to_db: bool = False
    ) -> str:
        """
        Create a new task and return its ID
        
        Args:
            source_type: "upload", "arxiv", or "folder_upload"
            advanced_config: Optional advanced configuration snapshot
            arxiv_id: arXiv paper ID (if applicable)
            user_id: User ID for authenticated users (enables persistence)
            source_language: Source language code
            target_language: Target language code
            persist_to_db: Whether to immediately persist to database (default: False)
        
        Returns:
            Task ID (UUID string)
        """
        task_id = str(uuid.uuid4())
        
        # 1. Create in-memory cache (for all tasks)
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
                "output_path": None,
                "advanced_config": advanced_config,
                "latex_validation": None,
                "arxiv_id": arxiv_id,
                "user_id": user_id,
                "source_language": source_language,
                "target_language": target_language
            }
        
        # 2. Persist to Supabase (only if persist_to_db=True and user is authenticated)
        if persist_to_db and user_id:
            self._persist_task_create(task_id, user_id, source_type, arxiv_id, 
                                      source_language, target_language, advanced_config)
        
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
        output_path: Optional[str] = None,
        advanced_config: Optional[Dict[str, Any]] = None,
        latex_validation: Optional[Dict[str, Any]] = None,
        arxiv_id: Optional[str] = None,
        user_id: Optional[str] = None
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
            advanced_config: Advanced config snapshot (optional)
            latex_validation: LaTeX validation result (optional)
            arxiv_id: arXiv paper ID (optional)
            user_id: User ID - if provided, sync to Supabase (optional)
        
        Returns:
            True if task exists and was updated, False otherwise
        """
        # Collect updates for Supabase sync
        db_updates = {}
        
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            
            if status is not None:
                task["status"] = status
                db_updates["status"] = status
                # Auto-complete timestamp
                if status in [TaskStatus.COMPLETED.value, 
                             TaskStatus.COMPLETED_WITH_WARNINGS.value, 
                             TaskStatus.FAILED.value,
                             TaskStatus.FAILED_COMPILATION.value]:
                    task["completed_at"] = datetime.utcnow().isoformat()
                    db_updates["completed_at"] = task["completed_at"]
            
            if progress is not None:
                task["progress"] = max(0, min(100, progress))
                db_updates["progress"] = task["progress"]
            
            if stage is not None:
                task["stage"] = stage
                db_updates["stage"] = stage
            
            if message is not None:
                task["message"] = message
                db_updates["message"] = message
            
            if error is not None:
                task["error"] = error
                db_updates["error"] = error
            
            if warnings is not None:
                task["warnings"] = warnings
            
            if source_available is not None:
                task["source_available"] = source_available
            
            if source_path is not None:
                task["source_path"] = source_path
                db_updates["source_path"] = source_path
            
            if output_path is not None:
                task["output_path"] = output_path
                db_updates["output_path"] = output_path
            
            if advanced_config is not None:
                task["advanced_config"] = advanced_config
                # Extract relevant fields for DB
                if isinstance(advanced_config, dict):
                    db_updates["translation_mode"] = advanced_config.get("translation_mode", "full")
                    db_updates["compile_strategy"] = advanced_config.get("compile_strategy", "auto")
                    db_updates["translation_model"] = advanced_config.get("translation_model")
                    db_updates["enable_verification"] = advanced_config.get("enable_verification", True)
                    db_updates["generate_glossary"] = advanced_config.get("generate_terminology_table", True)
                    db_updates["use_author_api"] = advanced_config.get("use_author_api", True)
                    db_updates["custom_base_url"] = advanced_config.get("custom_base_url")
                    db_updates["custom_api_key_encrypted"] = advanced_config.get("custom_api_key_encrypted")
            
            if latex_validation is not None:
                task["latex_validation"] = latex_validation
            
            if arxiv_id is not None:
                task["arxiv_id"] = arxiv_id
                db_updates["arxiv_id"] = arxiv_id
            
            # Get user_id from task if not provided
            if user_id is None:
                user_id = task.get("user_id")
        
        # Sync to Supabase if user_id exists and we have updates
        if user_id and db_updates:
            self._persist_task_update(task_id, db_updates)
        
        return True
    
    def persist_task_if_needed(self, task_id: str) -> bool:
        """
        如果任务还未持久化到数据库,则首次持久化
        用于延迟任务创建:上传/下载时只创建内存任务,翻译时才持久化
        
        Args:
            task_id: Task ID
            
        Returns:
            True if persisted (or already persisted), False if failed
        """
        task = self.get_task(task_id)
        if not task:
            logger.warning(f"[TaskManager] Cannot persist non-existent task: {task_id}")
            return False
        
        user_id = task.get("user_id")
        if not user_id:
            # Guest task, no need to persist
            return True
        
        # 调用持久化方法(会自动处理已存在的情况)
        try:
            self._persist_task_create(
                task_id=task_id,
                user_id=user_id,
                source_type=task.get("source_type", "upload"),
                arxiv_id=task.get("arxiv_id"),
                source_language=task.get("source_language", "en"),
                target_language=task.get("target_language", "zh"),
                advanced_config=task.get("advanced_config")
            )
            logger.info(f"[TaskManager] Persisted task {task_id} to database")
            return True
        except Exception as e:
            logger.error(f"[TaskManager] Failed to persist task {task_id}: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID
        
        First checks in-memory cache, then attempts recovery from:
        1. Supabase database (for authenticated users' tasks)
        2. Local filesystem (for guest tasks or when Supabase unavailable)
        
        Args:
            task_id: Task ID
        
        Returns:
            Task dictionary or None if not found
        """
        with self._lock:
            if task_id in self._tasks:
                return self._tasks.get(task_id, None).copy()
        
        # Task not in memory, try to recover from persistent storage
        recovered_task = self._recover_task_from_storage(task_id)
        if recovered_task:
            # Cache the recovered task
            with self._lock:
                self._tasks[task_id] = recovered_task
            logger.info(f"[TaskManager] Recovered task {task_id} from persistent storage")
            return recovered_task.copy()
        
        return None
    
    def task_exists(self, task_id: str) -> bool:
        """Check if task exists"""
        with self._lock:
            return task_id in self._tasks
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from memory cache only
        
        Args:
            task_id: Task ID
        
        Returns:
            True if task was deleted, False if not found
        """
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                # Also remove from cancelled set if present
                self._cancelled_tasks.discard(task_id)
                return True
            return False
    
    def is_cancelled(self, task_id: str) -> bool:
        """
        Check if a task has been cancelled
        
        Args:
            task_id: Task ID
        
        Returns:
            True if task is cancelled, False otherwise
        """
        with self._lock:
            return task_id in self._cancelled_tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Mark a task as cancelled (for interrupting running tasks)
        
        Args:
            task_id: Task ID
        
        Returns:
            True if task exists and was marked as cancelled
        """
        with self._lock:
            if task_id in self._tasks:
                self._cancelled_tasks.add(task_id)
                # Update task status to failed
                task = self._tasks[task_id]
                task["status"] = TaskStatus.FAILED.value
                task["message"] = "Task cancelled by user"
                return True
            return False
    
    def delete_task_full(self, task_id: str) -> Dict[str, Any]:
        """
        Delete task completely: memory cache + local filesystem
        
        This will delete:
        - data/uploads/{task_id}/
        - data/outputs/{task_id}/
        - data/terms/{task_id}/
        - Memory cache
        - Cancelled flag
        
        Note: Supabase deletion should be handled by the API layer (RLS)
        
        Args:
            task_id: Task ID
        
        Returns:
            Dictionary with deletion results:
            {
                "success": bool,
                "deleted_dirs": [list of deleted directories],
                "errors": [list of error messages]
            }
        """
        import shutil
        from pathlib import Path
        from backend.app.core.config import get_settings
        
        settings = get_settings()
        deleted_dirs = []
        errors = []
        
        # Define directories to delete
        # NOTE: uploads/ is now shared across tasks (arxiv_id-based), do not delete
        dirs_to_delete = [
            settings.outputs_dir / task_id,
            Path(settings.outputs_dir).parent / "terms" / task_id,  # data/terms/{task_id}
        ]
        
        # Delete each directory
        for dir_path in dirs_to_delete:
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    deleted_dirs.append(str(dir_path))
                    logger.info(f"[TaskManager] Deleted directory: {dir_path}")
                except Exception as e:
                    error_msg = f"Failed to delete {dir_path}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"[TaskManager] {error_msg}")
        
        # Delete from memory cache and cancelled set
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
            self._cancelled_tasks.discard(task_id)
        
        success = len(errors) == 0
        return {
            "success": success,
            "deleted_dirs": deleted_dirs,
            "errors": errors
        }
    
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
            Callback function with signature: on_progress(percentage, message)
        """
        def on_progress(percentage: int, message: str = ""):
            """Progress callback"""
            # Infer stage from progress percentage
            if percentage < 10:
                stage = CompilationStage.PARSING.value
            elif percentage < 70:
                stage = CompilationStage.TRANSLATING.value
            elif percentage < 100:
                stage = CompilationStage.COMPILING.value
            else:
                stage = CompilationStage.DONE.value
            
            self.update_task(
                task_id=task_id,
                status=TaskStatus.PROCESSING.value,
                progress=percentage,
                stage=stage,
                message=message
            )
        
        return on_progress
    
    def _persist_task_create(
        self, 
        task_id: str, 
        user_id: str, 
        source_type: str,
        arxiv_id: Optional[str],
        source_language: str,
        target_language: str,
        advanced_config: Optional[Dict[str, Any]]
    ):
        """
        Persist task creation to Supabase (authenticated users only)
        
        Args:
            task_id: Task ID
            user_id: User ID
            source_type: "upload" or "arxiv"
            arxiv_id: arXiv paper ID (if applicable)
            source_language: Source language code
            target_language: Target language code
            advanced_config: Advanced configuration snapshot
        """
        try:
            client = get_supabase_admin_client()
            if not client:
                logger.warning(f"[TaskManager] Supabase admin client not available, skipping persistence for task {task_id}")
                return
            
            # Build database record
            db_record = {
                "task_id": task_id,
                "user_id": user_id,
                "source_type": source_type,
                "arxiv_id": arxiv_id,
                "source_language": source_language,
                "target_language": target_language,
                "status": TaskStatus.PENDING.value,
                "progress": 0,
                "stage": CompilationStage.IDLE.value,
            }
            
            # Extract advanced config fields if available
            if advanced_config and isinstance(advanced_config, dict):
                db_record["translation_mode"] = advanced_config.get("translation_mode", "full")
                db_record["compile_strategy"] = advanced_config.get("compile_strategy", "auto")
                db_record["translation_model"] = advanced_config.get("translation_model")
                db_record["enable_verification"] = advanced_config.get("enable_verification", True)
                db_record["generate_glossary"] = advanced_config.get("generate_terminology_table", True)
                db_record["use_author_api"] = advanced_config.get("use_author_api", True)
                db_record["custom_base_url"] = advanced_config.get("custom_base_url")
                db_record["custom_api_key_encrypted"] = advanced_config.get("custom_api_key_encrypted")
            
            # Insert into database
            result = client.table("translation_tasks").insert(db_record).execute()
            logger.info(f"[TaskManager] ✅ Persisted task {task_id} to Supabase for user {user_id}")
        
        except Exception as e:
            logger.error(f"[TaskManager] Failed to persist task {task_id} to Supabase: {e}", exc_info=True)
    
    def _persist_task_update(self, task_id: str, updates: Dict[str, Any]):
        """
        Persist task updates to Supabase
        
        Args:
            task_id: Task ID
            updates: Dictionary of fields to update
        """
        try:
            client = get_supabase_admin_client()
            if not client:
                return
            
            # Update in database
            result = client.table("translation_tasks").update(updates).eq("task_id", task_id).execute()
            
            if result.data:
                logger.debug(f"[TaskManager] Synced task {task_id} to Supabase: {list(updates.keys())}")
        
        except Exception as e:
            logger.error(f"[TaskManager] Failed to sync task {task_id} to Supabase: {e}")
    
    def _recover_task_from_storage(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to recover a task from Supabase or local filesystem
        
        Args:
            task_id: Task ID to recover
            
        Returns:
            Task dictionary if found, None otherwise
        """
        # Try Supabase first
        task = self._recover_from_supabase(task_id)
        if task:
            return task
        
        # Fallback to local filesystem
        task = self._recover_from_filesystem(task_id)
        if task:
            return task
        
        return None
    
    def _recover_from_supabase(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Recover task from Supabase database
        
        Args:
            task_id: Task ID
            
        Returns:
            Task dictionary if found, None otherwise
        """
        try:
            client = get_supabase_admin_client()
            if not client:
                return None
            
            result = client.table("translation_tasks").select("*").eq("task_id", task_id).execute()
            
            if result.data and len(result.data) > 0:
                db_task = result.data[0]
                
                # Convert database record to internal task format
                task = {
                    "task_id": db_task.get("task_id"),
                    "status": db_task.get("status", "completed"),
                    "progress": db_task.get("progress", 100),
                    "stage": db_task.get("stage", "done"),
                    "message": db_task.get("message", "Task completed"),
                    "error": db_task.get("error"),
                    "warnings": None,
                    "source_available": True,
                    "created_at": db_task.get("created_at", datetime.utcnow().isoformat()),
                    "completed_at": db_task.get("completed_at"),
                    "source_type": db_task.get("source_type", "arxiv"),
                    "source_path": db_task.get("source_path"),
                    "output_path": db_task.get("output_path"),
                    "advanced_config": {
                        "translation_mode": db_task.get("translation_mode", "full"),
                        "compile_strategy": db_task.get("compile_strategy", "auto"),
                        "translation_model": db_task.get("translation_model"),
                        "enable_verification": db_task.get("enable_verification", True),
                        "generate_terminology_table": db_task.get("generate_glossary", True),
                        "use_author_api": db_task.get("use_author_api", True),
                    },
                    "latex_validation": None,
                    "arxiv_id": db_task.get("arxiv_id"),
                    "user_id": db_task.get("user_id"),
                    "source_language": db_task.get("source_language", "en"),
                    "target_language": db_task.get("target_language", "zh")
                }
                
                # If paths are not in DB, try to infer from local filesystem
                if not task["output_path"] or not task["source_path"]:
                    self._infer_paths_from_filesystem(task)
                
                logger.debug(f"[TaskManager] Recovered task {task_id} from Supabase")
                return task
                
        except Exception as e:
            logger.warning(f"[TaskManager] Failed to recover task {task_id} from Supabase: {e}")
        
        return None
    
    def _recover_from_filesystem(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Recover task from local filesystem
        
        Args:
            task_id: Task ID
            
        Returns:
            Task dictionary if found, None otherwise
        """
        from pathlib import Path
        from backend.app.core.config import get_settings
        
        try:
            settings = get_settings()
            output_base = Path(settings.OUTPUT_DIR)
            
            # Check if output directory exists for this task
            task_output_dir = output_base / task_id
            if task_output_dir.exists() and task_output_dir.is_dir():
                # Task output exists, construct task info from filesystem
                task = {
                    "task_id": task_id,
                    "status": TaskStatus.COMPLETED.value,  # Assume completed if output exists
                    "progress": 100,
                    "stage": CompilationStage.DONE.value,
                    "message": "Task recovered from filesystem",
                    "error": None,
                    "warnings": None,
                    "source_available": True,
                    "created_at": datetime.fromtimestamp(task_output_dir.stat().st_ctime).isoformat(),
                    "completed_at": datetime.fromtimestamp(task_output_dir.stat().st_mtime).isoformat(),
                    "source_type": "unknown",
                    "source_path": None,  # Will be inferred below
                    "output_path": str(task_output_dir),
                    "advanced_config": None,
                    "latex_validation": None,
                    "arxiv_id": None,
                    "user_id": None,
                    "source_language": "en",
                    "target_language": "zh"
                }
                
                # Try to find source path
                source_base = Path(settings.SOURCE_DIR)
                task_source_dir = source_base / task_id
                if task_source_dir.exists():
                    task["source_path"] = str(task_source_dir)
                
                # Try to infer arxiv_id from directory contents
                self._infer_arxiv_id(task, task_output_dir)
                
                logger.debug(f"[TaskManager] Recovered task {task_id} from filesystem")
                return task
                
        except Exception as e:
            logger.warning(f"[TaskManager] Failed to recover task {task_id} from filesystem: {e}")
        
        return None
    
    def _infer_paths_from_filesystem(self, task: Dict[str, Any]):
        """
        Infer source_path and output_path from filesystem if not set
        
        Args:
            task: Task dictionary to update
        """
        from pathlib import Path
        from backend.app.core.config import get_settings
        
        try:
            settings = get_settings()
            task_id = task["task_id"]
            
            if not task.get("output_path"):
                output_dir = Path(settings.OUTPUT_DIR) / task_id
                if output_dir.exists():
                    task["output_path"] = str(output_dir)
            
            if not task.get("source_path"):
                source_dir = Path(settings.SOURCE_DIR) / task_id
                if source_dir.exists():
                    task["source_path"] = str(source_dir)
                    
        except Exception as e:
            logger.warning(f"[TaskManager] Failed to infer paths for task {task['task_id']}: {e}")
    
    def _infer_arxiv_id(self, task: Dict[str, Any], directory: Any):
        """
        Try to infer arxiv_id from directory contents
        
        Args:
            task: Task dictionary to update
            directory: Directory to search
        """
        import re
        arxiv_pattern = re.compile(r'(\d{4}\.\d{4,5})(v\d+)?')
        
        try:
            # Check directory name
            match = arxiv_pattern.search(directory.name)
            if match:
                task["arxiv_id"] = match.group(1)
                task["source_type"] = "arxiv"
                return
            
            # Check file names
            for file_path in directory.iterdir():
                match = arxiv_pattern.search(file_path.name)
                if match:
                    task["arxiv_id"] = match.group(1)
                    task["source_type"] = "arxiv"
                    return
                    
        except Exception:
            pass


# Global task manager instance
task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """Get the global task manager instance"""
    return task_manager
