from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from backend.app.api.routes.translate import TranslateRequest
from backend.app.core.auth import optional_current_user
from backend.app.services import community_content_pool_service, paper_service

router = APIRouter(prefix="/papers")
security = HTTPBearer(auto_error=False)


def _require_authenticated_credentials(credentials: Optional[HTTPAuthorizationCredentials]) -> None:
    if credentials is not None:
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


class AssetSummary(BaseModel):
    id: str
    task_id: Optional[str] = None
    asset_type: str
    file_name: str
    mime_type: str
    created_at: Optional[str] = None


class ViewerState(BaseModel):
    liked: bool = False
    favorited: bool = False


class PaperSummary(BaseModel):
    id: str
    source: str
    arxiv_id: Optional[str] = None
    title: str
    authors: List[Any] = []
    categories: List[str] = []
    abstract_raw: Optional[str] = None
    abstract_translated: Optional[str] = None
    community_status: str
    trans_status: str
    created_at: Optional[str] = None
    official_published_at: Optional[str] = None
    community_selected_task_id: Optional[str] = None
    community_selected_asset_id: Optional[str] = None
    visibility: Optional[str] = None
    status: Optional[str] = None
    like_count: Optional[int] = None
    favorite_count: Optional[int] = None
    comment_count: Optional[int] = None
    view_count: Optional[int] = None
    download_count: Optional[int] = None
    latest_asset: Optional[AssetSummary] = None
    assets: Optional[Dict[str, AssetSummary]] = None
    viewer_state: Optional[ViewerState] = None


class TaskSummary(BaseModel):
    task_id: Optional[str] = None
    status: Optional[str] = None


class PaperSubmitResponse(BaseModel):
    paper: PaperSummary
    task: TaskSummary
    admission_result: str


class PaperListResponse(BaseModel):
    items: List[PaperSummary]
    total: int
    source_mode: str = "database"


class ContentPoolReadinessResponse(BaseModel):
    candidate_total: int
    warmed_total: int
    translated_ready_total: int
    failure_total: int
    running_total: int
    freshness: Optional[str] = None
    stage_totals: Dict[str, int]
    updated_at: str


class ContentPoolJobEventResponse(BaseModel):
    timestamp: str
    arxiv_id: str
    stage: str
    status: str
    attempt: int
    payload: Dict[str, Any] = {}
    error: Optional[str] = None


class PaperDetailResponse(BaseModel):
    paper: PaperSummary
    preview: Optional["PaperPreviewResponse"] = None
    reader_state: str = "unavailable"
    reader: Optional[Dict[str, Any]] = None
    experience: Optional[Dict[str, Any]] = None


class PaperViewResponse(BaseModel):
    paper_id: str
    view_count: int


class PaperTranslateResponse(BaseModel):
    paper_id: str
    task_id: str
    status: str
    reused_existing_task: bool
    processing_url: str


class PaperPreviewResponse(BaseModel):
    paper_id: str
    task_id: Optional[str] = None
    asset: AssetSummary
    html_content: str
    generated_at: Optional[str] = None


class PaperDownloadSessionResponse(BaseModel):
    paper_id: str
    asset_id: str
    download_url: str
    expires_at: str


PaperDetailResponse.model_rebuild()


class PaperImportRequest(BaseModel):
    source: str = "arxiv"
    arxiv_id: Optional[str] = None


class PaperImportResponse(BaseModel):
    paper_id: str
    reused: bool
    imported: bool
    reader_state: str


@router.post("/submit", response_model=PaperSubmitResponse)
async def submit_paper(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise HTTPException(status_code=400, detail="file is required")

        source_language = str(form.get("source_language") or "en")
        target_language = str(form.get("target_language") or "zh")
        payload = await paper_service.submit_uploaded_paper(
            file=file,
            credentials=credentials,
            source_language=source_language,
            target_language=target_language,
        )
        return payload

    if "application/json" in content_type or content_type == "":
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        arxiv_id = body.get("arxiv_id") if isinstance(body, dict) else None
        if not arxiv_id:
            raise HTTPException(status_code=400, detail="arxiv_id is required")

        payload = await paper_service.submit_arxiv_paper(
            arxiv_id=str(arxiv_id),
            credentials=credentials,
            source_language=str(body.get("source_language") or "en"),
            target_language=str(body.get("target_language") or "zh"),
        )
        return payload

    raise HTTPException(status_code=400, detail="Unsupported content type")


@router.post("/import", response_model=PaperImportResponse)
async def import_paper(request: PaperImportRequest):
    if not request.arxiv_id:
        raise HTTPException(status_code=400, detail="arxiv_id is required")

    result = await paper_service.import_or_reuse_paper(
        source=request.source,
        arxiv_id=request.arxiv_id,
    )
    return PaperImportResponse(**result)


@router.get("", response_model=PaperListResponse)
async def list_papers(
    response: Response,
    sort: str = "latest",
    q: Optional[str] = None,
    limit: Optional[int] = Query(default=None, ge=1, le=12),
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
):
    user_id = str(current_user.get("id")) if isinstance(current_user, dict) and current_user.get("id") else None
    payload = await paper_service.list_community_papers(
        sort=sort,
        q=q,
        viewer_user_id=user_id,
        limit=limit,
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    response.headers["X-Community-Source-Mode"] = payload.get("source_mode", "database")
    return payload


@router.get("/content-pool/readiness", response_model=ContentPoolReadinessResponse)
async def get_content_pool_readiness(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    _require_authenticated_credentials(credentials)
    return community_content_pool_service.get_content_pool_readiness_snapshot()


@router.get("/content-pool/jobs", response_model=List[ContentPoolJobEventResponse])
async def get_content_pool_job_log(
    arxiv_id: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    _require_authenticated_credentials(credentials)
    return community_content_pool_service.get_content_pool_job_log(arxiv_id=arxiv_id, limit=limit)


@router.get("/{paper_id}", response_model=PaperDetailResponse)
async def get_paper_detail(
    paper_id: str,
    response: Response,
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
):
    user_id = str(current_user.get("id")) if isinstance(current_user, dict) and current_user.get("id") else None
    payload = await paper_service.get_community_paper_detail(
        paper_id=paper_id,
        viewer_user_id=user_id,
        fast_path=True,
    )
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=120"
    response.headers["X-Reader-State"] = payload.get("reader_state", "unavailable")
    return payload


@router.post("/{paper_id}/view", response_model=PaperViewResponse)
async def record_paper_view(paper_id: str):
    return await paper_service.record_community_paper_view(paper_id=paper_id)


@router.post("/{paper_id}/translate", response_model=PaperTranslateResponse)
async def translate_paper(
    paper_id: str,
    request: TranslateRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    return await paper_service.start_paper_translation(
        paper_id=paper_id,
        request=request,
        credentials=credentials,
    )


@router.get("/{paper_id}/preview", response_model=PaperPreviewResponse)
async def preview_paper(paper_id: str, response: Response):
    payload = await paper_service.get_paper_preview(paper_id=paper_id)
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    return payload


@router.post("/{paper_id}/download-session", response_model=PaperDownloadSessionResponse)
async def create_download_session(paper_id: str):
    return await paper_service.create_paper_download_session(paper_id=paper_id)


@router.get("/{paper_id}/download")
async def download_paper(
    paper_id: str,
    token: str = Query(..., min_length=8),
):
    payload = await paper_service.resolve_paper_download(paper_id=paper_id, token=token)
    asset = payload["asset"]
    return FileResponse(
        path=payload["file_path"],
        media_type=asset.get("mime_type") or "application/octet-stream",
        filename=asset.get("file_name") or f"{paper_id}.pdf",
    )
