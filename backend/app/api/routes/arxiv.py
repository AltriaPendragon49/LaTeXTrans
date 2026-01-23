"""
arXiv API Routes

Provides endpoints for downloading arXiv papers.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
import logging

from backend.app.services.latex.utils import (
    batch_download_arxiv_tex,
    extract_arxiv_ids,
    is_valid_arxiv_id
)
from backend.app.services.task_manager import get_task_manager
from backend.app.core.config import get_settings, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()


class ArxivRequest(BaseModel):
    """arXiv download request"""
    arxiv_id: str = Field(..., description="arXiv paper ID (e.g., '2508.18791' or URL)")
    

class ArxivResponse(BaseModel):
    """arXiv download response"""
    task_id: str
    arxiv_id: str
    status: str
    message: str
    source_path: str | None = None


@router.post("/arxiv", response_model=ArxivResponse)
async def download_arxiv(request: ArxivRequest):
    """
    Download arXiv paper source
    
    Args:
        request: arXiv download request with paper ID
    
    Returns:
        Task information with download status
    
    Raises:
        HTTPException: If arXiv ID is invalid or download fails
    """
    # Extract and validate arXiv ID
    arxiv_ids = extract_arxiv_ids([request.arxiv_id])
    
    if not arxiv_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid arXiv ID format: {request.arxiv_id}"
        )
    
    arxiv_id = arxiv_ids[0]
    logger.info(f"Downloading arXiv paper: {arxiv_id}")
    
    # Create task
    task_id = task_manager.create_task(source_type="arxiv")
    
    # Update task with arXiv ID
    task_manager.update_task(
        task_id=task_id,
        status=TaskStatus.PROCESSING.value,
        message=f"Downloading arXiv paper {arxiv_id}..."
    )
    
    try:
        # Download arXiv source
        source_dirs = batch_download_arxiv_tex(
            [arxiv_id],
            save_dir=str(settings.uploads_dir / task_id)
        )
        
        if not source_dirs:
            raise Exception(f"Failed to download arXiv paper {arxiv_id}")
        
        source_path = source_dirs[0]
        
        # Update task as completed
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PENDING.value,  # Ready for translation
            progress=100,
            message=f"arXiv paper {arxiv_id} downloaded successfully",
            source_path=source_path,
            source_available=True
        )
        
        logger.info(f"Successfully downloaded arXiv {arxiv_id} to {source_path}")
        
        return ArxivResponse(
            task_id=task_id,
            arxiv_id=arxiv_id,
            status="success",
            message=f"arXiv paper {arxiv_id} downloaded successfully",
            source_path=source_path
        )
    
    except Exception as e:
        logger.error(f"Failed to download arXiv {arxiv_id}: {e}")
        
        # Update task as failed
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"Failed to download arXiv paper {arxiv_id}"
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download arXiv paper: {str(e)}"
        )


@router.get("/arxiv/validate/{arxiv_id}")
async def validate_arxiv_id(arxiv_id: str):
    """
    Validate arXiv ID format
    
    Args:
        arxiv_id: arXiv paper ID to validate
    
    Returns:
        Validation result
    """
    is_valid = is_valid_arxiv_id(arxiv_id)
    
    return {
        "arxiv_id": arxiv_id,
        "is_valid": is_valid,
        "message": "Valid arXiv ID" if is_valid else "Invalid arXiv ID format"
    }
