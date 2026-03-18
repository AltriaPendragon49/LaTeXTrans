from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from backend.app.services import paper_service

router = APIRouter(prefix="/papers")
security = HTTPBearer(auto_error=False)


def _decode_user_id(credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    if credentials is None or credentials.credentials.count(".") != 2:
        return None

    try:
        payload_b64 = credentials.credentials.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")))
        if isinstance(payload, dict):
            return payload.get("sub")
    except Exception:
        return None
    return None


class AssetSummary(BaseModel):
    id: str
    task_id: Optional[str] = None
    asset_type: str
    file_path: str
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


class PaperDetailResponse(BaseModel):
    paper: PaperSummary


class PaperViewResponse(BaseModel):
    paper_id: str
    view_count: int


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


@router.get("", response_model=PaperListResponse)
async def list_papers(
    sort: str = "latest",
    q: Optional[str] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    user_id = _decode_user_id(credentials)
    return await paper_service.list_community_papers(
        sort=sort,
        q=q,
        viewer_user_id=user_id,
    )


@router.get("/{paper_id}", response_model=PaperDetailResponse)
async def get_paper_detail(
    paper_id: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    user_id = _decode_user_id(credentials)
    return await paper_service.get_community_paper_detail(
        paper_id=paper_id,
        viewer_user_id=user_id,
    )


@router.post("/{paper_id}/view", response_model=PaperViewResponse)
async def record_paper_view(paper_id: str):
    return await paper_service.record_community_paper_view(paper_id=paper_id)
