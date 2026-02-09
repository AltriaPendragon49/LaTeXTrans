"""
FastAPI Main Application

Minimal MVP version with:
- Health check endpoint
- arXiv download endpoint
- Basic CORS configuration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
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
