"""RAG 术语 API 路由。

提供上传、审阅和查询用于 RAG 增强翻译管线的术语条目的接口。
"""

from __future__ import annotations

import logging
from datetime import datetime as Datetime
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from backend.app.core.auth import optional_current_user, require_admin_user, resolve_current_user_id
from backend.app.core.config import get_settings
from backend.app.services.rag.domain_constants import DOMAIN_LABELS_ZH, DOMAIN_GROUPS, TermDomain
from backend.app.services.terminology_service import TerminologyService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/terminology")
security = HTTPBearer(auto_error=False)

settings = get_settings()


# ---- Pydantic 模型 ----


class TermItem(BaseModel):
    """单条术语记录"""
    id: str
    source_term: str
    target_term: str
    source_lang: str = "en"
    target_lang: str = "zh"
    domain: Optional[str] = None
    source_type: str = "imported"
    status: str = "pending_review"
    owner_user_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    reviewed_by_user_id: Optional[str] = None
    reviewed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    extracted_from_task_id: Optional[str] = None
    provenance: Optional[Any] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("created_at", "updated_at", "reviewed_at", mode="before")
    @classmethod
    def _coerce_datetime_to_str(cls, v: Any) -> Optional[str]:
        if isinstance(v, Datetime):
            return v.isoformat()
        return v


class TermListResponse(BaseModel):
    """分页术语列表响应体"""
    terms: list[TermItem]
    total: int
    page: int
    page_size: int


class UploadResponse(BaseModel):
    """术语文件上传响应体"""
    accepted: int
    rejected: int
    errors: list[str]
    term_ids: list[str]


class RejectRequest(BaseModel):
    """拒绝术语的请求体"""
    reason: Optional[str] = Field(default=None, description="Reason for rejection")


class GlossaryLookupRequest(BaseModel):
    """术语表查找请求体"""
    chunk_text: str = Field(..., description="Source text chunk to look up terms for")
    source_lang: str = Field(default="en", description="Source language code")
    target_lang: str = Field(default="zh", description="Target language code")
    top_n: Optional[int] = Field(default=None, description="Max terms to return (defaults to server setting)")
    domain: Optional[str] = Field(default=None, description="Optional domain filter (e.g. 'machine_learning', 'physics'). When set, only terms from this domain are returned.")


class GlossaryLookupResponse(BaseModel):
    """术语表查找响应体"""
    terms: list[TermItem]
    glossary_block: str
    match_count: int
    chunk_text: Optional[str] = None


class MatchLogItem(BaseModel):
    """单条术语匹配日志条目"""
    id: str
    task_id: str
    term_id: str
    chunk_index: int = 0
    retrieval_source: str = "bm25"
    was_injected: bool = False
    rerank_score: Optional[float] = None
    source_term: Optional[str] = None
    target_term: Optional[str] = None
    created_at: Optional[str] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _coerce_datetime_to_str(cls, v: Any) -> Optional[str]:
        if isinstance(v, Datetime):
            return v.isoformat()
        return v


# ---- 辅助函数 ----


def _get_terminology_service() -> TerminologyService:
    return TerminologyService()


def _error_detail(code: str, message: str) -> dict:
    return {"code": code, "message": message}


# ---- 接口 ----


# ---- 领域列表 ----

@router.get("/domains")
async def list_domains():
    """列出所有可用的术语领域及其标签和分组"""
    domains = []
    for domain in TermDomain:
        domains.append({
            "value": domain.value,
            "label_zh": DOMAIN_LABELS_ZH.get(domain.value, domain.value),
            "group": next((g for g, members in DOMAIN_GROUPS.items() if domain.value in members), None),
        })
    return {
        "domains": domains,
        "groups": {g: {"label_zh": g, "members": members} for g, members in DOMAIN_GROUPS.items()},
    }


# ---- CRUD 接口（管理员）----


class CreateTermRequest(BaseModel):
    """创建新术语的请求体"""
    source_term: str = Field(..., min_length=1, description="Source-language term")
    target_term: str = Field(..., min_length=1, description="Target-language translation")
    source_lang: str = Field(default="en", description="Source language code")
    target_lang: str = Field(default="zh", description="Target language code")
    domain: Optional[str] = Field(default=None, description="Domain category")
    source_type: str = Field(default="manual", description="Source type")
    status: str = Field(default="pending_review", description="Initial status")


class UpdateTermRequest(BaseModel):
    """更新已有术语的请求体（所有字段可选）"""
    source_term: Optional[str] = Field(default=None, min_length=1)
    target_term: Optional[str] = Field(default=None, min_length=1)
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    domain: Optional[str] = None
    status: Optional[str] = None


class BatchOperationRequest(BaseModel):
    """批量操作术语的请求体"""
    term_ids: list[str] = Field(..., min_length=1)
    operation: str = Field(..., pattern="^(approve|reject|delete)$")
    reason: Optional[str] = None


