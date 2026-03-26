from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import mimetypes
import re
import shutil
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from fastapi import HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.routes import arxiv as arxiv_route
from backend.app.api.routes import download as download_route
from backend.app.api.routes import translate as translate_route
from backend.app.api.routes import upload as upload_route
from backend.app.core.config import TaskStatus, get_settings
from backend.app.core.supabase_client import get_supabase_admin_client
from backend.app.services.latex.utils import extract_abstract, extract_text_from_tex
from backend.app.services.latex_validator import find_main_tex_file
from backend.app.services import paper_preview_service
from backend.app.services.task_manager import get_task_manager, get_task_queue
from backend.app.utils.async_blocking import run_db_blocking

logger = logging.getLogger(__name__)

task_manager = get_task_manager()
settings = get_settings()

COMMUNITY_STATUS_OFFICIAL = "official"
COMMUNITY_STATUS_USER_FALLBACK = "user_fallback"
_RUNTIME_PAPER_OVERRIDES: Dict[str, Dict[str, Any]] = {}
TERMINAL_TASK_STATUSES = {
    "completed",
    "completed_with_warnings",
    "failed",
    "failed_compilation",
    "structure_invalid",
}
_preview_recovery_inflight: set[str] = set()
_detail_repair_inflight: set[str] = set()
_preview_payload_cache: Dict[str, Dict[str, Any]] = {}
_source_html_cache: Dict[str, str] = {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _run_db_blocking_with_retry(
    operation_name: str,
    operation,
    *,
    retries: int = 1,
) -> Any:
    for attempt in range(retries + 1):
        try:
            return await run_db_blocking(operation)
        except httpx.RemoteProtocolError:
            if attempt >= retries:
                raise
            logger.warning(
                "Transient Supabase disconnect during %s; retrying (%s/%s)",
                operation_name,
                attempt + 1,
                retries + 1,
            )
            await asyncio.sleep(0.2)


def _normalize_metadata_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = " ".join(str(value).split()).strip()
    return normalized or None


def _count_cjk_characters(value: Optional[str]) -> int:
    text = _normalize_metadata_text(value) or ""
    return len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", text))


def _looks_untranslated_for_zh(value: Optional[str]) -> bool:
    text = _normalize_metadata_text(value) or ""
    if not text:
        return True
    cjk_count = _count_cjk_characters(text)
    letter_count = len(re.findall(r"[A-Za-z]", text))
    if cjk_count >= 8:
        return False
    if cjk_count > 0 and letter_count == 0:
        return False
    if cjk_count > 0 and (cjk_count / max(letter_count, 1)) >= 0.08:
        return False
    return letter_count >= 20


def _preview_html_looks_untranslated_for_zh(html_content: Optional[str]) -> bool:
    if not html_content:
        return True

    try:
        text = BeautifulSoup(html_content, "html.parser").get_text(" ", strip=True)
    except Exception:
        text = html_content

    return _looks_untranslated_for_zh(text)


def _preview_asset_has_translated_content(preview_asset: Optional[Dict[str, Any]]) -> bool:
    if not preview_asset:
        return False

    preview_path = _resolve_storage_path(preview_asset.get("file_path") or "")
    if not preview_path.exists():
        return False

    try:
        html_content = preview_path.read_text(encoding="utf-8")
    except Exception:
        return False

    if _preview_html_needs_refresh(html_content):
        return False

    return not _preview_html_looks_untranslated_for_zh(html_content)


def _should_replace_translated_abstract(
    current_value: Optional[str],
    candidate_value: Optional[str],
    raw_abstract: Optional[str],
) -> bool:
    current = _normalize_metadata_text(current_value)
    candidate = _normalize_metadata_text(candidate_value)
    raw = _normalize_metadata_text(raw_abstract)
    if not candidate:
        return False
    if not current:
        return True
    if current == candidate:
        return False
    if raw and current == raw:
        return True
    if _looks_untranslated_for_zh(current) and _count_cjk_characters(candidate) > 0:
        return True
    return False


def _fetch_arxiv_metadata_sync(arxiv_id: str) -> Dict[str, Any]:
    response = requests.get(
        "https://export.arxiv.org/api/query",
        params={"id_list": arxiv_id},
        headers={"User-Agent": "LaTexTrans/CommunityWeek1Fix"},
        timeout=15,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", namespace)
    if entry is None:
        return {}

    title = _normalize_metadata_text(entry.findtext("atom:title", default="", namespaces=namespace))
    abstract_raw = _normalize_metadata_text(entry.findtext("atom:summary", default="", namespaces=namespace))
    authors = [
        _normalize_metadata_text(author.findtext("atom:name", default="", namespaces=namespace))
        for author in entry.findall("atom:author", namespace)
    ]
    categories = []
    for category in entry.findall("atom:category", namespace):
        term = _normalize_metadata_text(category.attrib.get("term"))
        if term and term not in categories:
            categories.append(term)

    return {
        "title": title,
        "authors": [author for author in authors if author],
        "categories": categories,
        "abstract_raw": abstract_raw,
    }


async def _fetch_arxiv_metadata(arxiv_id: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_fetch_arxiv_metadata_sync, arxiv_id)
    except Exception as exc:
        logger.warning("Failed to fetch arXiv metadata for %s: %s", arxiv_id, exc)
        return {}


def _needs_arxiv_metadata_hydration(paper: Dict[str, Any]) -> bool:
    if paper.get("source") != "arxiv" or not paper.get("arxiv_id"):
        return False
    title = str(paper.get("title") or "").strip()
    return (
        not title
        or title.startswith("arXiv:")
        or not (paper.get("authors") or [])
        or not (paper.get("categories") or [])
        or not (paper.get("abstract_raw") or "").strip()
    )


def _best_available_metadata_payload(paper: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    title = _normalize_metadata_text(str(paper.get("title") or ""))
    metadata_title = _normalize_metadata_text(metadata.get("title"))
    if metadata_title and (not title or title.startswith("arXiv:")):
        payload["title"] = metadata_title
    if metadata.get("authors") and not (paper.get("authors") or []):
        payload["authors"] = metadata["authors"]
    if metadata.get("categories") and not (paper.get("categories") or []):
        payload["categories"] = metadata["categories"]
    if metadata.get("abstract_raw") and not _normalize_metadata_text(paper.get("abstract_raw")):
        payload["abstract_raw"] = metadata["abstract_raw"]
    return payload


def _extract_plaintext_abstract_from_directory(directory: Path) -> Optional[str]:
    if not directory.exists():
        return None

    main_tex = find_main_tex_file(directory)
    if main_tex and Path(main_tex).exists():
        try:
            latex = Path(main_tex).read_text(encoding="utf-8")
            abstract = extract_abstract(latex)
            if abstract not in {"No abstract", "No title", ""}:
                plain_text = _normalize_metadata_text(extract_text_from_tex(abstract))
                if plain_text:
                    return plain_text
        except Exception:
            pass

    envs_map_path = directory / "envs_map.json"
    if envs_map_path.exists():
        try:
            env_rows = json.loads(envs_map_path.read_text(encoding="utf-8"))
        except Exception:
            env_rows = []
        if isinstance(env_rows, list):
            for row in env_rows:
                if str(row.get("env_name") or "").strip() != "abstract":
                    continue
                content = row.get("trans_content") or row.get("content") or ""
                plain_text = _normalize_metadata_text(extract_text_from_tex(str(content)))
                if plain_text:
                    return plain_text

    return None


def _candidate_output_directories_for_task(task_id: str) -> List[Path]:
    candidates: List[Path] = []
    seen: set[str] = set()

    def _add_directory(path: Optional[Path]) -> None:
        if path is None:
            return
        try:
            normalized = str(path.resolve())
        except Exception:
            normalized = str(path)
        if normalized in seen:
            return
        seen.add(normalized)
        if path.exists() and path.is_dir():
            candidates.append(path)

    task = task_manager.get_task(task_id) if task_id else None
    if task:
        stored_output = _resolve_storage_path(task.get("output_path") or "")
        _add_directory(stored_output)

    task_root = Path(settings.outputs_dir) / task_id
    _add_directory(task_root)
    if task_root.exists() and task_root.is_dir():
        for child in sorted(task_root.iterdir()):
            if child.is_dir():
                _add_directory(child)

    return candidates


def _extract_translated_abstract_from_task(task_id: str) -> Optional[str]:
    for output_dir in _candidate_output_directories_for_task(task_id):
        abstract = _extract_plaintext_abstract_from_directory(output_dir)
        if abstract:
            return abstract
    return None


async def _hydrate_arxiv_metadata_if_needed(paper: Dict[str, Any]) -> Dict[str, Any]:
    if not _needs_arxiv_metadata_hydration(paper):
        return paper

    metadata = await _fetch_arxiv_metadata(str(paper.get("arxiv_id")))
    payload = _best_available_metadata_payload(paper, metadata)
    if not payload:
        return paper

    payload["updated_at"] = _utc_now_iso()
    return await _update_paper(str(paper["id"]), payload)


async def _hydrate_translated_abstract_if_needed(
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    current_abstract = _normalize_metadata_text(paper.get("abstract_translated"))
    if current_abstract and not _looks_untranslated_for_zh(current_abstract):
        return paper

    for task_id in _candidate_task_ids_for_asset_recovery(paper, asset_map):
        abstract_translated = _extract_translated_abstract_from_task(task_id)
        if _should_replace_translated_abstract(
            current_abstract,
            abstract_translated,
            paper.get("abstract_raw"),
        ):
            return await _update_paper(
                str(paper["id"]),
                {
                    "abstract_translated": abstract_translated,
                    "updated_at": _utc_now_iso(),
                },
            )

    return paper


async def _repair_public_detail_in_background(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]],
) -> None:
    if paper_id in _detail_repair_inflight:
        return

    _detail_repair_inflight.add(paper_id)
    try:
        repaired = await _hydrate_arxiv_metadata_if_needed(paper)
        await _hydrate_translated_abstract_if_needed(repaired, asset_map=asset_map)
    except Exception as exc:
        logger.warning("Failed to repair public detail for paper %s: %s", paper_id, exc)
    finally:
        _detail_repair_inflight.discard(paper_id)


def _schedule_public_detail_repair(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]],
) -> bool:
    needs_metadata = _needs_arxiv_metadata_hydration(paper)
    current_abstract = _normalize_metadata_text(paper.get("abstract_translated"))
    needs_translated_abstract = not current_abstract or _looks_untranslated_for_zh(current_abstract)

    if paper_id in _detail_repair_inflight:
        return False

    if not needs_metadata and not needs_translated_abstract:
        return False

    asyncio.create_task(
        _repair_public_detail_in_background(
            paper_id=paper_id,
            paper=paper,
            asset_map=asset_map,
        )
    )
    return True


