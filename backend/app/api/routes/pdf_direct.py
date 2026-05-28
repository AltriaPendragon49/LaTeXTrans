"""
PDF 直接翻译 API 路由

通过后端代理 NiuTrans paper-translation API 接口。
所有接口均需本地认证。
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import Response
from starlette.responses import StreamingResponse
from typing import Optional
import io
import logging

from backend.app.core.auth import require_current_user, resolve_current_user_id
from backend.app.services.pdf_direct_service import (
    PdfDirectService,
    PdfDirectServiceError,
    TRANS_STATUS_PROCESSING,
)
from backend.app.services.translation_quota_service import TranslationQuotaService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pdf-direct", tags=["PDF Direct Translation"])


def _get_service() -> PdfDirectService:
    """获取 PDF 直接翻译服务实例"""
    return PdfDirectService()


def _get_quota_service() -> TranslationQuotaService:
    """获取翻译配额服务实例"""
    return TranslationQuotaService()


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_current_user),
    service: PdfDirectService = Depends(_get_service),
):
    user_id = resolve_current_user_id(current_user)
    """上传 PDF 文件到 NiuTrans 并获取文档页数"""
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "AUTH_SESSION_INVALID", "message": "Authentication required."})

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail={"code": "PDF_DIRECT_VALIDATION_ERROR", "message": "Only PDF files are supported."},
        )

    try:
        content = await file.read()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"code": "PDF_DIRECT_VALIDATION_ERROR", "message": "Failed to read uploaded file."},
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail={"code": "PDF_DIRECT_VALIDATION_ERROR", "message": "Uploaded file is empty."},
        )

    try:
        result = await service.upload_and_get_page_num(
            user_id=user_id,
            file_content=content,
            file_name=file.filename or "document.pdf",
        )
        return result
    except PdfDirectServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, **(exc.extra or {})})


@router.post("/{task_id}/start")
async def start_translation(
    task_id: str,
    current_user: dict = Depends(require_current_user),
    service: PdfDirectService = Depends(_get_service),
):
    """启动 PDF 直接翻译任务"""
    user_id = resolve_current_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "AUTH_SESSION_INVALID", "message": "Authentication required."})

    try:
        result = await service.start_translation(user_id=user_id, task_id=task_id)
        return result
    except PdfDirectServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, **(exc.extra or {})})


@router.get("/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(require_current_user),
    service: PdfDirectService = Depends(_get_service),
):
    """查询 PDF 直接翻译任务状态"""
    user_id = resolve_current_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "AUTH_SESSION_INVALID", "message": "Authentication required."})

    try:
        return await service.get_task_status(user_id=user_id, task_id=task_id)
    except PdfDirectServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, **(exc.extra or {})})


@router.post("/{task_id}/poll")
async def poll_task_status(
    task_id: str,
    current_user: dict = Depends(require_current_user),
    service: PdfDirectService = Depends(_get_service),
):
    """向上游轮询 PDF 直接翻译任务的最新状态"""
    user_id = resolve_current_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "AUTH_SESSION_INVALID", "message": "Authentication required."})

    try:
        return await service.poll_upstream_status(user_id=user_id, task_id=task_id)
    except PdfDirectServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, **(exc.extra or {})})


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: dict = Depends(require_current_user),
    service: PdfDirectService = Depends(_get_service),
):
    """取消 PDF 直接翻译任务"""
    user_id = resolve_current_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "AUTH_SESSION_INVALID", "message": "Authentication required."})

    try:
        return await service.cancel_task(user_id=user_id, task_id=task_id)
    except PdfDirectServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, **(exc.extra or {})})


@router.get("/{task_id}/download")
async def download_translated_pdf(
    task_id: str,
    current_user: dict = Depends(require_current_user),
    service: PdfDirectService = Depends(_get_service),
):
    """下载翻译后的 PDF 文件"""
    user_id = resolve_current_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "AUTH_SESSION_INVALID", "message": "Authentication required."})

    try:
        content, content_type = await service.download_translated_pdf(user_id=user_id, task_id=task_id)
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=translated_{task_id}.pdf",
                "Content-Length": str(len(content)),
            },
        )
    except PdfDirectServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, **(exc.extra or {})})


@router.get("")
async def list_tasks(
    current_user: dict = Depends(require_current_user),
    service: PdfDirectService = Depends(_get_service),
    quota_service: TranslationQuotaService = Depends(_get_quota_service),
):
    """列出当前用户的 PDF 直接翻译任务列表及配额快照"""
    user_id = resolve_current_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "AUTH_SESSION_INVALID", "message": "Authentication required."})

    from backend.app.repositories.pdf_direct_task_repository import PdfDirectTaskRepository
    repo = PdfDirectTaskRepository()
    tasks = repo.list_tasks_for_user(user_id)
    quota = quota_service.get_quota_snapshot(user_id)

    return {
        "tasks": [_task_to_summary(t) for t in tasks],
        "quota_snapshot": quota.get("pdf_direct"),
    }


def _task_to_summary(task: dict) -> dict:
    """将任务数据库记录转换为前端友好的摘要格式"""
    return {
        "task_id": task["id"],
        "file_name": task.get("file_name"),
        "page_num": task.get("page_num"),
        "progress": task.get("progress"),
        "trans_status": task.get("trans_status"),
        "trans_failure_cause": task.get("trans_failure_cause"),
        "status": task.get("status"),
        "has_artifact": bool(task.get("cos_artifact_key")),
        "created_at": _serialize(task.get("created_at")),
        "completed_at": _serialize(task.get("completed_at")),
    }


def _serialize(value) -> Optional[str]:
    """将时间戳值转换为 UTC ISO 字符串，支持 datetime 和 str 类型"""
    if value is None:
        return None
    from datetime import datetime, timezone
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    return str(value)
