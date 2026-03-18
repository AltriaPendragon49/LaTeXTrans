from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import mimetypes
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.routes import arxiv as arxiv_route
from backend.app.api.routes import download as download_route
from backend.app.api.routes import translate as translate_route
from backend.app.api.routes import upload as upload_route
from backend.app.core.config import TaskStatus, get_settings
from backend.app.core.supabase_client import get_supabase_admin_client
from backend.app.services import paper_preview_service
from backend.app.services.task_manager import get_task_manager, get_task_queue
from backend.app.utils.async_blocking import run_db_blocking

logger = logging.getLogger(__name__)

task_manager = get_task_manager()
settings = get_settings()

COMMUNITY_STATUS_OFFICIAL = "official"
COMMUNITY_STATUS_USER_FALLBACK = "user_fallback"
TERMINAL_TASK_STATUSES = {
    "completed",
    "completed_with_warnings",
    "failed",
    "failed_compilation",
    "structure_invalid",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_storage_path(stored_path: Optional[str]) -> Path:
    if not stored_path:
        return Path("")

    candidate = Path(stored_path)
    if candidate.is_absolute():
        return candidate
    return settings.base_dir / candidate


def _store_relative_path(path: Path | str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return str(candidate).replace("\\", "/")

    try:
        relative = candidate.resolve().relative_to(settings.base_dir.resolve())
        return str(relative).replace("\\", "/")
    except Exception:
        return str(candidate).replace("\\", "/")


def _community_library_root(paper_id: str) -> Path:
    root = settings.community_papers_dir / paper_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def _community_asset_destination(
    *,
    paper_id: str,
    task_id: Optional[str],
    asset_type: str,
    source_name: str,
) -> Path:
    paper_root = _community_library_root(paper_id)
    safe_name = Path(source_name or asset_type).name or asset_type
    if asset_type == "source_archive":
        return paper_root / "source" / safe_name
    if asset_type == "translated_pdf":
        filename = f"{task_id or 'latest'}-{safe_name}" if task_id else safe_name
        return paper_root / "translated" / filename
    if asset_type == "preview_html":
        filename = f"{task_id or 'latest'}-{safe_name}" if task_id else safe_name
        return paper_root / "preview" / filename
    return paper_root / asset_type / safe_name


def _copy_into_community_library(source_path: Path, destination_path: Path) -> Path:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists():
        if destination_path.is_dir():
            shutil.rmtree(destination_path)
        else:
            destination_path.unlink()

    if source_path.is_dir():
        shutil.copytree(source_path, destination_path)
    else:
        shutil.copy2(source_path, destination_path)
    return destination_path


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


async def _fetch_paper_by_title(*, title: str, source: Optional[str] = None) -> Optional[Dict[str, Any]]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    def _query():
        query = (
            admin_client.table("papers")
            .select(_paper_select_clause())
            .eq("title", title)
            .neq("status", "removed")
            .limit(1)
        )
        if source:
            query = query.eq("source", source)
        return query.execute()

    result = await run_db_blocking(_query)
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


async def _fetch_asset_rows_for_paper(paper_id: str) -> List[Dict[str, Any]]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    result = await run_db_blocking(
        lambda: (
            admin_client.table("paper_assets")
            .select("id, paper_id, task_id, asset_type, file_path, file_name, mime_type, is_latest, created_at")
            .eq("paper_id", paper_id)
            .eq("is_latest", True)
            .execute()
        )
    )
    return result.data or []


async def _fetch_asset_map_for_paper(*, paper_id: str) -> Dict[str, Dict[str, Any]]:
    rows = await _fetch_asset_rows_for_paper(paper_id)
    asset_map: Dict[str, Dict[str, Any]] = {}
    for row in sorted(rows, key=lambda item: item.get("created_at") or "", reverse=True):
        asset_type = row.get("asset_type")
        if asset_type and asset_type not in asset_map:
            asset_map[str(asset_type)] = row
    return asset_map


async def _upsert_latest_asset(
    *,
    paper_id: str,
    task_id: Optional[str],
    asset_type: str,
    file_path: str,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> Dict[str, Any]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    resolved_name = file_name or Path(file_path).name
    resolved_mime = mime_type or mimetypes.guess_type(resolved_name)[0] or "application/octet-stream"

    await run_db_blocking(
        lambda: (
            admin_client.table("paper_assets")
            .update({"is_latest": False})
            .eq("paper_id", paper_id)
            .eq("asset_type", asset_type)
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
                    "asset_type": asset_type,
                    "storage_backend": "local_disk",
                    "file_path": file_path,
                    "file_name": resolved_name,
                    "mime_type": resolved_mime,
                    "is_latest": True,
                }
            )
            .execute()
        )
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=500, detail=f"Failed to create asset: {asset_type}")
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
    resolved_source = _resolve_storage_path(source_path)
    if not resolved_source.exists():
        return None
    destination = _community_asset_destination(
        paper_id=paper_id,
        task_id=task_id,
        asset_type="source_archive",
        source_name=resolved_source.name,
    )
    copied = _copy_into_community_library(resolved_source, destination)
    return await _upsert_latest_asset(
        paper_id=paper_id,
        task_id=task_id,
        asset_type="source_archive",
        file_path=_store_relative_path(copied),
        file_name=copied.name,
    )


def _serialize_latest_asset(asset: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not asset:
        return None
    return {
        "id": asset.get("id"),
        "task_id": asset.get("task_id"),
        "asset_type": asset.get("asset_type"),
        "file_name": asset.get("file_name"),
        "mime_type": asset.get("mime_type"),
        "created_at": asset.get("created_at"),
    }


def _serialize_public_asset(asset: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return _serialize_latest_asset(asset)


def _select_latest_asset_from_map(asset_map: Optional[Dict[str, Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    if not asset_map:
        return None
    for preferred_type in ("preview_html", "translated_pdf", "preview_pdf", "source_archive"):
        asset = asset_map.get(preferred_type)
        if asset:
            return asset
    return None


def _public_asset_map(asset_map: Optional[Dict[str, Dict[str, Any]]]) -> Optional[Dict[str, Dict[str, Any]]]:
    if not asset_map:
        return None
    return {
        asset_type: serialized
        for asset_type, asset in asset_map.items()
        if (serialized := _serialize_public_asset(asset)) is not None
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


def _download_token_secret() -> str:
    return (
        settings.community_download_token_secret
        or settings.encryption_key
        or settings.llm_api_key
    )


def _sign_download_token(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_token = base64.urlsafe_b64encode(serialized).decode("utf-8").rstrip("=")
    signature = hmac.new(
        _download_token_secret().encode("utf-8"),
        serialized,
        hashlib.sha256,
    ).digest()
    signature_token = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{payload_token}.{signature_token}"


def _decode_download_token(token: str) -> Dict[str, Any]:
    try:
        payload_token, signature_token = token.split(".", 1)
        payload_bytes = base64.urlsafe_b64decode(payload_token + "=" * (-len(payload_token) % 4))
        expected_signature = hmac.new(
            _download_token_secret().encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).digest()
        provided_signature = base64.urlsafe_b64decode(
            signature_token + "=" * (-len(signature_token) % 4)
        )
    except Exception as exc:
        raise HTTPException(status_code=403, detail=f"Invalid download token: {exc}") from exc

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise HTTPException(status_code=403, detail="Invalid download token signature")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=403, detail=f"Invalid download token payload: {exc}") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=403, detail="Invalid download token payload")

    expires_at = int(payload.get("exp") or 0)
    if expires_at <= int(time.time()):
        raise HTTPException(status_code=410, detail="Download token expired")
    return payload


async def _increment_paper_download_count(paper_id: str) -> Dict[str, Any]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    result = await run_db_blocking(
        lambda: (
            admin_client.rpc(
                "increment_paper_download_count",
                {"target_paper_id": paper_id},
            ).execute()
        )
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"paper_id": paper_id, "download_count": rows[0].get("download_count")}


async def _resolve_translated_pdf_asset(
    *,
    paper_id: str,
    task_id: str,
) -> Optional[Dict[str, Any]]:
    task = task_manager.get_task(task_id)
    if not task:
        return None

    output_dir = _resolve_storage_path(task.get("output_path") or "")
    if not output_dir.exists():
        return None

    pdf_path = download_route._find_translated_pdf(output_dir)
    if not pdf_path or not pdf_path.exists():
        return None
    destination = _community_asset_destination(
        paper_id=paper_id,
        task_id=task_id,
        asset_type="translated_pdf",
        source_name=pdf_path.name,
    )
    copied = _copy_into_community_library(pdf_path, destination)

    asset = await _upsert_latest_asset(
        paper_id=paper_id,
        task_id=task_id,
        asset_type="translated_pdf",
        file_path=_store_relative_path(copied),
        file_name=copied.name,
        mime_type="application/pdf",
    )
    await _update_paper(
        paper_id,
        {
            "trans_latest_asset_pdf_id": asset.get("id"),
            "updated_at": _utc_now_iso(),
        },
    )
    return asset


async def _resolve_preview_html_asset(
    *,
    paper_id: str,
    task_id: str,
) -> Optional[Dict[str, Any]]:
    task = task_manager.get_task(task_id)
    if not task:
        return None

    output_dir = _resolve_storage_path(task.get("output_path") or "")
    if not output_dir.exists():
        return None

    try:
        preview_asset = paper_preview_service.generate_preview_html(
            output_dir,
            target_dir=_community_library_root(paper_id) / "preview",
        )
    except FileNotFoundError:
        return None

    return await _upsert_latest_asset(
        paper_id=paper_id,
        task_id=task_id,
        asset_type="preview_html",
        file_path=_store_relative_path(preview_asset["file_path"]),
        file_name=preview_asset["file_name"],
        mime_type=preview_asset["mime_type"],
    )


async def _enqueue_existing_task_translation(
    *,
    task_id: str,
    request: translate_route.TranslateRequest,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Dict[str, Any]:
    response = await translate_route.start_translation(
        task_id=task_id,
        request=request,
        credentials=credentials,
    )
    return {"task_id": response.task_id, "status": response.status}


async def _start_arxiv_paper_translation(
    *,
    paper: Dict[str, Any],
    request: translate_route.TranslateRequest,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    arxiv_id = paper.get("arxiv_id")
    if not arxiv_id:
        raise HTTPException(status_code=422, detail="Paper source is unavailable for translation")

    task_id = task_manager.create_task(
        source_type="arxiv",
        arxiv_id=arxiv_id,
        user_id=context["user_id"],
        source_language=request.source_language,
        target_language=request.target_language,
        persist_to_db=False,
    )
    config_hash = translate_route.compute_config_hash(
        arxiv_id=arxiv_id,
        source_language=request.source_language,
        target_language=request.target_language,
        translation_mode=request.advanced_config.translation_mode,
        compile_strategy=request.advanced_config.compile_strategy,
        formatting=request.advanced_config.formatting,
    )
    task_manager.update_task(
        task_id=task_id,
        source_language=request.source_language,
        target_language=request.target_language,
        advanced_config=request.advanced_config.model_dump(),
        config_hash=config_hash,
        user_id=context["user_id"],
    )
    task_manager.persist_task_if_needed(task_id)

    llm_config = await translate_route.build_llm_config_async(request.advanced_config, context["user_id"])
    token_hash = hashlib.md5((llm_config.get("api_key") or "").encode()).hexdigest()
    asyncio.create_task(
        translate_route._download_and_enqueue(
            task_id=task_id,
            arxiv_id=arxiv_id,
            user_id=context["user_id"],
            source_language=request.source_language,
            target_language=request.target_language,
            advanced_config=request.advanced_config,
            tq=get_task_queue(),
            token_hash=token_hash,
        )
    )
    return {"task_id": task_id, "status": "queued"}


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


def _task_source_for_community(task: Dict[str, Any]) -> str:
    return "arxiv" if task.get("arxiv_id") or task.get("source_type") == "arxiv" else "upload"


def _derive_task_title(task: Dict[str, Any]) -> str:
    arxiv_id = task.get("arxiv_id")
    if arxiv_id:
        return f"arXiv:{arxiv_id}"

    output_dir = _resolve_storage_path(task.get("output_path"))
    if output_dir.exists():
        pdf_path = download_route._find_translated_pdf(output_dir)
        if pdf_path and pdf_path.exists():
            return pdf_path.stem

    source_path = _resolve_storage_path(task.get("source_path"))
    if source_path.name:
        return source_path.stem if source_path.is_file() else source_path.name
    return "Uploaded paper"


async def _find_publish_target_for_task(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    arxiv_id = task.get("arxiv_id")
    if arxiv_id:
        return await _fetch_paper_by_arxiv_id(str(arxiv_id))
    return await _fetch_paper_by_title(
        title=_derive_task_title(task),
        source=_task_source_for_community(task),
    )


async def _sync_task_assets_for_paper(
    *,
    paper_id: str,
    task_id: str,
    promote_to_official: bool,
) -> Dict[str, Any]:
    task = task_manager.get_task(task_id)
    if not task:
        return {"done": False, "status": None}

    source_asset_id: Optional[str] = None
    if task.get("source_available") and task.get("source_path"):
        asset = await _create_source_asset(
            paper_id=paper_id,
            task_id=task_id,
            source_path=task.get("source_path"),
        )
        update_payload: Dict[str, Any] = {
            "trans_status": "processing" if task.get("status") == "processing" else "queued",
            "community_selected_task_id": task_id,
            "updated_at": _utc_now_iso(),
        }
        if asset:
            source_asset_id = asset.get("id")
            update_payload["community_selected_asset_id"] = source_asset_id
        if promote_to_official:
            update_payload["community_status"] = COMMUNITY_STATUS_OFFICIAL
            update_payload["official_published_at"] = _utc_now_iso()
        await _update_paper(paper_id, update_payload)

    if task.get("status") in {"completed", "completed_with_warnings"}:
        translated_asset = await _resolve_translated_pdf_asset(
            paper_id=paper_id,
            task_id=task_id,
        )
        preview_asset = await _resolve_preview_html_asset(
            paper_id=paper_id,
            task_id=task_id,
        )
        selected_asset = preview_asset or translated_asset
        update_payload = {
            "trans_status": "completed",
            "community_selected_task_id": task_id,
            "community_selected_asset_id": (
                selected_asset.get("id") if selected_asset else source_asset_id
            ),
            "updated_at": _utc_now_iso(),
        }
        if promote_to_official:
            update_payload["community_status"] = COMMUNITY_STATUS_OFFICIAL
            update_payload["official_published_at"] = _utc_now_iso()
        paper = await _update_paper(paper_id, update_payload)
        return {"done": True, "status": "completed", "paper": paper}

    if task.get("status") in TERMINAL_TASK_STATUSES:
        paper = await _update_paper(
            paper_id,
            {
                "trans_status": "failed",
                "community_selected_task_id": task_id,
                "updated_at": _utc_now_iso(),
            },
        )
        return {"done": True, "status": "failed", "paper": paper}

    return {"done": False, "status": task.get("status")}


async def ensure_task_published_to_community_library(
    *,
    task_id: str,
    promote_to_official: bool = False,
) -> Optional[Dict[str, Any]]:
    task = task_manager.get_task(task_id)
    if not task or not task.get("user_id"):
        return None

    if task.get("status") not in {"completed", "completed_with_warnings"}:
        return None

    existing = await _find_publish_target_for_task(task)
    if (
        existing
        and existing.get("community_status") == COMMUNITY_STATUS_OFFICIAL
        and existing.get("trans_status") == "completed"
        and not promote_to_official
    ):
        return {"paper": existing, "published": False}

    if existing:
        paper = await _update_paper(
            existing["id"],
            {
                "trans_status": "processing",
                "trans_latest_task_id": task_id,
                "community_selected_task_id": task_id,
                "updated_at": _utc_now_iso(),
                **(
                    {
                        "community_status": COMMUNITY_STATUS_OFFICIAL,
                        "official_published_at": _utc_now_iso(),
                    }
                    if promote_to_official
                    else {}
                ),
            },
        )
    else:
        paper = await _insert_paper(
            _paper_payload(
                source=_task_source_for_community(task),
                arxiv_id=task.get("arxiv_id"),
                title=_derive_task_title(task),
                created_by=task["user_id"],
                community_status=(
                    COMMUNITY_STATUS_OFFICIAL if promote_to_official else COMMUNITY_STATUS_USER_FALLBACK
                ),
                task_id=task_id,
                official_published_at=_utc_now_iso() if promote_to_official else None,
            )
        )

    sync_result = await _sync_task_assets_for_paper(
        paper_id=paper["id"],
        task_id=task_id,
        promote_to_official=promote_to_official,
    )
    return {"paper": sync_result.get("paper") or paper, "published": True}


async def watch_task_and_publish_community_library(
    *,
    task_id: str,
    promote_to_official: bool = False,
) -> None:
    for _ in range(180):
        task = task_manager.get_task(task_id)
        if task:
            if task.get("status") in {"completed", "completed_with_warnings"}:
                await ensure_task_published_to_community_library(
                    task_id=task_id,
                    promote_to_official=promote_to_official,
                )
                return
            if task.get("status") in TERMINAL_TASK_STATUSES:
                return
        await asyncio.sleep(2)


async def _watch_task_and_sync_asset(
    *,
    paper_id: str,
    task_id: str,
    promote_to_official: bool,
) -> None:
    for _ in range(180):
        result = await _sync_task_assets_for_paper(
            paper_id=paper_id,
            task_id=task_id,
            promote_to_official=promote_to_official,
        )
        if result.get("done"):
            return
        await asyncio.sleep(2)


def _paper_summary(
    paper: Dict[str, Any],
    *,
    latest_asset: Optional[Dict[str, Any]] = None,
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
    viewer_state: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    selected_latest_asset = latest_asset or _select_latest_asset_from_map(asset_map)
    return {
        "id": paper.get("id"),
        "source": paper.get("source"),
        "arxiv_id": paper.get("arxiv_id"),
        "title": paper.get("title"),
        "authors": paper.get("authors") or [],
        "categories": paper.get("categories") or [],
        "abstract_raw": paper.get("abstract_raw"),
        "abstract_translated": paper.get("abstract_translated"),
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
        "latest_asset": _serialize_latest_asset(selected_latest_asset),
        "assets": _public_asset_map(asset_map),
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


async def _ensure_public_paper(paper_id: str) -> Dict[str, Any]:
    paper = await _fetch_paper_by_id(paper_id)
    if paper is None or paper.get("visibility") != "public" or paper.get("status") == "removed":
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


async def start_paper_translation(
    *,
    paper_id: str,
    request: translate_route.TranslateRequest,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Dict[str, Any]:
    context = await resolve_submitter_context(credentials)
    paper = await _ensure_public_paper(paper_id)

    active_task_id = paper.get("community_selected_task_id")
    if active_task_id and paper.get("trans_status") in {"queued", "processing"}:
        return {
            "paper_id": paper_id,
            "task_id": active_task_id,
            "status": paper.get("trans_status"),
            "reused_existing_task": True,
            "processing_url": f"/processing?taskId={active_task_id}",
        }

    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    source_asset = asset_map.get("source_archive")
    if source_asset and source_asset.get("file_path"):
        resolved_source_path = _resolve_storage_path(source_asset["file_path"])
        task_id = task_manager.create_task(
            source_type=paper.get("source") or "upload",
            arxiv_id=paper.get("arxiv_id"),
            user_id=context["user_id"],
            source_language=request.source_language,
            target_language=request.target_language,
            persist_to_db=False,
        )
        task_manager.update_task(
            task_id=task_id,
            source_path=str(resolved_source_path).replace("\\", "/"),
            source_available=True,
            arxiv_id=paper.get("arxiv_id"),
            source_language=request.source_language,
            target_language=request.target_language,
            advanced_config=request.advanced_config.model_dump(),
            user_id=context["user_id"],
        )
        task_manager.persist_task_if_needed(task_id)
        translation_result = await _enqueue_existing_task_translation(
            task_id=task_id,
            request=request,
            credentials=credentials,
        )
    elif paper.get("source") == "arxiv" and paper.get("arxiv_id"):
        translation_result = await _start_arxiv_paper_translation(
            paper=paper,
            request=request,
            context=context,
        )
        task_id = translation_result["task_id"]
    else:
        raise HTTPException(status_code=422, detail="Paper source is unavailable for translation")

    await _update_paper(
        paper_id,
        {
            "trans_status": translation_result["status"],
            "trans_latest_task_id": translation_result["task_id"],
            "community_selected_task_id": translation_result["task_id"],
            "updated_at": _utc_now_iso(),
        },
    )
    asyncio.create_task(
        _watch_task_and_sync_asset(
            paper_id=paper_id,
            task_id=translation_result["task_id"],
            promote_to_official=context["is_admin"],
        )
    )
    return {
        "paper_id": paper_id,
        "task_id": translation_result["task_id"],
        "status": translation_result["status"],
        "reused_existing_task": False,
        "processing_url": f"/processing?taskId={translation_result['task_id']}",
    }


async def get_paper_preview(*, paper_id: str) -> Dict[str, Any]:
    paper = await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    preview_asset = asset_map.get("preview_html")
    if not preview_asset:
        raise HTTPException(status_code=404, detail="Preview not available")

    preview_path = _resolve_storage_path(preview_asset.get("file_path") or "")
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview file not found")

    html_content = preview_path.read_text(encoding="utf-8")
    html_content = html_content.replace("<script", "&lt;script")
    return {
        "paper_id": paper_id,
        "task_id": preview_asset.get("task_id") or paper.get("community_selected_task_id"),
        "asset": _serialize_public_asset(preview_asset),
        "html_content": html_content,
        "generated_at": preview_asset.get("created_at"),
    }


async def create_paper_download_session(*, paper_id: str) -> Dict[str, Any]:
    await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    translated_asset = asset_map.get("translated_pdf")
    if not translated_asset:
        raise HTTPException(status_code=404, detail="Translated PDF not available")

    expires_at = int(time.time()) + 300
    token = _sign_download_token(
        {
            "v": 1,
            "paper_id": paper_id,
            "asset_id": translated_asset.get("id"),
            "exp": expires_at,
        }
    )
    return {
        "paper_id": paper_id,
        "asset_id": translated_asset.get("id"),
        "download_url": f"/api/papers/{paper_id}/download?token={token}",
        "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
    }


async def resolve_paper_download(*, paper_id: str, token: str) -> Dict[str, Any]:
    payload = _decode_download_token(token)
    if payload.get("paper_id") != paper_id:
        raise HTTPException(status_code=403, detail="Download token does not match paper")

    await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    translated_asset = asset_map.get("translated_pdf")
    if not translated_asset:
        raise HTTPException(status_code=404, detail="Translated PDF not available")
    if payload.get("asset_id") != translated_asset.get("id"):
        raise HTTPException(status_code=403, detail="Download token does not match asset")

    file_path = _resolve_storage_path(translated_asset.get("file_path") or "")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Translated PDF file not found")

    await _increment_paper_download_count(paper_id)
    return {
        "paper_id": paper_id,
        "asset": translated_asset,
        "file_path": str(file_path),
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

    asset_map: Optional[Dict[str, Dict[str, Any]]] = None
    latest_asset: Optional[Dict[str, Any]] = None
    try:
        asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
        latest_asset = _select_latest_asset_from_map(asset_map)
    except HTTPException:
        latest_asset = (await _fetch_latest_assets([paper_id])).get(paper_id)
    viewer_state = (await _fetch_viewer_state([paper_id], user_id=viewer_user_id)).get(
        paper_id,
        {"liked": False, "favorited": False},
    )
    return {
        "paper": _paper_summary(
            paper,
            latest_asset=latest_asset,
            asset_map=asset_map,
            viewer_state=viewer_state,
        ),
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
