from __future__ import annotations

import asyncio
import base64
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from starlette.background import BackgroundTask

from backend.app.api.routes import download as download_route
from backend.app.api.routes.translate import TranslateRequest
from backend.app.core.auth import optional_current_user, require_current_user
from backend.app.core.config import get_settings
from backend.app.policies import authorize
from backend.app.services import community_content_pool_service, paper_preview_service, paper_service, paper_thumbnail_service

router = APIRouter(prefix="/papers")
security = HTTPBearer(auto_error=False)
settings = get_settings()
LOCAL_PDF_PREVIEW_CHUNK_SIZE = 64 * 1024
THUMBNAIL_CACHE_VERSION = "v3"


def _ensure_paper_authorized(
    current_user: Optional[Dict[str, Any]],
    action: str,
) -> None:
    decision = authorize(current_user, "paper", action)
    if decision.allowed:
        return

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_SESSION_INVALID", "message": decision.reason},
            headers={"WWW-Authenticate": "Bearer"},
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "AUTH_FORBIDDEN", "message": decision.reason},
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
    arxiv_url: Optional[str] = None
    github_url: Optional[str] = None
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
    offset: int = 0
    limit: Optional[int] = None
    has_more: bool = False
    next_offset: Optional[int] = None
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
    preview: Optional["PaperPreviewBootstrapResponse"] = None
    reader_state: str = "unavailable"
    reader: Optional[Dict[str, Any]] = None
    experience: Optional[Dict[str, Any]] = None
    structured_insights: Optional[Dict[str, Any]] = None


class SimilarPaperItemResponse(BaseModel):
    arxiv_id: str
    title: str
    abstract: str
    arxiv_url: str
    community_paper_id: Optional[str] = None
    link_type: str


class SimilarPaperListResponse(BaseModel):
    items: List[SimilarPaperItemResponse]


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


class PaperPreviewBootstrapResponse(BaseModel):
    paper_id: str
    task_id: Optional[str] = None
    asset: AssetSummary
    generated_at: Optional[str] = None
    fetch_url: str


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


class AdminArxivCurationRequest(BaseModel):
    arxiv_ids: List[str]
    source_language: str = "en"
    target_language: str = "zh"


class AdminCurationBatchItemResponse(BaseModel):
    job_id: str
    paper_id: Optional[str] = None
    source_type: str
    arxiv_id: Optional[str] = None
    original_filename: Optional[str] = None
    status: str
    error: Optional[str] = None


class AdminCurationBatchResponse(BaseModel):
    batch_id: str
    status: str
    items: List[AdminCurationBatchItemResponse]


class AdminCurationJobHistoryItemResponse(BaseModel):
    job_id: str
    batch_id: str
    paper_id: Optional[str] = None
    published_paper_id: Optional[str] = None
    task_id: Optional[str] = None
    source_type: str
    arxiv_id: Optional[str] = None
    original_filename: Optional[str] = None
    status: str
    terminal_task_status: Optional[str] = None
    terminal_reason: Optional[str] = None
    timeout_reason: Optional[str] = None
    error: Optional[str] = None
    failed_artifact_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AdminCurationJobHistoryResponse(BaseModel):
    items: List[AdminCurationJobHistoryItemResponse]
    total: int


class AdminDeletePaperResponse(BaseModel):
    job_id: str
    paper_id: str
    status: str


class AdminDeleteCurationJobResponse(BaseModel):
    job_id: str
    paper_id: Optional[str] = None
    status: str


class AdminBatchDeleteCurationJobsRequest(BaseModel):
    job_ids: List[str]


class AdminBatchDeleteCurationJobsFailureResponse(BaseModel):
    job_id: str
    status_code: int
    detail: Optional[str] = None


class AdminBatchDeleteCurationJobsResponse(BaseModel):
    deleted: List[AdminDeleteCurationJobResponse]
    failed: List[AdminBatchDeleteCurationJobsFailureResponse]
    deleted_count: int
    failed_count: int


def _ensure_local_admin(current_user: Optional[Dict[str, Any]]) -> None:
    roles = {str(role or "").strip().lower() for role in (current_user or {}).get("roles", [])}
    if "admin" in roles:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "AUTH_FORBIDDEN", "message": "Admin role required."},
    )


async def _proxy_remote_pdf_preview(*, url: str, filename: str, request: Request) -> Response:
    upstream_headers: Dict[str, str] = {
        "User-Agent": "LaTeXTrans-Preview/1.0",
    }
    range_header = request.headers.get("range")
    if range_header:
        upstream_headers["Range"] = range_header

    client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)
    upstream_request = client.build_request("GET", url, headers=upstream_headers)
    try:
        upstream_response = await client.send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Translated PDF upstream fetch failed") from exc

    if upstream_response.status_code not in (200, 206):
        await upstream_response.aclose()
        await client.aclose()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Translated PDF upstream response invalid")

    response_headers = {
        "Cache-Control": "public, max-age=300, stale-while-revalidate=600",
        "Content-Disposition": f'inline; filename="{filename}"',
    }
    for source_name, target_name in (
        ("accept-ranges", "Accept-Ranges"),
        ("content-range", "Content-Range"),
        ("content-length", "Content-Length"),
        ("etag", "ETag"),
        ("last-modified", "Last-Modified"),
    ):
        value = upstream_response.headers.get(source_name)
        if value:
            response_headers[target_name] = value

    media_type = upstream_response.headers.get("content-type") or "application/pdf"

    async def _stream():
        async for chunk in upstream_response.aiter_bytes():
            if chunk:
                yield chunk

    async def _close_stream() -> None:
        await upstream_response.aclose()
        await client.aclose()

    return StreamingResponse(
        _stream(),
        status_code=upstream_response.status_code,
        media_type=media_type,
        headers=response_headers,
        background=BackgroundTask(_close_stream),
    )


def _parse_single_byte_range(range_header: Optional[str], total_size: int) -> Optional[tuple[int, int]]:
    normalized = str(range_header or "").strip()
    if not normalized.startswith("bytes="):
        return None

    value = normalized[len("bytes=") :].strip()
    if not value or "," in value:
        return None

    start_raw, _, end_raw = value.partition("-")
    try:
        if start_raw == "":
            suffix_length = int(end_raw)
            if suffix_length <= 0:
                return None
            end = total_size - 1
            start = max(total_size - suffix_length, 0)
        else:
            start = int(start_raw)
            if start < 0 or start >= total_size:
                return None
            end = int(end_raw) if end_raw else total_size - 1
            if end < start:
                return None
            end = min(end, total_size - 1)
    except ValueError:
        return None

    return start, end


async def _serve_local_pdf_preview(
    *,
    file_path: Path,
    filename: str,
    request: Request,
    cache_control: str,
    content_disposition: str = "inline",
) -> Response:
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF file not found")

    total_size = file_path.stat().st_size
    base_headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": cache_control,
        "Content-Disposition": f'{content_disposition}; filename="{filename}"',
    }
    range_header = request.headers.get("range")
    byte_range = _parse_single_byte_range(range_header, total_size)

    if range_header and byte_range is None:
        return Response(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            headers={
                **base_headers,
                "Content-Range": f"bytes */{total_size}",
            },
        )

    if byte_range is None:
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            headers=base_headers,
        )

    start, end = byte_range
    content_length = end - start + 1

    async def _stream():
        with open(file_path, "rb") as handle:
            handle.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk = handle.read(min(LOCAL_PDF_PREVIEW_CHUNK_SIZE, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        _stream(),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type="application/pdf",
        headers={
            **base_headers,
            "Content-Length": str(content_length),
            "Content-Range": f"bytes {start}-{end}/{total_size}",
        },
    )


def _paper_thumbnail_cache_dir() -> Path:
    cache_dir = settings.storage_temp_dir / "paper_pdf_thumbnails"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _decode_png_data_uri(payload: Optional[str]) -> Optional[bytes]:
    normalized = str(payload or "")
    if not normalized.startswith("data:image/png;base64,"):
        return None
    encoded = normalized.split(",", 1)[1]
    try:
        return base64.b64decode(encoded)
    except Exception:
        return None


def _thumbnail_cache_path(cache_seed: str) -> Path:
    digest = hashlib.sha256(f"{THUMBNAIL_CACHE_VERSION}:{cache_seed}".encode("utf-8")).hexdigest()
    return _paper_thumbnail_cache_dir() / f"{digest}.png"


def _render_pdf_thumbnail_bytes_from_path(pdf_path: Path) -> Optional[bytes]:
    rasterizer = shutil.which("pdftocairo") or shutil.which("pdftoppm")
    if not rasterizer:
        data_uri = paper_preview_service._inline_pdf_data_uri(pdf_path)
        return _decode_png_data_uri(data_uri)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_prefix = Path(temp_dir) / "page"
            command = [
                rasterizer,
                "-f",
                "1",
                "-l",
                "1",
                "-singlefile",
                "-png",
                "-scale-to-x",
                "480",
                "-scale-to-y",
                "-1",
                str(pdf_path),
                str(output_prefix),
            ]
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                timeout=30,
            )
            rendered = output_prefix.with_suffix(".png")
            return rendered.read_bytes() if rendered.exists() else None
    except Exception:
        data_uri = paper_preview_service._inline_pdf_data_uri(pdf_path)
        return _decode_png_data_uri(data_uri)


async def _render_pdf_thumbnail_bytes_from_url(url: str) -> Optional[bytes]:
    client = httpx.AsyncClient(follow_redirects=True, timeout=120.0)
    upstream_request = client.build_request(
        "GET",
        url,
        headers={"User-Agent": "LaTeXTrans-Preview/1.0"},
    )
    temp_path: Optional[Path] = None
    upstream_response = None
    try:
        upstream_response = await client.send(upstream_request, stream=True)
        if upstream_response.status_code >= 400:
            return None

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            async for chunk in upstream_response.aiter_bytes():
                if chunk:
                    temp_file.write(chunk)

        return await asyncio.to_thread(_render_pdf_thumbnail_bytes_from_path, temp_path)
    except httpx.HTTPError:
        return None
    finally:
        if upstream_response is not None:
            await upstream_response.aclose()
        await client.aclose()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


async def _serve_pdf_thumbnail_response(
    *,
    cache_seed: str,
    file_path: Optional[str] = None,
    remote_url: Optional[str] = None,
) -> Response:
    cache_path = await paper_thumbnail_service.ensure_pdf_thumbnail(
        cache_seed=cache_seed,
        file_path=file_path,
        remote_url=remote_url,
    )
    if not cache_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF thumbnail not available")
    return FileResponse(
        path=cache_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"},
    )


@router.post("/submit", response_model=PaperSubmitResponse)
async def submit_paper(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    current_user: Optional[Dict[str, Any]] = Depends(require_current_user),
):
    _ensure_paper_authorized(current_user, "submit")
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_SESSION_INVALID", "message": "Session is invalid or expired."},
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
            current_user=current_user,
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
            current_user=current_user,
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