@router.post("/terms", response_model=TermItem)
async def create_term(
    body: CreateTermRequest,
    _admin: dict = Depends(require_admin_user),
):
    """创建新术语（仅管理员）"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    reviewer_id = str(_admin.get("id", "admin"))
    result = service.create_term({
        "source_term": body.source_term,
        "target_term": body.target_term,
        "source_lang": body.source_lang,
        "target_lang": body.target_lang,
        "domain": body.domain,
        "source_type": body.source_type,
        "status": body.status,
        "owner_user_id": reviewer_id,
        "created_by_user_id": reviewer_id,
    })
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error_detail("CREATE_FAILED", "Failed to create term."),
        )
    return result


@router.put("/terms/{term_id}", response_model=dict)
async def update_term(
    term_id: str,
    body: UpdateTermRequest,
    _admin: dict = Depends(require_admin_user),
):
    """更新已有术语（仅管理员）"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    updates = {k: v for k, v in body.model_dump(exclude_none=True).items() if v is not None}
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error_detail("NO_UPDATES", "No fields to update."),
        )

    service = _get_terminology_service()
    success = service.update_term(term_id, updates)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERM_NOT_FOUND", f"Term '{term_id}' not found."),
        )
    return {"ok": True, "term_id": term_id}


@router.delete("/terms/{term_id}", response_model=dict)
async def delete_term(
    term_id: str,
    _admin: dict = Depends(require_admin_user),
):
    """删除术语（仅管理员）"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    success = service.delete_term(term_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERM_NOT_FOUND", f"Term '{term_id}' not found."),
        )
    return {"ok": True, "term_id": term_id}


@router.post("/terms/{term_id}/share", response_model=dict)
async def share_term(
    term_id: str,
    current_user: dict[str, Any] | None = Depends(optional_current_user),
):
    """将个人术语分享给管理员审阅（创建 pending_review 副本）"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    user_id = resolve_current_user_id(current_user) or "anonymous"
    service = _get_terminology_service()

    # Verify the term exists and belongs to this user
    term = service._repository.get_term(term_id)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERM_NOT_FOUND", f"Term '{term_id}' not found."),
        )
    if term.get("owner_user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_error_detail("NOT_OWNER", "You can only share your own terms."),
        )

    # Create a shared copy for admin review
    shared = service._repository.insert_term({
        "source_term": term["source_term"],
        "target_term": term["target_term"],
        "source_lang": term.get("source_lang", "en"),
        "target_lang": term.get("target_lang", "zh"),
        "domain": term.get("domain"),
        "source_type": "shared_by_user",
        "status": "pending_review",
        "owner_user_id": user_id,
        "created_by_user_id": user_id,
    })
    return {"ok": True, "shared_term_id": shared["id"]}


@router.post("/terms/batch", response_model=dict)
async def batch_operate_terms(
    body: BatchOperationRequest,
    _admin: dict = Depends(require_admin_user),
):
    """批量批准、拒绝或删除术语（仅管理员）"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    reviewer_id = str(_admin.get("id", "admin"))

    if body.operation == "approve":
        affected = service.batch_approve_terms(body.term_ids, reviewer_id)
        succeeded = affected
        failed = len(body.term_ids) - affected
    elif body.operation == "reject":
        affected = service.batch_reject_terms(body.term_ids, reviewer_id, reason=body.reason)
        succeeded = affected
        failed = len(body.term_ids) - affected
    elif body.operation == "delete":
        affected = service.batch_delete_terms(body.term_ids)
        succeeded = affected
        failed = len(body.term_ids) - affected
    else:
        succeeded = 0
        failed = len(body.term_ids)

    return {"ok": failed == 0, "operation": body.operation, "succeeded": succeeded, "failed": failed}


# ---- User terms (self-service) ----


@router.get("/my-terms", response_model=TermListResponse)
async def list_my_terms(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=200, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    current_user: dict[str, Any] | None = Depends(optional_current_user),
):
    """列出当前用户自己的术语"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    user_id = resolve_current_user_id(current_user) or "anonymous"
    service = _get_terminology_service()
    try:
        rows, total = service._repository.get_terms_by_owner(
            owner_user_id=user_id, page=page, page_size=page_size, status=status,
        )
    except Exception:
        logger.exception("Failed to list user terms")
        return {"terms": [], "total": 0, "page": page, "page_size": page_size}

    return {"terms": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/terms", response_model=TermListResponse)
async def list_terms(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=200, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status (pending_review, approved)"),
    source_type: Optional[str] = Query(default=None, description="Filter by source type (system, imported, manual, etc.)"),
    domain: Optional[str] = Query(default=None, description="Filter by domain"),
    source_lang: Optional[str] = Query(default=None, description="Filter by source language"),
    query: Optional[str] = Query(default=None, description="LIKE search on source_term"),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    current_user: dict[str, Any] | None = Depends(optional_current_user),
):
    """列出所有术语条目，支持可选过滤和分页"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    result = service.list_terms(
        page=page, page_size=page_size, status=status, source_type=source_type,
        domain=domain, source_lang=source_lang, query=query,
    )
    return result


@router.get("/pending", response_model=TermListResponse)
async def list_pending_terms(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=200, description="Items per page"),
    source_lang: Optional[str] = Query(default=None, description="Filter by source language"),
    domain: Optional[str] = Query(default=None, description="Filter by domain"),
    _admin: dict = Depends(require_admin_user),
):
    """列出待审阅的术语（仅管理员）"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    result = service.list_pending(
        page=page, page_size=page_size,
        source_lang=source_lang, domain=domain,
    )
    return result