def _resolve_storage_path(stored_path: Optional[str]) -> Path:
    if not stored_path:
        return Path("")

    candidate = Path(stored_path)
    if candidate.is_absolute():
        return candidate
    return settings.base_dir / candidate


def _normalize_search_text(value: Optional[str]) -> str:
    return " ".join(str(value or "").split()).strip().lower()


def _matches_paper_query(paper: Dict[str, Any], query: Optional[str]) -> bool:
    normalized_query = _normalize_search_text(query)
    if not normalized_query:
        return True

    searchable_parts = [
        paper.get("title"),
        paper.get("arxiv_id"),
        paper.get("abstract_raw"),
        paper.get("abstract_translated"),
        " ".join(str(category) for category in (paper.get("categories") or [])),
        " ".join(
            str(author.get("name") if isinstance(author, dict) else author)
            for author in (paper.get("authors") or [])
        ),
    ]
    haystack = _normalize_search_text(" ".join(part for part in searchable_parts if part))
    return normalized_query in haystack


def _load_baseline_seed_rows() -> List[Dict[str, Any]]:
    baseline_path = getattr(settings, "community_baseline_seed_path", None)
    if not baseline_path:
        return []

    path = Path(baseline_path)
    if not path.exists():
        logger.warning("Community baseline seed file is configured but missing: %s", path)
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to parse community baseline seed file %s: %s", path, exc)
        return []

    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []

    normalized_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized = dict(row)
        normalized.setdefault("visibility", "public")
        normalized.setdefault("status", "published")
        normalized_rows.append(normalized)
    return normalized_rows


