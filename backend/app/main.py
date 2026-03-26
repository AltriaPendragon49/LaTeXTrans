"""
FastAPI Main Application

Minimal MVP version with:
- Health check endpoint
- arXiv download endpoint
- Basic CORS configuration
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Set

from fastapi import FastAPI, Response, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.auth import require_admin_request
from backend.app.core.config import get_settings
from backend.app.services.task_manager import (
    get_task_manager,
    get_task_queue,
)
from backend.app.services import task_manager as task_manager_module

if hasattr(task_manager_module, "set_runtime_shutting_down"):
    set_runtime_shutting_down = task_manager_module.set_runtime_shutting_down
else:
    def set_runtime_shutting_down(_flag: bool) -> None:
        return None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="LaTeXTrans Backend API"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter()

INTERRUPTED_TASK_STATUSES = ["queued", "pending", "processing"]
NON_SUCCESS_PAPER_STATUSES = [
    "not_started",
    "queued",
    "processing",
    "failed",
    "failed_compilation",
    "structure_invalid",
]


def _dedupe_non_empty(values: List[str]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered

async def reset_stale_community_tasks() -> dict:
    """
    Purge non-success community-paper rows.
    This removes related local artifacts and paper-related Supabase rows.
    """
    import asyncio as _asyncio
    import shutil as _shutil
    from backend.app.core.supabase_client import create_supabase_admin_client

    result = {"reset_papers": 0, "deleted_folders": 0, "errors": []}

    if not settings.supabase_service_role_key:
        msg = "[StaleCleanup] SUPABASE_SERVICE_ROLE_KEY is not configured; cleanup skipped"
        logger.error(msg)
        result["errors"].append(msg)
        return result
    if not settings.supabase_url:
        msg = "[StaleCleanup] SUPABASE_URL is not configured; cleanup skipped"
        logger.error(msg)
        result["errors"].append(msg)
        return result

    client = create_supabase_admin_client()
    if not client:
        msg = "[StaleCleanup] Failed to create Supabase admin client"
        logger.error(msg)
        result["errors"].append(msg)
        return result

    try:
        purgeable_res = await _asyncio.to_thread(
            lambda: client.table("papers")
            .select("id, trans_latest_task_id, community_selected_task_id")
            .in_("trans_status", NON_SUCCESS_PAPER_STATUSES)
            .execute()
        )
        purgeable_rows = purgeable_res.data or []
        purgeable_ids = [row["id"] for row in purgeable_rows if row.get("id")]
        logger.info("[StaleCleanup] Purgeable non-success papers: %s", purgeable_ids)

        cp_dir = settings.community_papers_dir
        for paper_id in purgeable_ids:
            target = cp_dir / paper_id
            if target.exists():
                try:
                    _shutil.rmtree(target)
                    result["deleted_folders"] += 1
                except Exception as rm_err:
                    msg = f"[StaleCleanup] Failed to delete {target}: {rm_err}"
                    logger.error(msg)
                    result["errors"].append(msg)

        if not purgeable_ids:
            logger.info("[StaleCleanup] Nothing to purge")
            return result

        task_manager = get_task_manager()
        asset_res = await _asyncio.to_thread(
            lambda: client.table("paper_assets")
            .select("task_id")
            .in_("paper_id", purgeable_ids)
            .execute()
        )
        comment_res = await _asyncio.to_thread(
            lambda: client.table("comments")
            .select("id")
            .in_("paper_id", purgeable_ids)
            .execute()
        )
        comment_ids = _dedupe_non_empty([row.get("id") for row in (comment_res.data or [])])

        paper_report_res = await _asyncio.to_thread(
            lambda: client.table("reports")
            .select("id")
            .eq("target_type", "paper")
            .in_("target_id", purgeable_ids)
            .execute()
        )
        report_ids = [row.get("id") for row in (paper_report_res.data or [])]
        if comment_ids:
            comment_report_res = await _asyncio.to_thread(
                lambda: client.table("reports")
                .select("id")
                .eq("target_type", "comment")
                .in_("target_id", comment_ids)
                .execute()
            )
            report_ids.extend(row.get("id") for row in (comment_report_res.data or []))
        report_ids = _dedupe_non_empty(report_ids)

        if report_ids:
            await _asyncio.to_thread(
                lambda: client.table("moderation_actions")
                .delete()
                .in_("report_id", report_ids)
                .execute()
            )
            await _asyncio.to_thread(
                lambda: client.table("reports")
                .delete()
                .in_("id", report_ids)
                .execute()
            )

        for table_name in ["comments", "paper_assets", "paper_likes", "paper_favorites"]:
            await _asyncio.to_thread(
                lambda t=table_name: client.table(t)
                .delete()
                .in_("paper_id", purgeable_ids)
                .execute()
            )

        purgeable_task_ids = _dedupe_non_empty(
            [row.get("trans_latest_task_id") for row in purgeable_rows]
            + [row.get("community_selected_task_id") for row in purgeable_rows]
            + [row.get("task_id") for row in (asset_res.data or [])]
        )
        for task_id in purgeable_task_ids:
            deletion_result = task_manager.delete_task_full(task_id)
            result.setdefault("deleted_task_artifacts", []).append(
                {
                    "task_id": task_id,
                    "success": deletion_result.get("success", False),
                    "deleted_dirs": deletion_result.get("deleted_dirs", []),
                }
            )
            result.setdefault("task_cleanup_errors", []).extend(deletion_result.get("errors", []))

        if purgeable_task_ids:
            await _asyncio.to_thread(
                lambda: client.table("translation_tasks")
                .delete()
                .in_("task_id", purgeable_task_ids)
                .execute()
            )

        await _asyncio.to_thread(
            lambda: client.table("papers")
            .delete()
            .in_("id", purgeable_ids)
            .execute()
        )
        result["purged_records"] = len(purgeable_ids)
    except Exception as e:
        msg = f"[StaleCleanup] Unexpected error: {e}"
        logger.error(msg, exc_info=True)
        result["errors"].append(msg)

    logger.info("[StaleCleanup] Done: %s", result)
    return result


async def fail_interrupted_translation_tasks() -> dict:
    """
    Mark interrupted queued/pending/processing translation tasks as failed on restart.
    Also cleans local task artifacts and updates affected community-paper status.
    """
    from backend.app.core.supabase_client import create_supabase_admin_client

    result = {"failed_tasks": 0, "updated_papers": 0, "cleaned_task_artifacts": 0, "errors": []}

    if not settings.supabase_service_role_key or not settings.supabase_url:
        return result

    client = create_supabase_admin_client()
    task_manager = get_task_manager()
    if not client:
        return result

    try:
        active_res = await asyncio.to_thread(
            lambda: client.table("translation_tasks")
            .select("task_id")
            .in_("status", INTERRUPTED_TASK_STATUSES)
            .execute()
        )
        active_ids = _dedupe_non_empty([row.get("task_id") for row in (active_res.data or [])])
        updated_paper_ids: Set[str] = set()
        now_iso = datetime.now(timezone.utc).isoformat()

        if active_ids:
            for task_id in active_ids:
                deletion_result = task_manager.delete_task_full(task_id)
                if deletion_result.get("success"):
                    result["cleaned_task_artifacts"] += 1
                result.setdefault("task_cleanup_errors", []).extend(deletion_result.get("errors", []))

            await asyncio.to_thread(
                lambda: client.table("translation_tasks")
                .update(
                    {
                        "status": "failed",
                        "progress": 100,
                        "message": "Task interrupted by backend restart",
                        "error": "Task interrupted by backend restart",
                        "detail_code": "task_interrupted_restart",
                        "completed_at": now_iso,
                    }
                )
                .in_("task_id", active_ids)
                .execute()
            )
            result["failed_tasks"] = len(active_ids)

            affected_papers_res = await asyncio.to_thread(
                lambda: client.table("papers")
                .select("id")
                .in_("trans_status", ["queued", "processing"])
                .in_("community_selected_task_id", active_ids)
                .execute()
            )
            affected_paper_ids = _dedupe_non_empty([row.get("id") for row in (affected_papers_res.data or [])])
            if affected_paper_ids:
                await asyncio.to_thread(
                    lambda: client.table("papers")
                    .update({"trans_status": "failed", "updated_at": now_iso})
                    .in_("id", affected_paper_ids)
                    .execute()
                )
                updated_paper_ids.update(affected_paper_ids)

        stale_papers_res = await asyncio.to_thread(
            lambda: client.table("papers")
            .select("id, community_selected_task_id")
            .in_("trans_status", ["queued", "processing"])
            .execute()
        )
        stale_rows = stale_papers_res.data or []
        stale_task_ids = _dedupe_non_empty([row.get("community_selected_task_id") for row in stale_rows])
        if stale_task_ids:
            stale_task_status_res = await asyncio.to_thread(
                lambda: client.table("translation_tasks")
                .select("task_id, status")
                .in_("task_id", stale_task_ids)
                .execute()
            )
            terminal_failed_statuses = {"failed", "failed_compilation", "structure_invalid"}
            failed_task_ids = {
                str(row.get("task_id") or "").strip()
                for row in (stale_task_status_res.data or [])
                if str(row.get("status") or "").strip() in terminal_failed_statuses
            }
            stale_paper_ids = _dedupe_non_empty(
                [
                    row.get("id")
                    for row in stale_rows
                    if str(row.get("community_selected_task_id") or "").strip() in failed_task_ids
                ]
            )
            stale_paper_ids = [paper_id for paper_id in stale_paper_ids if paper_id not in updated_paper_ids]
            if stale_paper_ids:
                await asyncio.to_thread(
                    lambda: client.table("papers")
                    .update({"trans_status": "failed", "updated_at": now_iso})
                    .in_("id", stale_paper_ids)
                    .execute()
                )
                updated_paper_ids.update(stale_paper_ids)

        result["updated_papers"] = len(updated_paper_ids)
    except Exception as exc:
        msg = f"[RestartFailover] Unexpected error: {exc}"
        logger.error(msg, exc_info=True)
        result["errors"].append(msg)

    logger.info("[RestartFailover] Done: %s", result)
    return result


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    set_runtime_shutting_down(False)
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(f"LLM Model: {settings.llm_model}")
    logger.info(f"CORS origins: {settings.cors_origins}")
    logger.warning(
        "Task runtime state is still partially in-process memory; "
        "run a single worker in production until full runtime-state externalization is implemented."
    )

    # Initialize TaskQueue
    import backend.app.services.task_manager as tm_module
    from backend.app.services.task_manager import TaskQueue
    tq = TaskQueue(max_concurrent=settings.max_concurrent_translations)
    await tq.initialize()
    tm_module.task_queue = tq
    logger.info(f"[Startup] TaskQueue initialized (max_concurrent={settings.max_concurrent_translations})")

    await fail_interrupted_translation_tasks()
    await reset_stale_community_tasks()

    # 鈹€鈹€ Orphaned-task cleanup 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
    from backend.app.services.task_manager import task_manager as _tm
    from backend.app.core.supabase_client import get_supabase_admin_client
    from pathlib import Path as _Path
    import shutil as _shutil
    import time as _time

    cleanup_interval = 30 * 60  # 30 minutes

    async def _run_cleanup():
        """
        State-independent orphaned task cleanup.

        Scans data/outputs and data/terms for directories older than
        guest_task_ttl_hours. Any task_id not found in the Supabase
        translation_tasks table is considered orphaned and deleted.
        If Supabase is unreachable the entire deletion is skipped to
        prevent accidental data loss.
        """
        import asyncio as _asyncio2
        try:
            outputs_dir = _Path(settings.outputs_dir)
            terms_dir   = _Path(settings.data_dir) / "terms"
            ttl_seconds = settings.guest_task_ttl_hours * 3600
            now = _time.time()

            # 1. Collect directories older than TTL from both scan dirs
            old_task_ids: set = set()
            for scan_dir in [outputs_dir, terms_dir]:
                if not scan_dir.exists():
                    continue
                for entry in scan_dir.iterdir():
                    if not entry.is_dir():
                        continue
                    try:
                        age = now - entry.stat().st_mtime
                        if age >= ttl_seconds:
                            old_task_ids.add(entry.name)
                    except OSError:
                        pass

            if not old_task_ids:
                logger.debug("[OrphanedCleanup] No old directories found, skipping.")
                return

            # 2. Bulk-query Supabase to find which task_ids still exist in DB
            client = get_supabase_admin_client()
            if not client:
                logger.warning(
                    "[OrphanedCleanup] Supabase admin client unavailable 鈥?"
                    "skipping deletion to prevent accidental data loss."
                )
                return

            try:
                result = await _asyncio2.to_thread(
                    lambda: (
                        client.table("translation_tasks")
                        .select("task_id")
                        .in_("task_id", list(old_task_ids))
                        .execute()
                    )
                )
                db_task_ids = {row["task_id"] for row in (result.data or [])}
            except Exception as db_err:
                logger.warning(
                    f"[OrphanedCleanup] Supabase query failed ({db_err}) 鈥?"
                    "skipping deletion to prevent accidental data loss."
                )
                return

            # 3. Delete directories whose task_id is NOT in the DB (orphaned)
            orphaned = old_task_ids - db_task_ids
            if not orphaned:
                logger.debug("[OrphanedCleanup] No orphaned tasks found.")
                return

            logger.info(f"[OrphanedCleanup] Found {len(orphaned)} orphaned task(s) to delete.")
            for task_id in orphaned:
                for base_dir in [outputs_dir, terms_dir]:
                    target = base_dir / task_id
                    if target.exists():
                        try:
                            _shutil.rmtree(target)
                            logger.info(f"[OrphanedCleanup] Deleted: {target}")
                        except Exception as rm_err:
                            logger.error(f"[OrphanedCleanup] Failed to delete {target}: {rm_err}")
                # Also evict from in-memory cache if present
                _tm._tasks.pop(task_id, None)

        except Exception as e:
            logger.error(f"[OrphanedCleanup] Unexpected error during cleanup: {e}", exc_info=True)

    async def cleanup_loop():
        # --- Run once immediately on startup ---
        logger.info("[OrphanedCleanup] Running initial cleanup on startup...")
        await _run_cleanup()

        # --- Then run periodically ---
        while True:
            await asyncio.sleep(cleanup_interval)
            logger.info("[OrphanedCleanup] Running scheduled cleanup...")
            await _run_cleanup()

            # Also flush expired in-memory guest tasks (supplementary)
            try:
                from backend.app.services.task_manager import guest_tracker
                expired_ids = guest_tracker.get_expired_task_ids()
                for task_id in expired_ids:
                    _tm._tasks.pop(task_id, None)
                    guest_tracker.remove(task_id)
                if expired_ids:
                    logger.info(f"[GuestCleanup] Evicted {len(expired_ids)} in-memory guest task(s)")
            except Exception as e:
                logger.error(f"[GuestCleanup] Error flushing in-memory tasks: {e}", exc_info=True)

    app.state.cleanup_task = asyncio.create_task(cleanup_loop())
    logger.info("[Startup] Orphaned-task cleanup started (runs on startup + every 30 min)")




@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    set_runtime_shutting_down(True)
    cleanup_task = getattr(app.state, 'cleanup_task', None)
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info(f"Shutting down {settings.app_name}")


@api_router.post("/admin/cleanup", tags=["admin"])
async def admin_cleanup_stale_tasks(_admin: dict = Depends(require_admin_request)):
    """
    Manually trigger stale task cleanup and restart failover reconciliation.
    """
    failover_result = await fail_interrupted_translation_tasks()
    cleanup_result = await reset_stale_community_tasks()
    errors = list(cleanup_result.get("errors", [])) + list(failover_result.get("errors", []))
    return {"ok": not errors, **cleanup_result, **failover_result, "errors": errors}


@api_router.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Status information
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "llm_model": settings.llm_model
    }


@api_router.get("/")
async def root():
    """
    Root endpoint
    
    Returns:
        Welcome message
    """
    return {
        "message": "LaTeXTrans Backend API",
        "version": settings.version,
        "docs": "/docs",
        "health": "/api/health"
    }


@api_router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Handle favicon.ico requests to avoid 404 errors in logs
    """
    return Response(content="", media_type="image/x-icon")


# Import and include API routes
from backend.app.api.routes import arxiv, upload, task, translate, download, history, papers, community_agent
from backend.app.api.routes import settings as settings_routes

api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(arxiv.router, tags=["arxiv"])
api_router.include_router(translate.router, tags=["translate"])
api_router.include_router(task.router, tags=["task"])
api_router.include_router(download.router, tags=["download"])
api_router.include_router(settings_routes.router, tags=["settings"])
api_router.include_router(history.router, tags=["history"])
api_router.include_router(papers.router, tags=["papers"])
api_router.include_router(community_agent.router, tags=["community-agent"])
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )

