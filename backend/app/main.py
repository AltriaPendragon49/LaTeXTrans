"""
FastAPI Main Application

Minimal MVP version with:
- Health check endpoint
- arXiv download endpoint
- Basic CORS configuration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from backend.app.core.config import get_settings

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
    description="LaTeXTrans Backend API - MVP Version"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(f"LLM Model: {settings.llm_model}")

    # Initialize TaskQueue
    import backend.app.services.task_manager as tm_module
    from backend.app.services.task_manager import TaskQueue
    tq = TaskQueue(max_concurrent=settings.max_concurrent_translations)
    await tq.initialize()
    tm_module.task_queue = tq
    logger.info(f"[Startup] TaskQueue initialized (max_concurrent={settings.max_concurrent_translations})")

    # Start periodic guest cleanup background task
    async def periodic_cleanup():
        from backend.app.services.task_manager import guest_tracker, task_manager
        from pathlib import Path
        import shutil
        cleanup_interval = 30 * 60  # 30 minutes
        while True:
            try:
                expired_ids = guest_tracker.get_expired_task_ids()
                for task_id in expired_ids:
                    output_dir = Path(settings.outputs_dir) / task_id
                    if output_dir.exists():
                        shutil.rmtree(output_dir, ignore_errors=True)
                        logger.info(f"[GuestCleanup] Deleted output dir: {output_dir}")
                    terms_dir = Path(settings.data_dir) / "terms" / task_id
                    if terms_dir.exists():
                        shutil.rmtree(terms_dir, ignore_errors=True)
                        logger.info(f"[GuestCleanup] Deleted terms dir: {terms_dir}")
                    task_manager._tasks.pop(task_id, None)
                    guest_tracker.remove(task_id)
                if expired_ids:
                    logger.info(f"[GuestCleanup] Cleaned up {len(expired_ids)} expired guest tasks")
            except Exception as e:
                logger.error(f"[GuestCleanup] Error during cleanup: {e}", exc_info=True)
            await asyncio.sleep(cleanup_interval)

    app.state.cleanup_task = asyncio.create_task(periodic_cleanup())
    logger.info("[Startup] Guest cleanup task started (interval=30min)")


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



@app.get("/health")
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


@app.get("/")
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
        "health": "/health"
    }


# Import and include API routes
from backend.app.api.routes import arxiv, upload, task, translate, download, history
from backend.app.api.routes import settings as settings_routes

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(arxiv.router, prefix="/api", tags=["arxiv"])
app.include_router(translate.router, prefix="/api", tags=["translate"])
app.include_router(task.router, prefix="/api", tags=["task"])
app.include_router(download.router, prefix="/api", tags=["download"])
app.include_router(settings_routes.router, prefix="/api", tags=["settings"])
app.include_router(history.router, prefix="/api", tags=["history"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