def _apply_runtime_paper_override(paper: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if paper is None:
        return None
    paper_id = str(paper.get("id") or "").strip()
    override = _RUNTIME_PAPER_OVERRIDES.get(paper_id)
    if not override:
        return paper
    merged = dict(paper)
    merged.update(override)
    return merged


def _preview_asset_needs_refresh(preview_path: Path) -> bool:
    if not preview_path.exists():
        return True

    try:
        html_content = preview_path.read_text(encoding="utf-8")
    except Exception:
        return True

    return _preview_html_needs_refresh(html_content)


def _preview_html_needs_refresh(html_content: str) -> bool:
    stale_markers = (
        'data-reader-version="reader-v1"',
        'data-reader-version="reader-v2"',
        'data-reader-version="reader-v3"',
        'data-reader-version="reader-v4"',
        'data-reader-version="reader-v5"',
        'data-reader-version="reader-v6"',
        'data-reader-version="reader-v7"',
        'data-reader-version="reader-v8"',
        'data-reader-version="day4"',
        "\\begin{document}",
        "\\clearpage",
        "\\begin{figure",
        "\\begin{algorithm",
        "\\paragraph{",
        "\\PARR{",
        "\\KwData",
        "\\SetAlgoLined",
        "\\For{",
        "\\multirow{",
        "\\resizebox{",
        "\\hdashline",
        "\\textsubscript{",
        "[1.1pt]",
        "LNCE=",
        "<PLACEHOLDER_",
        "<PROTECTED_",
    )
    if any(marker in html_content for marker in stale_markers):
        return True

    current_marker = f'data-reader-version="{paper_preview_service.PREVIEW_READER_VERSION}"'
    if current_marker in html_content:
        return False

    version_match = re.search(r'data-reader-version="([^"]+)"', html_content)
    if version_match:
        return version_match.group(1) != paper_preview_service.PREVIEW_READER_VERSION

    return False


def _preview_payload_cache_key(
    preview_path: Path,
    preview_asset: Dict[str, Any],
) -> Optional[str]:
    if not preview_path.exists():
        return None

    try:
        stat_result = preview_path.stat()
    except OSError:
        return None

    resolved_path = preview_path.resolve() if hasattr(preview_path, "resolve") else preview_path
    st_mtime_ns = getattr(stat_result, "st_mtime_ns", None)
    if st_mtime_ns is None:
        st_mtime = getattr(stat_result, "st_mtime", None)
        st_mtime_ns = int(float(st_mtime) * 1_000_000_000) if st_mtime is not None else 0
    st_size = getattr(stat_result, "st_size", 0)

    return "|".join(
        [
            str(resolved_path),
            str(preview_asset.get("id") or ""),
            str(preview_asset.get("created_at") or ""),
            str(st_mtime_ns),
            str(st_size),
        ]
    )


def _load_preview_payload(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    preview_asset: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    preview_path = _resolve_storage_path(preview_asset.get("file_path") or "")
    if not preview_path.exists():
        return None

    cache_key = _preview_payload_cache_key(preview_path, preview_asset)
    if cache_key:
        cached_payload = _preview_payload_cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload

    try:
        html_content = preview_path.read_text(encoding="utf-8")
    except Exception:
        return None

    if _preview_html_needs_refresh(html_content):
        return None
    if _preview_html_looks_untranslated_for_zh(html_content):
        return None

    payload = {
        "paper_id": paper_id,
        "task_id": preview_asset.get("task_id") or paper.get("community_selected_task_id"),
        "asset": _serialize_public_asset(preview_asset),
        "html_content": html_content.replace("<script", "&lt;script"),
        "generated_at": preview_asset.get("created_at"),
    }
    if cache_key:
        _preview_payload_cache[cache_key] = payload
    return payload


def _build_preview_payload(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    preview_asset: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    return _load_preview_payload(
        paper_id=paper_id,
        paper=paper,
        preview_asset=preview_asset,
    )


async def _recover_preview_asset_in_background(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]],
) -> None:
    if paper_id in _preview_recovery_inflight:
        return

    _preview_recovery_inflight.add(paper_id)
    try:
        current_asset_map = asset_map or {}
        for task_id in _candidate_task_ids_for_asset_recovery(paper, current_asset_map):
            preview_asset = await _resolve_preview_html_asset(
                paper=paper,
                paper_id=paper_id,
                task_id=task_id,
                asset_map=current_asset_map,
            )
            if preview_asset:
                return
    except Exception as exc:
        logger.warning("Failed to recover preview asset for paper %s: %s", paper_id, exc)
    finally:
        _preview_recovery_inflight.discard(paper_id)


def _schedule_preview_recovery(
    *,
    paper_id: str,
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]],
) -> bool:
    if paper_id in _preview_recovery_inflight:
        return False

    if paper.get("trans_status") not in {"completed", "completed_with_warnings"}:
        return False

    if not _candidate_task_ids_for_asset_recovery(paper, asset_map):
        return False

    asyncio.create_task(
        _recover_preview_asset_in_background(
            paper_id=paper_id,
            paper=paper,
            asset_map=asset_map,
        )
    )
    return True


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
    try:
        if source_path.resolve() == destination_path.resolve():
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            return destination_path
    except FileNotFoundError:
        pass

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

    return await resolve_submitter_context_by_user_id(str(user_id))