@router.post("/upload", response_model=UploadResponse)
async def upload_terminology_file(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    current_user: dict[str, Any] | None = Depends(optional_current_user),
):
    """上传 CSV 或 BibTeX 文件以导入术语条目。

    支持的文件类型：
      - ``.csv``: 逗号、分号或制表符分隔的值。
      - ``.bib``: BibTeX 参考文献文件。

    CSV 列名（不区分大小写）：
      - ``source_term``（必需）：源语言术语。
      - ``target_term``（必需）：目标语言翻译。
      - ``source_lang``（可选，默认 ``en``）。
      - ``target_lang``（可选，默认 ``zh``）。
      - ``domain``（可选）。

    BibTeX 文件中，从条目标题提取候选术语。
    """
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    max_size = settings.rag_terminology_max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=_error_detail(
                "FILE_TOO_LARGE",
                f"File exceeds maximum upload size of {settings.rag_terminology_max_upload_size_mb} MB.",
            ),
        )

    user_id = resolve_current_user_id(current_user) or "anonymous"
    filename = (file.filename or "").lower()
    service = _get_terminology_service()

    try:
        if filename.endswith(".bib"):
            text_content = content.decode("utf-8", errors="replace")
            term_ids = service.import_bibtex(text_content, user_id)
            return UploadResponse(
                accepted=len(term_ids),
                rejected=0,
                errors=[],
                term_ids=term_ids,
            )
        else:
            result = service.import_csv(content, user_id)
            return UploadResponse(
                accepted=result.accepted,
                rejected=result.rejected,
                errors=result.errors,
                term_ids=result.term_ids,
            )
    except Exception as exc:
        logger.exception("Terminology upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error_detail("UPLOAD_FAILED", str(exc)),
        )


@router.post("/{term_id}/approve")
async def approve_term(
    term_id: str,
    _admin: dict = Depends(require_admin_user),
):
    """批准待审阅的术语（仅管理员）"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    reviewer_id = str(_admin.get("id", "admin"))
    success = service.approve_term(term_id, reviewer_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERM_NOT_FOUND", f"Term '{term_id}' not found or could not be approved."),
        )

    return {"ok": True, "term_id": term_id, "status": "approved"}


@router.post("/{term_id}/reject")
async def reject_term(
    term_id: str,
    body: RejectRequest,
    _admin: dict = Depends(require_admin_user),
):
    """拒绝待审阅的术语，可选附上拒绝原因（仅管理员）"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    reviewer_id = str(_admin.get("id", "admin"))
    success = service.reject_term(term_id, reviewer_id, reason=body.reason)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERM_NOT_FOUND", f"Term '{term_id}' not found or could not be rejected."),
        )

    return {"ok": True, "term_id": term_id, "status": "rejected"}


@router.get("/tasks/{task_id}/matches", response_model=list[MatchLogItem])
async def get_task_match_logs(
    task_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    current_user: dict[str, Any] | None = Depends(optional_current_user),
):
    """获取翻译任务的术语匹配日志"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    logs = service.get_match_logs(task_id)
    return logs


@router.post("/glossary/lookup", response_model=GlossaryLookupResponse)
async def lookup_glossary(
    body: GlossaryLookupRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    current_user: dict[str, Any] | None = Depends(optional_current_user),
):
    """查找与文本块匹配的术语表条目（内部管线使用）。

    返回匹配的已批准术语和格式化的术语块，适用于注入到翻译提示中。
    """
    if not settings.rag_terminology_enabled:
        return GlossaryLookupResponse(
            terms=[], glossary_block="", match_count=0, chunk_text=body.chunk_text,
        )

    service = _get_terminology_service()
    effective_top_n = body.top_n if body.top_n is not None else settings.rag_terminology_top_n
    result = service.get_rag_glossary(
        body.chunk_text,
        source_lang=body.source_lang,
        target_lang=body.target_lang,
        top_n=effective_top_n,
        domain=body.domain,
    )
    return GlossaryLookupResponse(
        terms=result.get("terms", []),
        glossary_block=result.get("glossary_block", ""),
        match_count=result.get("match_count", 0),
        chunk_text=body.chunk_text,
    )


@router.post("/index/refresh-bm25")
async def refresh_bm25_index(
    _admin: dict = Depends(require_admin_user),
):
    """触发 BM25 索引刷新（仅管理员）"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    ok = service.refresh_bm25_index()
    return {"ok": ok, "action": "refresh_bm25"}


@router.post("/index/build-vector")
async def build_vector_index(
    _admin: dict = Depends(require_admin_user),
):
    """触发向量索引重建（仅管理员）"""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    ok = service.build_vector_index()
    return {"ok": ok, "action": "build_vector_index"}
