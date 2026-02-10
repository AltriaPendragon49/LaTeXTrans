"""
arXiv API Routes

Provides endpoints for downloading arXiv papers.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
import asyncio
import base64
import json

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

# Allow missing Authorization header (guest mode)
security = HTTPBearer(auto_error=False)


# Custom exceptions for better error handling
class ArxivNoSourceError(Exception):
    """arXiv paper has no TeX source available"""
    pass


class ArxivExtractionError(Exception):
    """Failed to extract arXiv source archive"""
    pass


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


async def _download_arxiv_background(arxiv_id: str, task_id: str):
    """
    后台异步下载 arXiv 论文
    
    Args:
        arxiv_id: arXiv 论文 ID
        task_id: 任务 ID
    """
    try:
        # 使用 to_thread 在线程池中执行同步阻塞函数，避免阻塞事件循环
        # 这样 API 可以立即返回，前端可以开始轮询进度
        source_dirs = await asyncio.to_thread(
            batch_download_arxiv_tex,
            [arxiv_id],
            str(settings.uploads_dir / task_id),
            task_manager,
            task_id
        )
        
        if not source_dirs:
            raise ArxivNoSourceError(f"arXiv 论文 {arxiv_id} 没有可用的 TeX 源码")
        
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
        
    except ArxivNoSourceError as e:
        # 404 - No TeX source available for this paper
        logger.warning(f"No TeX source for arXiv {arxiv_id}: {e}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"arXiv 论文 {arxiv_id} 没有可用的 TeX 源码"
        )
    
    except ArxivExtractionError as e:
        # 422 - Extraction failed (unprocessable)
        logger.error(f"Failed to extract arXiv {arxiv_id}: {e}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"arXiv 论文 {arxiv_id} 解压失败"
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


@router.post("/arxiv", response_model=ArxivResponse)
async def download_arxiv(
    request: ArxivRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Download arXiv paper source (asynchronous)
    
    立即返回 task_id，后台异步执行下载。
    前端通过 GET /api/task/{task_id} 轮询获取下载进度。
    
    Args:
        request: arXiv download request with paper ID
    
    Returns:
        Task information with task_id for progress tracking
    
    Raises:
        HTTPException: If arXiv ID is invalid
    """
    # Extract and validate arXiv ID
    arxiv_ids = extract_arxiv_ids([request.arxiv_id])
    
    if not arxiv_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid arXiv ID format: {request.arxiv_id}"
        )
    
    arxiv_id = arxiv_ids[0]
    logger.info(f"Starting download for arXiv paper: {arxiv_id}")
    
    # Get user_id from token if authenticated
    user_id = None
    if credentials:
        try:
            # Parse JWT to get user_id (sub claim)
            token = credentials.credentials
            # Decode JWT payload (no verification, just reading claims)
            payload_b64 = token.split('.')[1]
            # Add padding if needed
            payload_b64 += '=' * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            user_id = payload.get('sub')
            if user_id:
                logger.info(f"Authenticated user creating arXiv task: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to parse user_id from token: {e}")
    
    # Create a new task
    task_id = task_manager.create_task(
        source_type="arxiv", 
        arxiv_id=arxiv_id,
        user_id=user_id
    )

    # 设置初始进度状态，确保前端第一次轮询就能看到进度
    task_manager.update_task(
        task_id=task_id,
        status=TaskStatus.PROCESSING.value,
        progress=0,
        stage="downloading",
        message=f"开始下载 arXiv 论文 {arxiv_id}..."
    )
    
    # Start background download task
    asyncio.create_task(_download_arxiv_background(arxiv_id, task_id))
    
    # Immediately return task_id for frontend polling
    return ArxivResponse(
        task_id=task_id,
        arxiv_id=arxiv_id,
        status="downloading",
        message=f"arXiv 论文 {arxiv_id} 正在后台下载，请轮询任务状态"
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