async def resolve_submitter_context_by_user_id(user_id: str) -> Dict[str, Any]:
    normalized_user_id = str(user_id or "").strip()
    if not normalized_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase admin client unavailable",
        )

    result = await _run_db_blocking_with_retry(
        "resolve_submitter_context",
        lambda: (
            admin_client.table("user_roles")
            .select("role")
            .eq("user_id", normalized_user_id)
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
        "user_id": normalized_user_id,
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
        return _apply_runtime_paper_override(
            next(
                (row for row in _load_baseline_seed_rows() if str(row.get("id") or "") == paper_id),
                None,
            )
        )

    result = await _run_db_blocking_with_retry(
        "fetch_paper_by_id",
        lambda: (
            admin_client.table("papers")
            .select(_paper_select_clause())
            .eq("id", paper_id)
            .limit(1)
            .execute()
        )
    )
    rows = result.data or []
    if rows:
        return _apply_runtime_paper_override(rows[0])
    return _apply_runtime_paper_override(
        next(
            (row for row in _load_baseline_seed_rows() if str(row.get("id") or "") == paper_id),
            None,
        )
    )


async def _fetch_paper_by_arxiv_id(arxiv_id: str) -> Optional[Dict[str, Any]]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        return _apply_runtime_paper_override(
            next(
                (
                    row
                    for row in _load_baseline_seed_rows()
                    if str(row.get("arxiv_id") or "").strip() == arxiv_id
                ),
                None,
            )
        )

    result = await _run_db_blocking_with_retry(
        "fetch_paper_by_arxiv_id",
        lambda: (
            admin_client.table("papers")
            .select(_paper_select_clause())
            .eq("arxiv_id", arxiv_id)
            .limit(1)
            .execute()
        )
    )
    rows = result.data or []
    if rows:
        return _apply_runtime_paper_override(rows[0])
    return _apply_runtime_paper_override(
        next(
            (
                row
                for row in _load_baseline_seed_rows()
                if str(row.get("arxiv_id") or "").strip() == arxiv_id
            ),
            None,
        )
    )


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

    result = await _run_db_blocking_with_retry("fetch_paper_by_title", _query)
    rows = result.data or []
    return rows[0] if rows else None


async def _insert_paper(payload: Dict[str, Any]) -> Dict[str, Any]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        raise HTTPException(status_code=500, detail="Supabase admin client unavailable")

    result = await _run_db_blocking_with_retry(
        "insert_paper",
        lambda: admin_client.table("papers").insert(payload).execute()
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=500, detail="Failed to create paper")
    return rows[0]


async def _update_paper(paper_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        current = await _fetch_paper_by_id(paper_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Paper not found")
        merged = dict(current)
        merged.update(payload)
        _RUNTIME_PAPER_OVERRIDES[paper_id] = merged
        return merged

    result = await _run_db_blocking_with_retry(
        "update_paper",
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

    result = await _run_db_blocking_with_retry(
        "fetch_asset_rows_for_paper",
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

    await _run_db_blocking_with_retry(
        "clear_latest_asset",
        lambda: (
            admin_client.table("paper_assets")
            .update({"is_latest": False})
            .eq("paper_id", paper_id)
            .eq("asset_type", asset_type)
            .execute()
        )
    )
    result = await _run_db_blocking_with_retry(
        "insert_latest_asset",
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

    result = await _run_db_blocking_with_retry(
        "fetch_latest_assets",
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


def _normalize_paper_state_from_assets(
    paper: Dict[str, Any],
    *,
    latest_asset: Optional[Dict[str, Any]] = None,
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    normalized = dict(paper)
    selected_latest_asset = latest_asset or _select_latest_asset_from_map(asset_map)
    translated_asset: Optional[Dict[str, Any]] = None
    if asset_map:
        preview_asset = asset_map.get("preview_html")
        if _preview_asset_has_translated_content(preview_asset):
            translated_asset = preview_asset
        else:
            translated_asset = asset_map.get("translated_pdf")
    if (
        translated_asset is None
        and selected_latest_asset
        and selected_latest_asset.get("asset_type") in {"preview_html", "translated_pdf"}
        and (
            selected_latest_asset.get("asset_type") != "preview_html"
            or _preview_asset_has_translated_content(selected_latest_asset)
        )
    ):
        translated_asset = selected_latest_asset

    if translated_asset:
        normalized["trans_status"] = "completed"
        if translated_asset.get("task_id"):
            normalized["community_selected_task_id"] = translated_asset.get("task_id")
        if translated_asset.get("id"):
            normalized["community_selected_asset_id"] = translated_asset.get("id")
    elif str(normalized.get("trans_status") or "") in {"completed", "completed_with_warnings"}:
        normalized["trans_status"] = "failed"

    if _looks_untranslated_for_zh(normalized.get("abstract_translated")):
        normalized["abstract_translated"] = None

    return normalized


def _candidate_task_ids_for_asset_recovery(
    paper: Dict[str, Any],
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[str]:
    candidates: List[str] = []
    if asset_map:
        for asset_type in ("preview_html", "translated_pdf", "source_archive"):
            asset = asset_map.get(asset_type)
            task_id = asset.get("task_id") if asset else None
            if task_id and task_id not in candidates:
                candidates.append(str(task_id))
    for task_id in (paper.get("trans_latest_task_id"), paper.get("community_selected_task_id")):
        if task_id and task_id not in candidates:
            candidates.append(str(task_id))
    return candidates


def _candidate_source_directories_for_preview(
    *,
    paper_id: str,
    task_id: str,
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Path]:
    candidates: List[Path] = []
    seen: set[str] = set()

    def _add(path: Optional[Path]) -> None:
        if path is None:
            return
        try:
            normalized = str(path.resolve())
        except Exception:
            normalized = str(path)
        if normalized in seen:
            return
        seen.add(normalized)
        if path.exists() and path.is_dir():
            candidates.append(path)

    if asset_map:
        source_asset = asset_map.get("source_archive")
        if source_asset and source_asset.get("file_path"):
            _add(_resolve_storage_path(source_asset.get("file_path")))

    task = task_manager.get_task(task_id) if task_id else None
    if task:
        _add(_resolve_storage_path(task.get("source_path") or ""))

    paper_source_root = _community_library_root(paper_id) / "source"
    _add(paper_source_root)
    if paper_source_root.exists():
        for child in sorted(paper_source_root.iterdir()):
            if child.is_dir():
                _add(child)

    for output_dir in _candidate_output_directories_for_task(task_id):
        _add(output_dir)
        _add(output_dir.parent)

    return candidates


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

    likes = await _run_db_blocking_with_retry(
        "fetch_viewer_likes",
        lambda: (
            admin_client.table("paper_likes")
            .select("paper_id")
            .eq("user_id", user_id)
            .in_("paper_id", paper_ids)
            .execute()
        )
    )
    favorites = await _run_db_blocking_with_retry(
        "fetch_viewer_favorites",
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

    result = await _run_db_blocking_with_retry(
        "increment_paper_download_count",
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
    for output_dir in _candidate_output_directories_for_task(task_id):
        pdf_path = download_route._find_translated_pdf(output_dir)
        if not pdf_path or not pdf_path.exists():
            continue

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

    return None


async def _ensure_translated_pdf_asset(
    *,
    paper: Dict[str, Any],
    asset_map: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    translated_asset = asset_map.get("translated_pdf")
    if translated_asset:
        return translated_asset

    for task_id in _candidate_task_ids_for_asset_recovery(paper, asset_map):
        translated_asset = await _resolve_translated_pdf_asset(
            paper_id=str(paper["id"]),
            task_id=task_id,
        )
        if translated_asset:
            asset_map["translated_pdf"] = translated_asset
            return translated_asset

    return None


async def _fetch_sanitized_arxiv_html(arxiv_id: str) -> Optional[str]:
    normalized = str(arxiv_id or "").strip()
    if not normalized:
        return None

    cached = _source_html_cache.get(normalized)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"https://arxiv.org/html/{normalized}",
                headers={"User-Agent": "LaTeXTrans-Community-Reader/1.0"},
            )
            response.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(response.text, "lxml")
    for selector in (
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        ".ltx_page_navbar",
        ".ltx_page_header",
        ".ltx_page_footer",
        ".ltx_role_toc",
        ".ltx_role_footnote",
        ".ltx_note_mark",
        ".ltx_dates",
        ".ltx_classification",
    ):
        for node in soup.select(selector):
            node.decompose()

    article = soup.select_one("article") or soup.select_one("main") or soup.body
    if article is None:
        return None

    for child in list(article.children):
        if isinstance(child, NavigableString):
            child.extract()
            continue
        if not isinstance(child, Tag):
            continue
        child_classes = set(child.get("class", []))
        starts_reading_content = (
            child.name in {"h1", "h2"}
            or child.name == "section"
            or "ltx_abstract" in child_classes
            or "ltx_authors" in child_classes
            or "ltx_title" in child_classes
            or any(cls.startswith("ltx_section") for cls in child_classes)
        )
        if starts_reading_content:
            break
        child.decompose()

    for text_node in list(article.find_all(string=lambda value: isinstance(value, str) and "\\WarningFilter" in value)):
        parent = text_node.parent
        if parent and parent is not article:
            parent.decompose()
        else:
            text_node.extract()

    article_classes = article.get("class", [])
    article["class"] = [*dict.fromkeys([*article_classes, "latextrans-source-article"])]
    article["data-reader-origin"] = "arxiv"

    base_html_url = f"https://arxiv.org/html/{normalized}/"
    for image in article.select("img[src]"):
        src = str(image.get("src") or "").strip()
        if src and not src.startswith(("#", "data:", "http://", "https://")):
            image["src"] = urljoin(base_html_url, src)

    for source in article.select("source[srcset]"):
        srcset = str(source.get("srcset") or "").strip()
        if srcset and not srcset.startswith(("#", "data:", "http://", "https://")):
            source["srcset"] = urljoin(base_html_url, srcset)

    for link in article.select("a[href]"):
        href = str(link.get("href") or "").strip()
        if href and not href.startswith(("#", "mailto:", "javascript:", "http://", "https://")):
            link["href"] = urljoin(base_html_url, href)

    html_content = str(article)
    _source_html_cache[normalized] = html_content
    return html_content


def _source_reader_resource(
    *,
    paper: Dict[str, Any],
    source_html_content: Optional[str] = None,
    source_anchors: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    arxiv_id = str(paper.get("arxiv_id") or "").strip()
    if arxiv_id:
        if source_html_content:
            return {
                "kind": "source_html",
                "html_content": source_html_content,
                "url": f"https://arxiv.org/html/{arxiv_id}",
                "anchors": list(source_anchors or []),
            }
        return {
            "kind": "source_pdf",
            "html_content": None,
            "url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
            "anchors": list(source_anchors or []),
        }
    return None


def _translated_pdf_reader_resource(*, paper_id: str, asset: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "kind": "translated_pdf",
        "html_content": None,
        "url": f"/api/papers/{paper_id}/download-session",
        "asset_id": asset.get("id"),
    }


def _extract_reader_anchors_from_html(html_content: Optional[str]) -> List[Dict[str, Any]]:
    if not html_content:
        return []

    try:
        root = BeautifulSoup(html_content, "html.parser")
    except Exception:
        return []

    anchors: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def _register(anchor_id: Any, kind: str, label: Any = None) -> None:
        normalized_id = str(anchor_id or "").strip()
        if not normalized_id or normalized_id in seen:
            return
        seen.add(normalized_id)
        entry: Dict[str, Any] = {"anchor_id": normalized_id, "kind": kind}
        normalized_label = _normalize_metadata_text(label)
        if normalized_label:
            entry["label"] = normalized_label
        anchors.append(entry)

    for section in root.select("section[data-section-id]"):
        section_id = section.get("data-section-id")
        heading = section.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        _register(section_id, "section", heading.get_text(" ", strip=True) if heading else None)

    for block in root.select("[data-block-id]"):
        _register(block.get("data-block-id"), "block")

    for heading in root.select("section[id],h1[id],h2[id],h3[id],h4[id],h5[id],h6[id]"):
        _register(heading.get("id"), "section", heading.get_text(" ", strip=True))

    return anchors[:400]


def _build_reader_experience_payload(
    *,
    paper: Dict[str, Any],
    paper_id: str,
    preview_payload: Optional[Dict[str, Any]],
    translated_asset: Optional[Dict[str, Any]],
    source_html_content: Optional[str] = None,
) -> Dict[str, Any]:
    source_anchors = _extract_reader_anchors_from_html(source_html_content)
    translated_anchors = _extract_reader_anchors_from_html(
        str(preview_payload.get("html_content") or "") if preview_payload else None
    )
    source_resource = _source_reader_resource(
        paper=paper,
        source_html_content=source_html_content,
        source_anchors=source_anchors,
    )
    translated_resource: Optional[Dict[str, Any]] = None
    if preview_payload:
        translated_resource = {
            "kind": "preview_html",
            "html_content": preview_payload.get("html_content"),
            "url": None,
            "anchors": translated_anchors,
        }
    elif translated_asset:
        translated_resource = _translated_pdf_reader_resource(
            paper_id=paper_id,
            asset=translated_asset,
        )

    available_modes: List[str] = []
    if source_resource:
        available_modes.append("source")
    if translated_resource:
        available_modes.append("translated")
    if not available_modes:
        available_modes.append("source")

    trans_status = str(paper.get("trans_status") or "")
    if translated_resource:
        stage_label = "中文版已准备好"
        failure_type = None
        can_leave_hint = None
        preferred_mode = "translated"
        resolved_reader_state = "translated_ready"
    elif trans_status in {"queued", "processing"}:
        stage_label = "正在生成中文版本"
        failure_type = None
        can_leave_hint = "你可以先阅读，完成后会自动更新"
        preferred_mode = "source"
        resolved_reader_state = "warming" if source_resource else "unavailable"
    elif source_resource and trans_status in {"completed", "completed_with_warnings"}:
        stage_label = "Reader upgrade in progress"
        failure_type = None
        can_leave_hint = "Reader content is refreshing in the background."
        preferred_mode = "source"
        resolved_reader_state = "warming"
    elif source_resource and trans_status in {"failed", "failed_compilation", "structure_invalid"}:
        stage_label = "英文阅读仍可用"
        failure_type = "translation_failed"
        can_leave_hint = None
        preferred_mode = "source"
        resolved_reader_state = "source_ready"
    elif source_resource:
        stage_label = "已准备英文阅读"
        failure_type = None
        can_leave_hint = None
        preferred_mode = "source"
        resolved_reader_state = "source_ready"
    else:
        stage_label = "暂时无法完成中文生成"
        failure_type = "translation_failed" if trans_status in TERMINAL_TASK_STATUSES else None
        can_leave_hint = None
        preferred_mode = "source"
        resolved_reader_state = "unavailable"

    return {
        "reader_state": "ready" if resolved_reader_state in {"source_ready", "translated_ready"} else resolved_reader_state,
        "reader": {
            "preferred_mode": preferred_mode,
            "available_modes": available_modes,
            "source": source_resource,
            "translated": translated_resource,
            "active_anchor_id": (
                (translated_anchors[0].get("anchor_id") if translated_anchors else None)
                or (source_anchors[0].get("anchor_id") if source_anchors else None)
            ),
            "state": resolved_reader_state,
        },
        "experience": {
            "stage_label": stage_label,
            "can_leave_hint": can_leave_hint,
            "failure_type": failure_type,
        },
    }


async def _resolve_preview_html_asset(
    *,
    paper: Dict[str, Any],
    paper_id: str,
    task_id: str,
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    preview_asset: Optional[Dict[str, str]] = None
    source_dirs = _candidate_source_directories_for_preview(
        paper_id=paper_id,
        task_id=task_id,
        asset_map=asset_map,
    )
    for output_dir in _candidate_output_directories_for_task(task_id):
        try:
            preview_asset = paper_preview_service.generate_preview_html(
                output_dir,
                target_dir=_community_library_root(paper_id) / "preview",
                source_dirs=source_dirs,
                paper_metadata={
                    "title": paper.get("title"),
                    "authors": paper.get("authors") or [],
                },
            )
            break
        except FileNotFoundError:
            continue

    if not preview_asset:
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
    created_by: Optional[str],
    community_status: str,
    authors: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    abstract_raw: Optional[str] = None,
    abstract_translated: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    task_id: Optional[str] = None,
    selected_asset_id: Optional[str] = None,
    official_published_at: Optional[str] = None,
    trans_status: str = "queued",
) -> Dict[str, Any]:
    return {
        "source": source,
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors or [],
        "categories": categories or [],
        "abstract_raw": abstract_raw,
        "abstract_translated": abstract_translated,
        "visibility": "public",
        "status": "published",
        "trans_status": trans_status,
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
        task_status = task.get("status")
        update_payload: Dict[str, Any] = {"updated_at": _utc_now_iso()}
        if task_status == "pending":
            update_payload["trans_status"] = "not_started"
        else:
            update_payload["trans_status"] = "processing" if task_status == "processing" else "queued"
            update_payload["community_selected_task_id"] = task_id
        if asset:
            source_asset_id = asset.get("id")
            update_payload["community_selected_asset_id"] = source_asset_id
        if promote_to_official:
            update_payload["community_status"] = COMMUNITY_STATUS_OFFICIAL
            update_payload["official_published_at"] = _utc_now_iso()
        paper = await _update_paper(paper_id, update_payload)
        if task_status == "pending":
            return {"done": True, "status": "pending", "paper": paper}

    if task.get("status") in {"completed", "completed_with_warnings"}:
        translated_asset = await _resolve_translated_pdf_asset(
            paper_id=paper_id,
            task_id=task_id,
        )
        preview_asset = await _resolve_preview_html_asset(
            paper=paper,
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
        translated_asset = await _resolve_translated_pdf_asset(
            paper_id=paper_id,
            task_id=task_id,
        )
        preview_asset = await _resolve_preview_html_asset(
            paper=paper,
            paper_id=paper_id,
            task_id=task_id,
        )
        selected_asset = preview_asset or translated_asset
        paper = await _update_paper(
            paper_id,
            {
                "trans_status": "failed",
                "community_selected_task_id": task_id,
                **(
                    {"community_selected_asset_id": selected_asset.get("id")}
                    if selected_asset and selected_asset.get("id")
                    else {}
                ),
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


async def mark_paper_translation_failed_by_task(task_id: str) -> int:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        return 0

    normalized_task_id = str(task_id or "").strip()
    if not normalized_task_id:
        return 0

    result = await _run_db_blocking_with_retry(
        "mark_paper_translation_failed_by_task.select",
        lambda: (
            admin_client.table("papers")
            .select("id")
            .eq("community_selected_task_id", normalized_task_id)
            .in_("trans_status", ["queued", "processing"])
            .execute()
        ),
    )
    rows = result.data or []
    paper_ids = [str(row.get("id") or "").strip() for row in rows if row.get("id")]
    if not paper_ids:
        return 0

    await _run_db_blocking_with_retry(
        "mark_paper_translation_failed_by_task.update",
        lambda: (
            admin_client.table("papers")
            .update({"trans_status": "failed", "updated_at": _utc_now_iso()})
            .in_("id", paper_ids)
            .execute()
        ),
    )
    return len(paper_ids)


async def resume_inflight_paper_translation_watchers() -> Dict[str, Any]:
    """
    Recreate in-memory paper watchers for tasks still marked queued/processing.
    """
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        return {"resumed_watchers": 0}

    result = await _run_db_blocking_with_retry(
        "resume_inflight_paper_translation_watchers",
        lambda: (
            admin_client.table("papers")
            .select("id, community_selected_task_id, trans_status, community_status")
            .in_("trans_status", ["queued", "processing"])
            .execute()
        ),
    )
    rows = result.data or []
    resumed_watchers = 0
    for row in rows:
        paper_id = str(row.get("id") or "").strip()
        task_id = str(row.get("community_selected_task_id") or "").strip()
        if not paper_id or not task_id:
            continue
        asyncio.create_task(
            _watch_task_and_sync_asset(
                paper_id=paper_id,
                task_id=task_id,
                promote_to_official=row.get("community_status") == COMMUNITY_STATUS_OFFICIAL,
            )
        )
        resumed_watchers += 1

    return {"resumed_watchers": resumed_watchers}


def _paper_summary(
    paper: Dict[str, Any],
    *,
    latest_asset: Optional[Dict[str, Any]] = None,
    asset_map: Optional[Dict[str, Dict[str, Any]]] = None,
    viewer_state: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    paper = _normalize_paper_state_from_assets(
        paper,
        latest_asset=latest_asset,
        asset_map=asset_map,
    )
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
            trans_status="not_started",
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
                "trans_status": "not_started",
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

    if credentials is None:
        context = {"user_id": None, "roles": [], "is_admin": False}
    else:
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
    metadata = await _fetch_arxiv_metadata(arxiv_id)

    if existing:
        update_payload: Dict[str, Any] = {
            "community_status": COMMUNITY_STATUS_OFFICIAL,
            "trans_status": "not_started",
            "trans_latest_task_id": None,
            "community_selected_task_id": None,
            "official_published_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        update_payload.update(_best_available_metadata_payload(existing, metadata))
        paper = await _update_paper(existing["id"], update_payload)
        admission_result = "created"
    else:
        paper = await _insert_paper(
            _paper_payload(
                source="arxiv",
                arxiv_id=arxiv_id,
                title=metadata.get("title") or f"arXiv:{arxiv_id}",
                created_by=context["user_id"],
                community_status=admission["community_status"],
                authors=metadata.get("authors"),
                categories=metadata.get("categories"),
                abstract_raw=metadata.get("abstract_raw"),
                task_id=None,
                official_published_at=_utc_now_iso() if context["is_admin"] else None,
                trans_status="not_started",
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
    submitter_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    if submitter_user_id:
        context = await resolve_submitter_context_by_user_id(submitter_user_id)
    elif credentials is None:
        context = {"user_id": None, "roles": [], "is_admin": False}
    else:
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

    try:
        asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    except HTTPException as exc:
        if exc.status_code == 500 and exc.detail == "Supabase admin client unavailable":
            asset_map = {}
        else:
            raise
    source_asset = asset_map.get("source_archive")
    if source_asset and source_asset.get("file_path"):
        resolved_source_path = _resolve_storage_path(source_asset["file_path"])
        if resolved_source_path.exists():
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
    preview_payload = (
        _build_preview_payload(
            paper_id=paper_id,
            paper=paper,
            preview_asset=preview_asset,
        )
        if preview_asset
        else None
    )
    if preview_payload:
        return preview_payload
    if preview_asset:
        preview_asset = None

    if not preview_asset:
        for task_id in _candidate_task_ids_for_asset_recovery(paper, asset_map):
            preview_asset = await _resolve_preview_html_asset(
                paper=paper,
                paper_id=paper_id,
                task_id=task_id,
                asset_map=asset_map,
            )
            if preview_asset:
                break
    if not preview_asset:
        raise HTTPException(status_code=404, detail="Preview not available")

    preview_payload = _build_preview_payload(
        paper_id=paper_id,
        paper=paper,
        preview_asset=preview_asset,
    )
    if preview_payload:
        return preview_payload

    raise HTTPException(status_code=404, detail="Preview file not found")


async def create_paper_download_session(*, paper_id: str) -> Dict[str, Any]:
    paper = await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    translated_asset = await _ensure_translated_pdf_asset(paper=paper, asset_map=asset_map)
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

    paper = await _ensure_public_paper(paper_id)
    asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
    translated_asset = await _ensure_translated_pdf_asset(paper=paper, asset_map=asset_map)
    if not translated_asset:
        raise HTTPException(status_code=404, detail="Translated PDF not available")
    if payload.get("asset_id") != translated_asset.get("id"):
        raise HTTPException(status_code=403, detail="Download token does not match asset")

    file_path = _resolve_storage_path(translated_asset.get("file_path") or "")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Translated PDF file not found")

    try:
        await _increment_paper_download_count(paper_id)
    except Exception as exc:
        logger.warning("Failed to increment download count for paper %s: %s", paper_id, exc)
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
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    admin_client = get_supabase_admin_client()
    papers: List[Dict[str, Any]] = []
    source_mode = "database"
    if admin_client is not None:
        result = await _run_db_blocking_with_retry(
            "list_community_papers",
            lambda: (
                admin_client.table("papers")
                .select(_paper_select_clause())
                .eq("visibility", "public")
                .neq("status", "removed")
                .execute()
            )
        )
        papers = result.data or []

    if not papers:
        baseline_rows = _load_baseline_seed_rows()
        if baseline_rows:
            papers = baseline_rows
            source_mode = "baseline_seed"

    if not papers and admin_client is None:
        logger.warning(
            "Supabase admin client unavailable and no baseline seed rows found; returning empty community list"
        )

    papers = [_apply_runtime_paper_override(paper) or paper for paper in papers]
    papers = [paper for paper in papers if _matches_paper_query(paper, q)]
    papers = _sort_papers(papers, sort)
    if limit is not None and limit > 0:
        papers = papers[:limit]

    paper_ids = [paper["id"] for paper in papers]
    latest_assets = await _fetch_latest_assets(paper_ids) if admin_client is not None else {}
    items = [
        _paper_summary(paper, latest_asset=latest_assets.get(paper["id"]))
        for paper in papers
    ]
    return {"items": items, "total": len(items), "source_mode": source_mode}


async def get_community_paper_detail(
    *,
    paper_id: str,
    viewer_user_id: Optional[str] = None,
    fast_path: bool = False,
) -> Dict[str, Any]:
    paper = await _fetch_paper_by_id(paper_id)
    if paper is None or paper.get("visibility") != "public" or paper.get("status") == "removed":
        raise HTTPException(status_code=404, detail="Paper not found")

    asset_map: Optional[Dict[str, Dict[str, Any]]] = None
    latest_asset: Optional[Dict[str, Any]] = None
    try:
        asset_map = await _fetch_asset_map_for_paper(paper_id=paper_id)
        latest_asset = _select_latest_asset_from_map(asset_map)
    except Exception as exc:
        logger.warning("Failed to fetch full asset map for paper %s: %s", paper_id, exc)
        asset_map = None
        try:
            latest_asset = (await _fetch_latest_assets([paper_id])).get(paper_id)
        except Exception:
            latest_asset = None
    if fast_path:
        _schedule_public_detail_repair(
            paper_id=paper_id,
            paper=paper,
            asset_map=asset_map,
        )
    else:
        paper = await _hydrate_arxiv_metadata_if_needed(paper)
        paper = await _hydrate_translated_abstract_if_needed(
            paper,
            asset_map=asset_map,
        )
    viewer_state = (await _fetch_viewer_state([paper_id], user_id=viewer_user_id)).get(
        paper_id,
        {"liked": False, "favorited": False},
    )
    resolved_asset_map: Dict[str, Dict[str, Any]] = dict(asset_map or {})
    preview_payload: Optional[Dict[str, Any]] = None

    preview_asset = resolved_asset_map.get("preview_html")
    if preview_asset:
        preview_payload = _build_preview_payload(
            paper_id=paper_id,
            paper=paper,
            preview_asset=preview_asset,
        )

    if not preview_payload:
        for task_id in _candidate_task_ids_for_asset_recovery(paper, resolved_asset_map):
            preview_asset = await _resolve_preview_html_asset(
                paper=paper,
                paper_id=paper_id,
                task_id=task_id,
                asset_map=resolved_asset_map,
            )
            if not preview_asset:
                continue
            resolved_asset_map["preview_html"] = preview_asset
            preview_payload = _build_preview_payload(
                paper_id=paper_id,
                paper=paper,
                preview_asset=preview_asset,
            )
            if preview_payload:
                break

    translated_asset = await _ensure_translated_pdf_asset(
        paper=paper,
        asset_map=resolved_asset_map,
    )

    if not preview_payload and paper.get("trans_status") in {"completed", "completed_with_warnings"}:
        _schedule_preview_recovery(
            paper_id=paper_id,
            paper=paper,
            asset_map=resolved_asset_map,
        )

    source_html_content = await _fetch_sanitized_arxiv_html(str(paper.get("arxiv_id") or ""))

    reader_payload = _build_reader_experience_payload(
        paper=paper,
        paper_id=paper_id,
        preview_payload=preview_payload,
        translated_asset=translated_asset,
        source_html_content=source_html_content,
    )

    return {
        "paper": _paper_summary(
            paper,
            latest_asset=latest_asset,
            asset_map=resolved_asset_map,
            viewer_state=viewer_state,
        ),
        "preview": preview_payload,
        "reader_state": reader_payload["reader_state"],
        "reader": reader_payload["reader"],
        "experience": reader_payload["experience"],
    }


async def import_or_reuse_paper(*, source: str, arxiv_id: str) -> Dict[str, Any]:
    """
    Import an external paper into the community library, or reuse an existing one.

    This is a minimal bridge for the community agent / homepage agent to perform
    “静默导入”. It prefers reusing existing papers when possible.
    """
    # 如果已有对应 arxiv_id 的 paper，则直接复用
    existing = await _fetch_paper_by_arxiv_id(arxiv_id)
    if existing is not None:
        return {
            "paper_id": existing["id"],
            "reused": True,
            "imported": False,
            "reader_state": "source_ready",
        }

    baseline_existing = next(
        (
            row
            for row in _load_baseline_seed_rows()
            if str(row.get("arxiv_id") or "").strip() == arxiv_id
        ),
        None,
    )
    if baseline_existing is not None:
        return {
            "paper_id": baseline_existing["id"],
            "reused": True,
            "imported": False,
            "reader_state": "source_ready",
        }

    # 否则走现有提交流程创建一篇新论文。这里调用 submit_arxiv_paper，
    # 并假定服务角色或匿名用户上下文在上层处理。
    payload = await submit_arxiv_paper(
        arxiv_id=arxiv_id,
        credentials=None,
        source_language="en",
        target_language="zh",
    )
    paper = payload["paper"]
    return {
        "paper_id": paper["id"],
        "reused": False,
        "imported": True,
        "reader_state": "source_ready",
    }


async def record_community_paper_view(*, paper_id: str) -> Dict[str, Any]:
    admin_client = get_supabase_admin_client()
    if admin_client is None:
        paper = await _fetch_paper_by_id(paper_id)
        if paper is None or paper.get("visibility") != "public" or paper.get("status") == "removed":
            raise HTTPException(status_code=404, detail="Paper not found")
        return {"paper_id": paper_id, "view_count": int(paper.get("view_count") or 0)}

    result = await _run_db_blocking_with_retry(
        "increment_paper_view_count",
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
