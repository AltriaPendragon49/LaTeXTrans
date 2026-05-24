"""RAG Terminology API Routes.

Provides endpoints for uploading, reviewing, and querying
terminology entries used in the RAG-enhanced translation pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from backend.app.core.auth import optional_current_user, require_admin_user, resolve_current_user_id
from backend.app.core.config import get_settings
from backend.app.services.rag.domain_constants import DOMAIN_LABELS_ZH, DOMAIN_GROUPS, TermDomain
from backend.app.services.terminology_service import TerminologyService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/terminology")
security = HTTPBearer(auto_error=False)

settings = get_settings()


# ---- Pydantic models ----


class TermItem(BaseModel):
    """A single terminology term record."""
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


class TermListResponse(BaseModel):
    """Paginated term list response."""
    terms: list[TermItem]
    total: int
    page: int
    page_size: int


class UploadResponse(BaseModel):
    """Response from a terminology file upload."""
    accepted: int
    rejected: int
    errors: list[str]
    term_ids: list[str]


class RejectRequest(BaseModel):
    """Request body for rejecting a term."""
    reason: Optional[str] = Field(default=None, description="Reason for rejection")


class GlossaryLookupRequest(BaseModel):
    """Request body for a glossary lookup."""
    chunk_text: str = Field(..., description="Source text chunk to look up terms for")
    source_lang: str = Field(default="en", description="Source language code")
    target_lang: str = Field(default="zh", description="Target language code")
    top_n: Optional[int] = Field(default=None, description="Max terms to return (defaults to server setting)")
    domain: Optional[str] = Field(default=None, description="Optional domain filter (e.g. 'machine_learning', 'physics'). When set, only terms from this domain are returned.")


class GlossaryLookupResponse(BaseModel):
    """Response from a glossary lookup request."""
    terms: list[TermItem]
    glossary_block: str
    match_count: int
    chunk_text: Optional[str] = None


class MatchLogItem(BaseModel):
    """A single glossary match log entry."""
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


# ---- Helpers ----


def _get_terminology_service() -> TerminologyService:
    return TerminologyService()


def _error_detail(code: str, message: str) -> dict:
    return {"code": code, "message": message}


# ---- Endpoints ----


# ---- Domain listing ----

@router.get("/domains")
async def list_domains():
    """List all available terminology domains with labels and groups."""
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


# ---- CRUD endpoints (admin) ----


class CreateTermRequest(BaseModel):
    """Request body for creating a new term."""
    source_term: str = Field(..., min_length=1, description="Source-language term")
    target_term: str = Field(..., min_length=1, description="Target-language translation")
    source_lang: str = Field(default="en", description="Source language code")
    target_lang: str = Field(default="zh", description="Target language code")
    domain: Optional[str] = Field(default=None, description="Domain category")
    source_type: str = Field(default="manual", description="Source type")
    status: str = Field(default="pending_review", description="Initial status")


class UpdateTermRequest(BaseModel):
    """Request body for updating an existing term (all fields optional)."""
    source_term: Optional[str] = Field(default=None, min_length=1)
    target_term: Optional[str] = Field(default=None, min_length=1)
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    domain: Optional[str] = None
    status: Optional[str] = None


class BatchOperationRequest(BaseModel):
    """Request body for batch operations on terms."""
    term_ids: list[str] = Field(..., min_length=1)
    operation: str = Field(..., pattern="^(approve|reject|delete)$")
    reason: Optional[str] = None


@router.post("/terms", response_model=TermItem)
async def create_term(
    body: CreateTermRequest,
    _admin: dict = Depends(require_admin_user),
):
    """Create a new terminology term (admin only)."""
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
    """Update an existing terminology term (admin only)."""
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
    """Delete a terminology term (admin only)."""
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
    """Share a personal term to admin for review (creates a copy as pending_review)."""
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
    """Batch approve, reject, or delete terms (admin only)."""
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
    """List the current user's own terminology terms."""
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
    """List all terminology terms with optional filters and pagination."""
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
    """List pending-review terms (admin only)."""
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
    """Upload a CSV or BibTeX file to import terminology terms.

    Supported file types:
      - ``.csv``: Comma-, semicolon-, or tab-separated values.
      - ``.bib``: BibTeX bibliography file.

    CSV columns (case-insensitive):
      - ``source_term`` (required): The source-language term.
      - ``target_term`` (required): The target-language translation.
      - ``source_lang`` (optional, default ``en``).
      - ``target_lang`` (optional, default ``zh``).
      - ``domain`` (optional).

    BibTeX files have term candidates extracted from entry titles.
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
    """Approve a pending term (admin only)."""
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
    """Reject a pending term with an optional reason (admin only)."""
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
    """Get glossary match logs for a translation task."""
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
    """Look up glossary terms matching a text chunk (internal pipeline use).

    Returns matching approved terms and a formatted glossary block
    suitable for injection into a translation prompt.
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
    """Trigger a BM25 index refresh (admin only)."""
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
    """Trigger a vector index rebuild (admin only)."""
    if not settings.rag_terminology_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_detail("TERMINOLOGY_DISABLED", "RAG terminology is not enabled on this server."),
        )

    service = _get_terminology_service()
    ok = service.build_vector_index()
    return {"ok": ok, "action": "build_vector_index"}
