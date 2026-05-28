"""
arXiv API 路由

提供下载 arXiv 论文的接口。
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
import asyncio
from pathlib import Path

from backend.app.core.auth import optional_current_user, resolve_current_user_id
from backend.app.services import task_artifact_storage
from backend.app.services.latex.utils import (
    batch_download_arxiv_tex,
    extract_arxiv_ids,
    is_valid_arxiv_id,
    ArxivNoSourceAvailableError,
    ArxivNetworkFailureError,
    ArxivArchiveCorruptedError,
)
from backend.app.services.task_manager import get_task_manager
from backend.app.core.config import get_settings, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()

# 允许缺失 Authorization 头（游客模式）
security = HTTPBearer(auto_error=False)


class ArxivRequest(BaseModel):
    """arXiv 下载请求"""
    arxiv_id: str = Field(..., description="arXiv paper ID (e.g., '2508.18791' or URL)")
    

class ArxivResponse(BaseModel):
    """arXiv 下载响应"""
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
        # 修改下载路径为 arxiv_id-based,实现跨任务共享
        source_dirs = await asyncio.to_thread(
            batch_download_arxiv_tex,
            [arxiv_id],
            str(settings.uploads_dir / f"arxiv_{arxiv_id}"),
            task_manager,
            task_id
        )
        
        if not source_dirs:
            raise ArxivNoSourceAvailableError(f"arXiv 论文 {arxiv_id} 没有可用的 TeX 源码")
        
        source_path = source_dirs[0]
        stored_source_path = source_path
        if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
            stored_source_path = task_artifact_storage.persist_task_directory(
                Path(source_path),
                stored_path=task_artifact_storage.normalize_stored_task_path(source_path),
                delete_local=True,
            )
        
        # 将任务状态标记为已完成
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PENDING.value,  # Ready for translation
            progress=100,
            message=f"arXiv paper {arxiv_id} downloaded successfully",
            detail_code="download_source_complete",
            source_path=stored_source_path,
            source_available=True
        )
        
        logger.info(f"Successfully downloaded arXiv {arxiv_id} to {stored_source_path}")
        
    except ArxivNoSourceAvailableError as e:
        # 404 - 该论文没有可用的 TeX 源码
        logger.warning(f"No TeX source for arXiv {arxiv_id}: {e}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"arXiv 论文 {arxiv_id} 没有可用的 TeX 源码"
        )
    
    except ArxivArchiveCorruptedError as e:
        # 422 - 解压失败（无法处理）
        logger.error(f"Failed to extract arXiv {arxiv_id}: {e}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"arXiv 论文 {arxiv_id} 解压失败"
        )

    except ArxivNetworkFailureError as e:
        logger.error(f"Network failure while downloading arXiv {arxiv_id}: {e}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"下载 arXiv 论文 {arxiv_id} 时网络不稳定，请稍后重试"
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    current_user: Optional[dict] = Depends(optional_current_user),
):
    """
    下载 arXiv 论文源码（异步）

    立即返回 task_id，后台异步执行下载。
    前端通过 GET /api/task/{task_id} 轮询获取下载进度。

    Args:
        request: 包含 arXiv 论文 ID 的下载请求

    Returns:
        包含 task_id 的任务信息，用于进度跟踪

    Raises:
        HTTPException: arXiv ID 格式无效时抛出
    """
    # 提取并验证 arXiv ID
    arxiv_ids = extract_arxiv_ids([request.arxiv_id])
    
    if not arxiv_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid arXiv ID format: {request.arxiv_id}"
        )
    
    arxiv_id = arxiv_ids[0]
    logger.info(f"Starting download for arXiv paper: {arxiv_id}")
    
    user_id = resolve_current_user_id(current_user, credentials)
    if user_id:
        logger.info(f"Authenticated user creating arXiv task: {user_id}")
    
    # 创建新任务
    task_id = task_manager.create_task(
        source_type="arxiv", 
        arxiv_id=arxiv_id,
        user_id=user_id,
        persist_to_db=False  # 延迟到翻译时才持久化
    )

    # 设置初始进度状态，确保前端第一次轮询就能看到进度
    task_manager.update_task(
        task_id=task_id,
        status=TaskStatus.PROCESSING.value,
        progress=0,
        stage="downloading",
        message=f"开始下载 arXiv 论文 {arxiv_id}...",
        detail_code="download_source_starting",
    )
    
    # 启动后台下载任务
    asyncio.create_task(_download_arxiv_background(arxiv_id, task_id))
    
    # 立即返回 task_id 供前端轮询
    return ArxivResponse(
        task_id=task_id,
        arxiv_id=arxiv_id,
        status="downloading",
        message=f"arXiv 论文 {arxiv_id} 正在后台下载，请轮询任务状态"
    )


@router.get("/arxiv/validate/{arxiv_id}")
async def validate_arxiv_id(arxiv_id: str):
    """
    验证 arXiv ID 格式

    Args:
        arxiv_id: 待验证的 arXiv 论文 ID

    Returns:
        验证结果
    """
    is_valid = is_valid_arxiv_id(arxiv_id)
    
    return {
        "arxiv_id": arxiv_id,
        "is_valid": is_valid,
        "message": "Valid arXiv ID" if is_valid else "Invalid arXiv ID format"
    }
