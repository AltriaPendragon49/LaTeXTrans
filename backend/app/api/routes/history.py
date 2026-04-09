"""
History API routes backed by local authenticated users and translation task persistence.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.app.core.auth import require_current_user
from backend.app.policies import authorize
from backend.app.core.config import get_settings
from backend.app.repositories import TranslationTaskRepository
from backend.app.utils.async_blocking import run_db_blocking

logger = logging.getLogger(__name__)
_settings = get_settings()
router = APIRouter()


def get_translation_task_repository() -> TranslationTaskRepository:
    return TranslationTaskRepository()


def _resolve_translation_task_repository() -> TranslationTaskRepository:
    return get_translation_task_repository()


# ---------------------------------------------------------------------------
# Lazy task-log status reconciliation
# ---------------------------------------------------------------------------
_TASK_LOG_TERMINAL_EVENT_MAP: Dict[str, str] = {
    "compilation_completed": "completed",
    "compilation_completed_with_warnings": "completed_with_warnings",
    "compilation_failed": "failed_compilation",
    "structure_invalid_aborted": "structure_invalid",
}


def _infer_status_from_task_log(output_path: Optional[str]) -> Optional[str]:
    if not output_path:
        return None
    root = Path(output_path)
    if not root.is_dir():
        return None

    candidates: List[Path] = []
    root_log = root / "task_log.json"
    if root_log.is_file():
        candidates.append(root_log)
    for child in root.iterdir():
        if child.is_dir():
            child_log = child / "task_log.json"
            if child_log.is_file():
                candidates.append(child_log)

    inferred: Optional[str] = None
    for log_path in candidates:
        try:
            entries = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for entry in entries:
            event = entry.get("event", "")
            if event in _TASK_LOG_TERMINAL_EVENT_MAP:
                inferred = _TASK_LOG_TERMINAL_EVENT_MAP[event]
    return inferred


def _ensure_task_authorized(
    current_user: Dict[str, Any],
    action: str,
    *,
    owner_user_id: Optional[str] = None,
) -> None:
    decision = authorize(
        current_user,
        "task",
        action,
        {"owner_user_id": owner_user_id or str(current_user.get("id") or "")},
    )
    if decision.allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=decision.reason,
    )


def _reconcile_task_snapshot(task: Dict[str, Any]) -> tuple[str, int, Optional[str], Optional[str]]:
    db_status = str(task.get("status") or "pending")
    effective_status = db_status
    effective_progress = int(task.get("progress") or 0)
    resolved_output_path = task.get("output_path")
    inferred_output_path: Optional[str] = None

    if db_status in {"pending", "processing", "queued"}:
        resolved_output_path = resolved_output_path or str(_settings.outputs_dir / task["task_id"])
        inferred = _infer_status_from_task_log(resolved_output_path)
        if inferred:
            effective_status = inferred
            effective_progress = 100
            if not task.get("output_path"):
                inferred_output_path = resolved_output_path

    return effective_status, effective_progress, resolved_output_path, inferred_output_path


class TaskHistoryItem(BaseModel):
    task_id: str
    source_type: str
    arxiv_id: Optional[str] = None
    translation_mode: str
    status: str
    progress: int
    created_at: str
    completed_at: Optional[str] = None
    source_language: str
    target_language: str
    compile_strategy: str
    translation_model: Optional[str] = None
    generate_glossary: bool
    use_author_api: bool
    formatting: Optional[Dict[str, Any]] = None


class TaskHistoryResponse(BaseModel):
    tasks: List[TaskHistoryItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class TaskDetailResponse(BaseModel):
    task_id: str
    source_type: str
    arxiv_id: Optional[str] = None
    source_language: str
    target_language: str
    translation_mode: str
    compile_strategy: str
    translation_model: Optional[str] = None
    generate_glossary: bool
    use_author_api: bool
    formatting: Optional[Dict[str, Any]] = None
    status: str
    progress: int
    stage: str
    message: Optional[str] = None
    error: Optional[str] = None
    source_path: Optional[str] = None
    output_path: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


@router.get("/history", response_model=TaskHistoryResponse)
async def get_user_history(
    current_user: Dict[str, Any] = Depends(require_current_user),
    repository: TranslationTaskRepository = Depends(_resolve_translation_task_repository),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
):
    _ensure_task_authorized(current_user, "list")
    try:
        rows, total = await run_db_blocking(
            lambda: repository.list_tasks_for_user(
                current_user["id"],
                page=page,
                page_size=page_size,
                status_filter=status_filter,
            )
        )

        corrections: List[tuple[str, str, Optional[str]]] = []
        tasks: list[TaskHistoryItem] = []

        for task in rows:
            effective_status, effective_progress, _resolved_output_path, inferred_output_path = _reconcile_task_snapshot(task)
            if effective_status != str(task.get("status") or "pending"):
                corrections.append(
                    (
                        str(task["task_id"]),
                        effective_status,
                        inferred_output_path,
                    )
                )

            tasks.append(
                TaskHistoryItem(
                    task_id=str(task["task_id"]),
                    source_type=str(task.get("source_type") or "upload"),
                    arxiv_id=task.get("arxiv_id"),
                    translation_mode=str(task.get("translation_mode") or "full"),
                    status=effective_status,
                    progress=effective_progress,
                    created_at=str(task["created_at"]),
                    completed_at=task.get("completed_at"),
                    source_language=str(task.get("source_language") or "en"),
                    target_language=str(task.get("target_language") or "zh"),
                    compile_strategy=str(task.get("compile_strategy") or "auto"),
                    translation_model=task.get("translation_model"),
                    generate_glossary=bool(task.get("generate_glossary", True)),
                    use_author_api=bool(task.get("use_author_api", True)),
                    formatting=task.get("formatting"),
                )
            )

        if corrections:
            async def _apply_corrections() -> None:
                for task_id, corrected_status, inferred_output_path in corrections:
                    patch: Dict[str, Any] = {"status": corrected_status, "progress": 100}
                    if inferred_output_path:
                        patch["output_path"] = inferred_output_path
                    try:
                        await run_db_blocking(lambda p=patch, tid=task_id: repository.update_task(tid, p))
                    except Exception:
                        logger.warning("[history] Failed to persist local correction for %s", task_id, exc_info=True)

            asyncio.create_task(_apply_corrections())

        offset = (page - 1) * page_size
        return TaskHistoryResponse(
            tasks=tasks,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + len(tasks)) < total,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {exc}",
        ) from exc


@router.get("/history/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_current_user),
    repository: TranslationTaskRepository = Depends(_resolve_translation_task_repository),
):
    _ensure_task_authorized(current_user, "view")
    try:
        task = await run_db_blocking(
            lambda: repository.get_task_for_user(current_user["id"], task_id)
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        effective_status, effective_progress, resolved_output_path, inferred_output_path = _reconcile_task_snapshot(task)
        if effective_status != str(task.get("status") or "pending") or inferred_output_path:
            patch: Dict[str, Any] = {"status": effective_status, "progress": effective_progress}
            if inferred_output_path:
                patch["output_path"] = inferred_output_path
            try:
                await run_db_blocking(lambda p=patch: repository.update_task(task_id, p))
            except Exception:
                logger.warning("[history] Failed to persist local detail correction for %s", task_id, exc_info=True)

        return TaskDetailResponse(
            task_id=str(task["task_id"]),
            source_type=str(task.get("source_type") or "upload"),
            arxiv_id=task.get("arxiv_id"),
            source_language=str(task.get("source_language") or "en"),
            target_language=str(task.get("target_language") or "zh"),
            translation_mode=str(task.get("translation_mode") or "full"),
            compile_strategy=str(task.get("compile_strategy") or "auto"),
            translation_model=task.get("translation_model"),
            generate_glossary=bool(task.get("generate_glossary", True)),
            use_author_api=bool(task.get("use_author_api", True)),
            formatting=task.get("formatting"),
            status=effective_status,
            progress=effective_progress,
            stage=str(task.get("stage") or "idle"),
            message=task.get("message"),
            error=task.get("error"),
            source_path=task.get("source_path"),
            output_path=resolved_output_path,
            created_at=str(task["created_at"]),
            completed_at=task.get("completed_at"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task detail: {exc}",
        ) from exc


@router.delete("/history/{task_id}")
async def delete_task_history(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_current_user),
    repository: TranslationTaskRepository = Depends(_resolve_translation_task_repository),
):
    from backend.app.services.task_manager import get_task_manager

    task_manager = get_task_manager()
    _ensure_task_authorized(current_user, "delete")

    try:
        task = await run_db_blocking(
            lambda: repository.get_task_for_user(current_user["id"], task_id)
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        if task.get("status") == "processing":
            task_manager.cancel_task(task_id)
            await asyncio.sleep(0.5)

        deleted = await run_db_blocking(
            lambda: repository.delete_task_for_user(current_user["id"], task_id)
        )
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        deletion_result = task_manager.delete_task_full(task_id)
        return {
            "message": "Task deleted successfully",
            "task_id": task_id,
            "deleted_dirs": deletion_result["deleted_dirs"],
            "errors": deletion_result["errors"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {exc}",
        ) from exc


class BatchDeleteRequest(BaseModel):
    task_ids: List[str]


@router.delete("/history")
async def delete_tasks_batch(
    request: BatchDeleteRequest,
    current_user: Dict[str, Any] = Depends(require_current_user),
    repository: TranslationTaskRepository = Depends(_resolve_translation_task_repository),
):
    from backend.app.services.task_manager import get_task_manager

    task_manager = get_task_manager()
    results = []
    _ensure_task_authorized(current_user, "delete")

    for task_id in request.task_ids:
        try:
            task = await run_db_blocking(
                lambda tid=task_id: repository.get_task_for_user(current_user["id"], tid)
            )
            if task is None:
                results.append({"task_id": task_id, "success": False, "error": "Task not found"})
                continue

            if task.get("status") == "processing":
                task_manager.cancel_task(task_id)
                await asyncio.sleep(0.3)

            await run_db_blocking(
                lambda tid=task_id: repository.delete_task_for_user(current_user["id"], tid)
            )
            deletion_result = task_manager.delete_task_full(task_id)
            results.append(
                {
                    "task_id": task_id,
                    "success": deletion_result["success"],
                    "deleted_dirs": deletion_result["deleted_dirs"],
                    "errors": deletion_result["errors"],
                }
            )
        except Exception as exc:
            results.append({"task_id": task_id, "success": False, "error": str(exc)})

    success_count = sum(1 for result in results if result["success"])
    return {
        "message": f"Deleted {success_count}/{len(request.task_ids)} tasks",
        "results": results,
    }