@router.get("", response_model=PaperListResponse, response_model_exclude_none=True)
async def list_papers(
    response: Response,
    sort: str = "latest",
    q: Optional[str] = None,
    limit: Optional[int] = Query(default=12, ge=1, le=24),
    offset: int = Query(default=0, ge=0),
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
):
    user_id = str(current_user.get("id")) if isinstance(current_user, dict) and current_user.get("id") else None
    payload = await paper_service.list_community_papers(
        sort=sort,
        q=q,
        viewer_user_id=user_id,
        limit=limit,
        offset=offset,
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    response.headers["X-Community-Source-Mode"] = payload.get("source_mode", "database")
    return payload


@router.get("/content-pool/readiness", response_model=ContentPoolReadinessResponse)
async def get_content_pool_readiness(
    current_user: Optional[Dict[str, Any]] = Depends(require_current_user),
):
    _ensure_paper_authorized(current_user, "content_pool_read")
    return community_content_pool_service.get_content_pool_readiness_snapshot()


@router.get("/content-pool/jobs", response_model=List[ContentPoolJobEventResponse])
async def get_content_pool_job_log(
    arxiv_id: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: Optional[Dict[str, Any]] = Depends(require_current_user),
):
    _ensure_paper_authorized(current_user, "content_pool_read")
    return community_content_pool_service.get_content_pool_job_log(arxiv_id=arxiv_id, limit=limit)


@router.post(
    "/admin/curation/arxiv",
    response_model=AdminCurationBatchResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_admin_arxiv_curation_batch(
    request: AdminArxivCurationRequest,
    current_user: Optional[Dict[str, Any]] = Depends(require_current_user),
):
    _ensure_local_admin(current_user)
    return await paper_service.submit_admin_arxiv_curation_batch(
        arxiv_ids=request.arxiv_ids,
        current_user=current_user,
        source_language=request.source_language,
        target_language=request.target_language,
    )


@router.get(
    "/admin/curation/batches/{batch_id}",
    response_model=AdminCurationBatchResponse,
    response_model_exclude_none=True,
)
async def get_admin_curation_batch(
    batch_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(require_current_user),
):
    _ensure_local_admin(current_user)
    return await paper_service.get_admin_curation_batch(batch_id=batch_id)


@router.get(
    "/admin/curation/jobs",
    response_model=AdminCurationJobHistoryResponse,
    response_model_exclude_none=True,
)
async def list_admin_curation_jobs(
    status: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    current_user: Optional[Dict[str, Any]] = Depends(require_current_user),
):
    _ensure_local_admin(current_user)
    normalized_status = str(status or "").strip().lower()
    status_filter = None if normalized_status in {"", "all"} else normalized_status
    normalized_query = str(q or "").strip() or None
    return await paper_service.list_admin_curation_jobs(
        status_filter=status_filter,
        search=normalized_query,
    )


@router.post(
    "/admin/curation/uploads",
    response_model=AdminCurationBatchResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_admin_upload_curation_batch(
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(require_current_user),
):
    _ensure_local_admin(current_user)
    form = await request.form()
    files = [
        value
        for _key, value in form.multi_items()
        if hasattr(value, "filename") and hasattr(value, "file")
    ]
    if not files:
        raise HTTPException(status_code=400, detail="At least one upload file is required")
    source_language = str(form.get("source_language") or "en")
    target_language = str(form.get("target_language") or "zh")
    return await paper_service.submit_admin_upload_curation_batch(
        files=files,
        current_user=current_user,
        source_language=source_language,
        target_language=target_language,
    )


@router.delete(
    "/admin/curation/jobs/{job_id}",
    response_model=AdminDeleteCurationJobResponse,
)
async def delete_admin_curation_job(
    job_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(require_current_user),
):
    _ensure_local_admin(current_user)
    return await paper_service.delete_admin_curation_job(
        job_id=job_id,
        current_user=current_user,
    )


@router.post(
    "/admin/curation/jobs/batch-delete",
    response_model=AdminBatchDeleteCurationJobsResponse,
)
async def batch_delete_admin_curation_jobs(
    request: AdminBatchDeleteCurationJobsRequest,
    current_user: Optional[Dict[str, Any]] = Depends(require_current_user),
):
    _ensure_local_admin(current_user)
    return await paper_service.batch_delete_admin_curation_jobs(
        job_ids=request.job_ids,
        current_user=current_user,
    )


@router.delete(
    "/admin/{paper_id}",
    response_model=AdminDeletePaperResponse,
    response_model_exclude_none=True,
)
async def delete_admin_community_paper(
    paper_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(require_current_user),
):
    _ensure_local_admin(current_user)
    return await paper_service.delete_community_paper_admin(
        paper_id=paper_id,
        current_user=current_user,
    )


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


@router.get(
    "/{paper_id}/similar",
    response_model=SimilarPaperListResponse,
    response_model_exclude_none=True,
)
async def get_paper_similar(
    paper_id: str,
    response: Response,
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
):
    _ = current_user
    payload = await paper_service.get_community_paper_similar(paper_id=paper_id)
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    return payload


@router.post("/{paper_id}/view", response_model=PaperViewResponse)
async def record_paper_view(paper_id: str):
    return await paper_service.record_community_paper_view(paper_id=paper_id)


@router.post("/{paper_id}/translate", response_model=PaperTranslateResponse)
async def translate_paper(
    paper_id: str,
    request: TranslateRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
):
    return await paper_service.start_paper_translation(
        paper_id=paper_id,
        request=request,
        credentials=credentials,
        current_user=current_user,
    )


@router.get("/{paper_id}/preview", response_model=PaperPreviewResponse)
async def preview_paper(paper_id: str, response: Response):
    payload = await paper_service.get_paper_preview(paper_id=paper_id)
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    return payload


@router.get("/{paper_id}/translated-pdf")
async def preview_translated_paper_pdf(paper_id: str, request: Request):
    payload = await paper_service.resolve_paper_translated_pdf_preview(paper_id=paper_id)
    asset = payload["asset"]
    filename = asset.get("file_name") or f"{paper_id}.pdf"
    if payload.get("signed_url"):
        return await _proxy_remote_pdf_preview(
            url=payload["signed_url"],
            filename=str(filename),
            request=request,
        )
    return await _serve_local_pdf_preview(
        file_path=Path(payload["file_path"]),
        filename=str(filename),
        request=request,
        cache_control="public, max-age=300, stale-while-revalidate=600",
    )


@router.get("/{paper_id}/translated-thumbnail")
async def preview_translated_paper_thumbnail(paper_id: str):
    payload = await paper_service.resolve_paper_translated_pdf_preview(paper_id=paper_id)
    asset = payload["asset"]
    cache_seed = f"translated:{paper_id}:{asset.get('id') or asset.get('file_name') or paper_id}"
    if payload.get("signed_url"):
        return await _serve_pdf_thumbnail_response(
            cache_seed=cache_seed,
            remote_url=payload["signed_url"],
        )
    return await _serve_pdf_thumbnail_response(
        cache_seed=cache_seed,
        file_path=payload["file_path"],
    )


@router.get("/{paper_id}/source-pdf")
async def preview_source_paper_pdf(paper_id: str, request: Request):
    payload = await paper_service.resolve_paper_source_pdf_preview(paper_id=paper_id)

    arxiv_id = str(payload.get("arxiv_id") or "").strip()
    if arxiv_id:
        return await download_route._proxy_arxiv_pdf(
            arxiv_id,
            f"source_{arxiv_id}.pdf",
            request=request,
        )

    legacy_task_id = str(payload.get("legacy_task_id") or "").strip()
    if legacy_task_id:
        return await download_route._serve_source_pdf(
            legacy_task_id,
            request,
            content_disposition="inline",
        )

    filename = str(payload.get("filename") or f"{paper_id}.pdf")
    return await _serve_local_pdf_preview(
        file_path=Path(payload["file_path"]),
        filename=filename,
        request=request,
        cache_control="public, max-age=300, stale-while-revalidate=600",
    )


@router.get("/{paper_id}/source-download")
async def download_source_paper_pdf(paper_id: str, request: Request):
    payload = await paper_service.resolve_paper_source_pdf_preview(paper_id=paper_id)

    arxiv_id = str(payload.get("arxiv_id") or "").strip()
    if arxiv_id:
        return await download_route._proxy_arxiv_pdf(
            arxiv_id,
            f"source_{arxiv_id}.pdf",
            request=request,
            content_disposition="attachment",
        )

    legacy_task_id = str(payload.get("legacy_task_id") or "").strip()
    if legacy_task_id:
        return await download_route._serve_source_pdf(
            legacy_task_id,
            request,
            content_disposition="attachment",
        )

    filename = str(payload.get("filename") or f"{paper_id}.pdf")
    return await _serve_local_pdf_preview(
        file_path=Path(payload["file_path"]),
        filename=filename,
        request=request,
        cache_control="public, max-age=300, stale-while-revalidate=600",
        content_disposition="attachment",
    )


@router.get("/{paper_id}/source-thumbnail")
async def preview_source_paper_thumbnail(paper_id: str):
    payload = await paper_service.resolve_paper_source_pdf_preview(paper_id=paper_id)

    if payload.get("file_path"):
        file_path = str(payload["file_path"])
        resolved_path = Path(file_path)
        stat = resolved_path.stat()
        return await _serve_pdf_thumbnail_response(
            cache_seed=f"source-file:{resolved_path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}",
            file_path=file_path,
        )

    arxiv_id = str(payload.get("arxiv_id") or "").strip()
    if arxiv_id:
        return await _serve_pdf_thumbnail_response(
            cache_seed=f"source-arxiv:{arxiv_id}",
            remote_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source PDF thumbnail not available")


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
    if payload.get("signed_url"):
        return RedirectResponse(
            url=payload["signed_url"],
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    return FileResponse(
        path=payload["file_path"],
        media_type=asset.get("mime_type") or "application/octet-stream",
        filename=asset.get("file_name") or f"{paper_id}.pdf",
    )
