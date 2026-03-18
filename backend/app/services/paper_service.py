from __future__ import annotations

import asyncio
import base64
import json
import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.routes import arxiv as arxiv_route
from backend.app.api.routes import upload as upload_route
from backend.app.core.supabase_client import get_supabase_admin_client
from backend.app.services.task_manager import get_task_manager
from backend.app.utils.async_blocking import run_db_blocking

logger = logging.getLogger(__name__)

task_manager = get_task_manager()

COMMUNITY_STATUS_OFFICIAL = "official"
COMMUNITY_STATUS_USER_FALLBACK = "user_fallback"
TERMINAL_TASK_STATUSES = {"completed", "failed", "failed_compilation", "structure_invalid"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    if token.count(".") != 2:
        return {}

    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


async def resolve_submitter_context(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_jwt_payload(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase admin client unavailable",
        )

    result = await run_db_blocking(
        lambda: (
            admin_client.table("user_roles")
            .select("role")
            .eq("user_id", user_id)
            .execute()
        )
    )
    roles = sorted(
        {
            row.get("role")
            for row in (result.data or [])
            if row.get("role") in {"admin", "moderator"}
        }
    )
    return {
        "user_id": user_id,
        "roles": roles,
        "is_admin": any(role in {"admin", "moderator"} for role in roles),
    }


def _paper_select_clause() -> str:
    return (
        "id, source, arxiv_id, title, authors, categories, abstract_raw, "
        "abstract_translated, visibility, status, trans_status, created_by, "
        "trans_latest_task_id, trans_latest_asset_pdf_id, like_count, favorite_count, "
        "comment_count, view_count, download_count, created_at, updated_at, "
        "community_status, community_selected_task_id, community_selected_asset_id, "
        "official_published_at"
    )


async def _fetch_paper_by_id(paper_id: str) -> Optional[Dict[str, Any]]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    result = await run_db_blocking(
        lambda: (
            admin_client.table("papers")
            .select(_paper_select_clause())
            .eq("id", paper_id)
            .limit(1)
            .execute()
        )
    )
    rows = result.data or []
    return rows[0] if rows else None


async def _fetch_paper_by_arxiv_id(arxiv_id: str) -> Optional[Dict[str, Any]]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    result = await run_db_blocking(
        lambda: (
            admin_client.table("papers")
            .select(_paper_select_clause())
            .eq("arxiv_id", arxiv_id)
            .limit(1)
            .execute()
        )
    )
    rows = result.data or []
    return rows[0] if rows else None


async def _insert_paper(payload: Dict[str, Any]) -> Dict[str, Any]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    result = await run_db_blocking(
        lambda: admin_client.table("papers").insert(payload).execute()
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=500, detail="Failed to create paper")
    return rows[0]


async def _update_paper(paper_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    result = await run_db_blocking(
        lambda: admin_client.table("papers").update(payload).eq("id", paper_id).execute()
    )
    rows = result.data or []
    if not rows:
        refreshed = await _fetch_paper_by_id(paper_id)
        if refreshed is None:
            raise HTTPException(status_code=404, detail="Paper not found")
        return refreshed
    return rows[0]


async def _fetch_latest_assets(paper_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    if not paper_ids:
        return {}

    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    result = await run_db_blocking(
        lambda: (
            admin_client.table("paper_assets")
            .select("id, paper_id, task_id, asset_type, file_path, file_name, mime_type, is_latest, created_at")
            .in_("paper_id", paper_ids)
            .eq("is_latest", True)
            .order("created_at", desc=True)
            .execute()
        )
    )

    latest_by_paper: Dict[str, Dict[str, Any]] = {}
    for row in result.data or []:
        latest_by_paper.setdefault(row["paper_id"], row)
    return latest_by_paper


async def _create_source_asset(
    *,
    paper_id: str,
    task_id: Optional[str],
    source_path: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not source_path:
        return None

    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    file_name = Path(source_path).name
    mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

    await run_db_blocking(
        lambda: (
            admin_client.table("paper_assets")
            .update({"is_latest": False})
            .eq("paper_id", paper_id)
            .eq("asset_type", "source_archive")
            .execute()
        )
    )

    result = await run_db_blocking(
        lambda: (
            admin_client.table("paper_assets")
            .insert(
                {
                    "paper_id": paper_id,
                    "task_id": task_id,
                    "asset_type": "source_archive",
                    "storage_backend": "local_disk",
                    "file_path": source_path,
                    "file_name": file_name,
                    "mime_type": mime_type,
                    "is_latest": True,
                }
            )
            .execute()
        )
    )
    rows = result.data or []
    return rows[0] if rows else None


def _serialize_latest_asset(asset: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not asset:
        return None
    return {
        "id": asset.get("id"),
        "task_id": asset.get("task_id"),
        "asset_type": asset.get("asset_type"),
        "file_path": asset.get("file_path"),
        "file_name": asset.get("file_name"),
        "mime_type": asset.get("mime_type"),
        "created_at": asset.get("created_at"),
    }


async def _fetch_viewer_state(
    paper_ids: List[str],
    *,
    user_id: Optional[str],
) -> Dict[str, Dict[str, bool]]:
    default_state = {paper_id: {"liked": False, "favorited": False} for paper_id in paper_ids}
    if not user_id or not paper_ids:
        return default_state

    admin_client = get_supabase_admin_client()
    if admin_client is None:
        return default_state

    likes = await run_db_blocking(
        lambda: (
            admin_client.table("paper_likes")
            .select("paper_id")
            .eq("user_id", user_id)
            .in_("paper_id", paper_ids)
            .execute()
        )
    )
    favorites = await run_db_blocking(
        lambda: (
            admin_client.table("paper_favorites")
            .select("paper_id")
            .eq("user_id", user_id)
            .in_("paper_id", paper_ids)
            .execute()
        )
    )

    liked_ids = {row.get("paper_id") for row in (likes.data or [])}
    favorited_ids = {row.get("paper_id") for row in (favorites.data or [])}

    for paper_id in paper_ids:
        default_state[paper_id] = {
            "liked": paper_id in liked_ids,
            "favorited": paper_id in favorited_ids,
        }
    return default_state


def _community_rank(paper: Dict[str, Any]) -> int:
    return 0 if paper.get("community_status") == COMMUNITY_STATUS_OFFICIAL else 1


def _translated_rank(paper: Dict[str, Any]) -> int:
    return 0 if paper.get("trans_status") == "completed" else 1


def _timestamp_key(value: Optional[str]) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _hot_tuple(paper: Dict[str, Any]) -> Any:
    return (
        _community_rank(paper),
        -(paper.get("view_count") or 0),
        -(paper.get("like_count") or 0),
        -_timestamp_key(paper.get("created_at")),
    )


def _latest_tuple(paper: Dict[str, Any]) -> Any:
    return (
        _community_rank(paper),
        -_timestamp_key(paper.get("official_published_at")),
        -_timestamp_key(paper.get("created_at")),
    )


def _translated_tuple(paper: Dict[str, Any]) -> Any:
    return (
        _community_rank(paper),
        _translated_rank(paper),
        -_timestamp_key(paper.get("official_published_at")),
        -_timestamp_key(paper.get("created_at")),
    )


def _sort_papers(papers: List[Dict[str, Any]], sort: str) -> List[Dict[str, Any]]:
    key_map = {
        "latest": _latest_tuple,
        "translated": _translated_tuple,
        "hot": _hot_tuple,
    }
    key = key_map.get(sort, _latest_tuple)
    return sorted(papers, key=key)


def _paper_payload(
    *,
    source: str,
    title: str,
    created_by: str,
    community_status: str,
    arxiv_id: Optional[str] = None,
    task_id: Optional[str] = None,
    selected_asset_id: Optional[str] = None,
    official_published_at: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "source": source,
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": [],
        "categories": [],
        "visibility": "public",
        "status": "published",
        "trans_status": "queued",
        "created_by": created_by,
        "trans_latest_task_id": task_id,
        "community_status": community_status,
        "community_selected_task_id": task_id,
        "community_selected_asset_id": selected_asset_id,
        "official_published_at": official_published_at,
    }


async def resolve_community_admission(
    *,
    submitter_context: Dict[str, Any],
    source_type: str,
    arxiv_id: Optional[str],
) -> Dict[str, Any]:
    is_admin = submitter_context["is_admin"]
    if source_type == "upload" or not arxiv_id:
        return {
            "community_status": COMMUNITY_STATUS_OFFICIAL if is_admin else COMMUNITY_STATUS_USER_FALLBACK,
            "admission_result": "created",
            "existing_paper": None,
            "should_create": True,
        }

    existing = await _fetch_paper_by_arxiv_id(arxiv_id)
    if not existing:
        return {
            "community_status": COMMUNITY_STATUS_OFFICIAL if is_admin else COMMUNITY_STATUS_USER_FALLBACK,
            "admission_result": "created",
            "existing_paper": None,
            "should_create": True,
        }

    if is_admin:
        return {
            "community_status": COMMUNITY_STATUS_OFFICIAL,
            "admission_result": "created",
            "existing_paper": existing,
            "should_create": False,
        }

    if existing.get("community_status") == COMMUNITY_STATUS_OFFICIAL:
        return {
            "community_status": COMMUNITY_STATUS_OFFICIAL,
            "admission_result": "reused_existing_official",
            "existing_paper": existing,
            "should_create": False,
        }

    return {
        "community_status": COMMUNITY_STATUS_USER_FALLBACK,
        "admission_result": "reused_existing_fallback",
        "existing_paper": existing,
        "should_create": False,
    }


async def _watch_task_and_sync_asset(
    *,
    paper_id: str,
    task_id: str,
    promote_to_official: bool,
) -> None:
    for _ in range(90):
        task = task_manager.get_task(task_id)
        if task:
            if task.get("source_available") and task.get("source_path"):
                asset = await _create_source_asset(
                    paper_id=paper_id,
                    task_id=task_id,
                    source_path=task.get("source_path"),
                )
                update_payload: Dict[str, Any] = {
                    "community_selected_asset_id": asset.get("id") if asset else None,
                    "trans_status": "queued",
                    "updated_at": _utc_now_iso(),
                }
                if promote_to_official:
                    update_payload["community_status"] = COMMUNITY_STATUS_OFFICIAL
                    update_payload["official_published_at"] = _utc_now_iso()
                await _update_paper(paper_id, update_payload)
                return

            if task.get("status") in TERMINAL_TASK_STATUSES:
                update_payload = {
                    "trans_status": "failed" if task.get("status") != "completed" else "completed",
                    "updated_at": _utc_now_iso(),
                }
                await _update_paper(paper_id, update_payload)
                return

        await asyncio.sleep(2)


def _paper_summary(
    paper: Dict[str, Any],
    *,
    latest_asset: Optional[Dict[str, Any]] = None,
    viewer_state: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    return {
        "id": paper.get("id"),
        "source": paper.get("source"),
        "arxiv_id": paper.get("arxiv_id"),
        "title": paper.get("title"),
        "authors": paper.get("authors") or [],
        "categories": paper.get("categories") or [],
        "community_status": paper.get("community_status"),
        "trans_status": paper.get("trans_status"),
        "created_at": paper.get("created_at"),
        "official_published_at": paper.get("official_published_at"),
        "community_selected_task_id": paper.get("community_selected_task_id"),
        "community_selected_asset_id": paper.get("community_selected_asset_id"),
        "visibility": paper.get("visibility"),
        "status": paper.get("status"),
        "like_count": paper.get("like_count"),
        "favorite_count": paper.get("favorite_count"),
        "comment_count": paper.get("comment_count"),
        "view_count": paper.get("view_count"),
        "download_count": paper.get("download_count"),
        "latest_asset": _serialize_latest_asset(latest_asset),
        "viewer_state": viewer_state,
    }


async def submit_uploaded_paper(
    *,
    file: UploadFile,
    credentials: Optional[HTTPAuthorizationCredentials],
    source_language: str = "en",
    target_language: str = "zh",
) -> Dict[str, Any]:
    context = await resolve_submitter_context(credentials)
    upload_response = await upload_route.upload_file(file=file, credentials=credentials)

    community_status = (
        COMMUNITY_STATUS_OFFICIAL if context["is_admin"] else COMMUNITY_STATUS_USER_FALLBACK
    )
    official_published_at = _utc_now_iso() if context["is_admin"] else None

    paper = await _insert_paper(
        _paper_payload(
            source="upload",
            arxiv_id=None,
            title=Path(file.filename or "upload").stem or "Uploaded paper",
            created_by=context["user_id"],
            community_status=community_status,
            task_id=upload_response.task_id,
            official_published_at=official_published_at,
        )
    )

    asset = await _create_source_asset(
        paper_id=paper["id"],
        task_id=upload_response.task_id,
        source_path=upload_response.source_path,
    )
    if asset:
        paper = await _update_paper(
            paper["id"],
            {
                "community_selected_asset_id": asset["id"],
                "updated_at": _utc_now_iso(),
            },
        )

    return {
        "paper": _paper_summary(paper, latest_asset=asset),
        "task": {
            "task_id": upload_response.task_id,
            "status": upload_response.status,
        },
        "admission_result": "created",
    }


async def submit_arxiv_paper(
    *,
    arxiv_id: str,
    credentials: Optional[HTTPAuthorizationCredentials],
    source_language: str = "en",
    target_language: str = "zh",
) -> Dict[str, Any]:
    del source_language, target_language

    context = await resolve_submitter_context(credentials)
    admission = await resolve_community_admission(
        submitter_context=context,
        source_type="arxiv",
        arxiv_id=arxiv_id,
    )
    existing = admission["existing_paper"]

    if existing and not context["is_admin"]:
        latest_asset = (
            await _fetch_latest_assets([existing["id"]])
        ).get(existing["id"])
        return {
            "paper": _paper_summary(existing, latest_asset=latest_asset),
            "task": {"task_id": None, "status": None},
            "admission_result": admission["admission_result"],
        }

    arxiv_response = await arxiv_route.download_arxiv(
        request=arxiv_route.ArxivRequest(arxiv_id=arxiv_id),
        credentials=credentials,
    )

    if existing:
        update_payload: Dict[str, Any] = {
            "community_status": COMMUNITY_STATUS_OFFICIAL,
            "trans_status": "queued",
            "trans_latest_task_id": arxiv_response.task_id,
            "community_selected_task_id": arxiv_response.task_id,
            "official_published_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        paper = await _update_paper(existing["id"], update_payload)
        admission_result = "created"
    else:
        paper = await _insert_paper(
            _paper_payload(
                source="arxiv",
                arxiv_id=arxiv_id,
                title=f"arXiv:{arxiv_id}",
                created_by=context["user_id"],
                community_status=admission["community_status"],
                task_id=arxiv_response.task_id,
                official_published_at=_utc_now_iso() if context["is_admin"] else None,
            )
        )
        admission_result = admission["admission_result"]

    asyncio.create_task(
        _watch_task_and_sync_asset(
            paper_id=paper["id"],
            task_id=arxiv_response.task_id,
            promote_to_official=context["is_admin"],
        )
    )

    return {
        "paper": _paper_summary(paper),
        "task": {
            "task_id": arxiv_response.task_id,
            "status": "processing",
        },
        "admission_result": admission_result,
    }


async def list_community_papers(
    *,
    sort: str = "latest",
    q: Optional[str] = None,
    viewer_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    del q

    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    result = await run_db_blocking(
        lambda: (
            admin_client.table("papers")
            .select(_paper_select_clause())
            .eq("visibility", "public")
            .neq("status", "removed")
            .execute()
        )
    )
    papers = result.data or []
    papers = _sort_papers(papers, sort)

    paper_ids = [paper["id"] for paper in papers]
    latest_assets = await _fetch_latest_assets(paper_ids)
    items = [
        _paper_summary(paper, latest_asset=latest_assets.get(paper["id"]))
        for paper in papers
    ]
    return {"items": items, "total": len(items)}


async def get_community_paper_detail(
    *,
    paper_id: str,
    viewer_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    paper = await _fetch_paper_by_id(paper_id)
    if paper is None or paper.get("visibility") != "public" or paper.get("status") == "removed":
        raise HTTPException(status_code=404, detail="Paper not found")

    latest_asset = (await _fetch_latest_assets([paper_id])).get(paper_id)
    viewer_state = (await _fetch_viewer_state([paper_id], user_id=viewer_user_id)).get(
        paper_id,
        {"liked": False, "favorited": False},
    )
    return {
        "paper": _paper_summary(paper, latest_asset=latest_asset, viewer_state=viewer_state),
    }


async def record_community_paper_view(*, paper_id: str) -> Dict[str, Any]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    result = await run_db_blocking(
        lambda: (
            admin_client.rpc(
                "increment_paper_view_count",
                {"target_paper_id": paper_id},
            ).execute()
        )
    )

    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Paper not found")

    return {"paper_id": paper_id, "view_count": rows[0].get("view_count", 0)}
