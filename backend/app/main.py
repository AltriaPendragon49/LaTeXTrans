"""
FastAPI Main Application

Minimal MVP version with:
- Health check endpoint
- arXiv download endpoint
- Basic CORS configuration
"""

from fastapi import FastAPI, Response, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from backend.app.core.config import get_settings
from backend.app.utils.async_blocking import run_db_blocking

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


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
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

    # ── Orphaned-task cleanup ─────────────────────────────────────────────
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
                    "[OrphanedCleanup] Supabase admin client unavailable – "
                    "skipping deletion to prevent accidental data loss."
                )
                return

            try:
                result = await run_db_blocking(
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
                    f"[OrphanedCleanup] Supabase query failed ({db_err}) – "
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
    cleanup_task = getattr(app.state, 'cleanup_task', None)
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info(f"Shutting down {settings.app_name}")



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
from backend.app.api.routes import arxiv, upload, task, translate, download, history, papers
from backend.app.api.routes import settings as settings_routes

api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(arxiv.router, tags=["arxiv"])
api_router.include_router(translate.router, tags=["translate"])
api_router.include_router(task.router, tags=["task"])
api_router.include_router(download.router, tags=["download"])
api_router.include_router(settings_routes.router, tags=["settings"])
api_router.include_router(history.router, tags=["history"])
api_router.include_router(papers.router, tags=["papers"])
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
