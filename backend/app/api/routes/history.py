"""
History API Routes - 纯 RLS 模式

提供用户翻译历史访问接口。
需要认证 - 访客用户无法访问历史。

核心原则：
- 后端不验证 token，不解析 user
- token 透传给 Supabase client
- RLS 使用 auth.uid() 自动控制权限
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from supabase import Client

from backend.app.core.auth import get_supabase_client_from_request

router = APIRouter()


class TaskHistoryItem(BaseModel):
    """Single task in history list"""
    task_id: str
    source_type: str
    arxiv_id: Optional[str] = None
    translation_mode: str
    status: str
    progress: int
    created_at: str
    completed_at: Optional[str] = None
    # Config snapshot
    source_language: str
    target_language: str
    compile_strategy: str
    translation_model: Optional[str] = None
    enable_verification: bool
    generate_glossary: bool
    use_author_api: bool
    # Typography formatting snapshot (JSONB)
    formatting: Optional[Dict[str, Any]] = None


class TaskHistoryResponse(BaseModel):
    """Paginated history response"""
    tasks: List[TaskHistoryItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class TaskDetailResponse(BaseModel):
    """Detailed task information"""
    task_id: str
    source_type: str
    arxiv_id: Optional[str] = None
    # Config snapshot
    source_language: str
    target_language: str
    translation_mode: str
    compile_strategy: str
    translation_model: Optional[str] = None
    enable_verification: bool
    generate_glossary: bool
    use_author_api: bool
    # Typography formatting snapshot (JSONB)
    formatting: Optional[Dict[str, Any]] = None
    # Status
    status: str
    progress: int
    stage: str
    message: Optional[str] = None
    error: Optional[str] = None
    # Paths (for download/preview)
    source_path: Optional[str] = None
    output_path: Optional[str] = None
    # Timestamps
    created_at: str
    completed_at: Optional[str] = None


@router.get("/history", response_model=TaskHistoryResponse)
async def get_user_history(
    supabase: Optional[Client] = Depends(get_supabase_client_from_request),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status")
):
    """
    Get user's translation history with pagination.
    
    纯 RLS 模式：RLS 自动过滤只返回当前用户的记录。
    """
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # RLS 自动过滤：只返回当前用户的任务
        query = supabase.table("translation_tasks").select(
            """task_id, source_type, arxiv_id, translation_mode, status, progress, 
               created_at, completed_at, source_language, target_language, 
               compile_strategy, translation_model, enable_verification, 
               generate_glossary, use_author_api, formatting""",
            count="exact"
        )
        
        if status_filter:
            query = query.eq("status", status_filter)
        
        # Add ordering and pagination
        offset = (page - 1) * page_size
        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
        
        result = query.execute()
        
        tasks = [
            TaskHistoryItem(
                task_id=task["task_id"],
                source_type=task["source_type"],
                arxiv_id=task.get("arxiv_id"),
                translation_mode=task.get("translation_mode", "full"),
                status=task["status"],
                progress=task.get("progress", 0),
                created_at=task["created_at"],
                completed_at=task.get("completed_at"),
                source_language=task.get("source_language", "en"),
                target_language=task.get("target_language", "zh"),
                compile_strategy=task.get("compile_strategy", "auto"),
                translation_model=task.get("translation_model"),
                enable_verification=task.get("enable_verification", True),
                generate_glossary=task.get("generate_glossary", True),
                use_author_api=task.get("use_author_api", True),
                formatting=task.get("formatting"),
            )
            for task in result.data
        ]
        
        total = result.count or 0
        
        return TaskHistoryResponse(
            tasks=tasks,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + len(tasks)) < total
        )
        
    except Exception as e:
        if "JWT" in str(e) or "token" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}"
        )


@router.get("/history/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(
    task_id: str,
    supabase: Optional[Client] = Depends(get_supabase_client_from_request)
):
    """
    Get detailed information about a specific task.
    
    纯 RLS 模式：RLS 确保只能访问自己的任务。
    """
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # RLS 自动过滤：只能查看自己的任务
        result = supabase.table("translation_tasks").select("*").eq(
            "task_id", task_id
        ).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        task = result.data[0]
        
        return TaskDetailResponse(
            task_id=task["task_id"],
            source_type=task["source_type"],
            arxiv_id=task.get("arxiv_id"),
            source_language=task.get("source_language", "en"),
            target_language=task.get("target_language", "zh"),
            translation_mode=task.get("translation_mode", "full"),
            compile_strategy=task.get("compile_strategy", "auto"),
            translation_model=task.get("translation_model"),
            enable_verification=task.get("enable_verification", True),
            generate_glossary=task.get("generate_glossary", True),
            use_author_api=task.get("use_author_api", True),
            formatting=task.get("formatting"),
            status=task["status"],
            progress=task.get("progress", 0),
            stage=task.get("stage", "idle"),
            message=task.get("message"),
            error=task.get("error"),
            source_path=task.get("source_path"),
            output_path=task.get("output_path"),
            created_at=task["created_at"],
            completed_at=task.get("completed_at"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        if "JWT" in str(e) or "token" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task detail: {str(e)}"
        )


@router.delete("/history/{task_id}")
async def delete_task_history(
    task_id: str,
    supabase: Optional[Client] = Depends(get_supabase_client_from_request)
):
    """
    Delete a single task from history.
    
    纯 RLS 模式：RLS 确保只能删除自己的任务。
    
    处理流程：
    1. 检查任务是否存在（RLS 过滤）
    2. 如果是 processing 状态，先标记为 cancelled 并等待 0.5s
    3. 删除 Supabase 记录
    4. 删除本地文件系统（uploads/outputs/terms）
    """
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    from backend.app.services.task_manager import get_task_manager
    import asyncio
    
    task_manager = get_task_manager()
    
    try:
        # 1. Check if task exists (RLS filtering)
        result = supabase.table("translation_tasks").select("status").eq(
            "task_id", task_id
        ).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        current_status = result.data[0].get("status")
        
        # 2. If task is processing, cancel it first
        if current_status == "processing":
            task_manager.cancel_task(task_id)
            # Wait briefly for the task to detect cancellation
            await asyncio.sleep(0.5)
        
        # 3. Delete from Supabase (RLS ensures only own tasks)
        delete_result = supabase.table("translation_tasks").delete().eq(
            "task_id", task_id
        ).execute()
        
        # 4. Delete local files
        deletion_result = task_manager.delete_task_full(task_id)
        
        return {
            "message": "Task deleted successfully",
            "task_id": task_id,
            "deleted_dirs": deletion_result["deleted_dirs"],
            "errors": deletion_result["errors"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if "JWT" in str(e) or "token" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}"
        )


class BatchDeleteRequest(BaseModel):
    """Batch delete request"""
    task_ids: List[str]


@router.delete("/history")
async def delete_tasks_batch(
    request: BatchDeleteRequest,
    supabase: Optional[Client] = Depends(get_supabase_client_from_request)
):
    """
    Delete multiple tasks in batch.
    
    纯 RLS 模式：RLS 确保只能删除自己的任务。
    
    Returns summary of deletion results for each task.
    """
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    from backend.app.services.task_manager import get_task_manager
    import asyncio
    
    task_manager = get_task_manager()
    results = []
    
    for task_id in request.task_ids:
        try:
            # Check task exists
            result = supabase.table("translation_tasks").select("status").eq(
                "task_id", task_id
            ).execute()
            
            if not result.data or len(result.data) == 0:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "error": "Task not found"
                })
                continue
            
            current_status = result.data[0].get("status")
            
            # Cancel if processing
            if current_status == "processing":
                task_manager.cancel_task(task_id)
                await asyncio.sleep(0.3)  # Shorter wait in batch mode
            
            # Delete from Supabase
            supabase.table("translation_tasks").delete().eq(
                "task_id", task_id
            ).execute()
            
            # Delete local files
            deletion_result = task_manager.delete_task_full(task_id)
            
            results.append({
                "task_id": task_id,
                "success": deletion_result["success"],
                "deleted_dirs": deletion_result["deleted_dirs"],
                "errors": deletion_result["errors"]
            })
            
        except Exception as e:
            results.append({
                "task_id": task_id,
                "success": False,
                "error": str(e)
            })
    
    success_count = sum(1 for r in results if r["success"])
    
    return {
        "message": f"Deleted {success_count}/{len(request.task_ids)} tasks",
        "results": results
    }

