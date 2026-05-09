from __future__ import annotations

from pathlib import PurePosixPath
import re
from typing import Any, Optional

from backend.app.core.config import get_settings
from backend.app.services.storage_backend import CosStorageBackend, _ensure_cos_config

ARXIV_EPRINT_FALLBACK_SOURCES = (
    "https://export.arxiv.org/e-print/{arxiv_id}",
    "https://arxiv.org/e-print/{arxiv_id}",
)

_SAFE_ARXIV_ID_RE = re.compile(r"^[0-9A-Za-z._/-]+$")


def _settings_value(settings: Any, name: str, default: Any = None) -> Any:
    return getattr(settings, name, default)


def _normalize_prefix(settings: Any) -> str:
    return str(_settings_value(settings, "arxiv_raw_cache_prefix", "") or "").strip().strip("/")


def _join_key(*parts: str) -> str:
    return "/".join(part.strip("/") for part in parts if part.strip("/"))


def normalize_arxiv_id_for_object(arxiv_id: str) -> str:
    normalized = str(arxiv_id or "").strip().strip("/")
    if normalized.endswith(".pdf"):
        normalized = normalized[:-4]
    if not normalized or not _SAFE_ARXIV_ID_RE.fullmatch(normalized):
        raise ValueError("Unsafe arXiv identifier for COS raw cache.")

    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("Unsafe arXiv identifier for COS raw cache.")
    return "/".join(path.parts)


def raw_pdf_object_key(arxiv_id: str, *, settings: Optional[Any] = None) -> str:
    active_settings = settings or get_settings()
    return _join_key(_normalize_prefix(active_settings), "pdf", normalize_arxiv_id_for_object(arxiv_id))


def _legacy_raw_pdf_object_key(arxiv_id: str, *, settings: Optional[Any] = None) -> str:
    active_settings = settings or get_settings()
    return _join_key(_normalize_prefix(active_settings), "pdf", f"{normalize_arxiv_id_for_object(arxiv_id)}.pdf")


def raw_eprint_object_key(arxiv_id: str, *, settings: Optional[Any] = None) -> str:
    active_settings = settings or get_settings()
    return _join_key(_normalize_prefix(active_settings), "e-print", normalize_arxiv_id_for_object(arxiv_id))


def is_enabled(*, settings: Optional[Any] = None) -> bool:
    active_settings = settings or get_settings()
    return (
        str(_settings_value(active_settings, "storage_backend_mode", "") or "").strip().lower() == "cos"
        and bool(_settings_value(active_settings, "arxiv_raw_cache_enabled", False))
    )


def _get_backend(settings: Any, backend: Optional[Any] = None) -> Optional[Any]:
    if backend is not None:
        return backend
    if str(_settings_value(settings, "storage_backend_mode", "") or "").strip().lower() != "cos":
        return None
    _ensure_cos_config(settings)
    return CosStorageBackend(
        bucket=settings.cos_bucket,
        region=settings.cos_region,
        secret_id=settings.cos_secret_id,
        secret_key=settings.cos_secret_key,
        base_prefix="",
    )


def is_raw_pdf_object_key(object_key: str, arxiv_id: str, *, settings: Optional[Any] = None) -> bool:
    try:
        normalized_key = str(object_key or "").strip().strip("/")
        return normalized_key in {
            raw_pdf_object_key(arxiv_id, settings=settings),
            _legacy_raw_pdf_object_key(arxiv_id, settings=settings),
        }
    except ValueError:
        return False


def _build_signed_url(
    *,
    object_key: str,
    settings: Any,
    backend: Optional[Any],
    filename: Optional[str],
    content_type: Optional[str],
    inline: bool,
) -> Optional[str]:
    if not is_enabled(settings=settings):
        return None

    resolved_backend = _get_backend(settings, backend)
    if resolved_backend is None:
        return None

    params: dict[str, str] = {}
    if filename:
        disposition = "inline" if inline else "attachment"
        params["response-content-disposition"] = f'{disposition}; filename="{filename}"'
    if content_type:
        params["response-content-type"] = content_type

    return resolved_backend.build_download_url(
        object_key=object_key,
        expires_in=int(_settings_value(settings, "arxiv_raw_cache_signed_url_expires_seconds", 600) or 600),
        params=params or None,
    )


def build_pdf_download_url(
    arxiv_id: str,
    *,
    settings: Optional[Any] = None,
    backend: Optional[Any] = None,
    filename: Optional[str] = None,
    inline: bool = True,
) -> Optional[str]:
    active_settings = settings or get_settings()
    return _build_signed_url(
        object_key=raw_pdf_object_key(arxiv_id, settings=active_settings),
        settings=active_settings,
        backend=backend,
        filename=filename,
        content_type="application/pdf",
        inline=inline,
    )


def build_eprint_download_url(
    arxiv_id: str,
    *,
    settings: Optional[Any] = None,
    backend: Optional[Any] = None,
) -> Optional[str]:
    active_settings = settings or get_settings()
    return _build_signed_url(
        object_key=raw_eprint_object_key(arxiv_id, settings=active_settings),
        settings=active_settings,
        backend=backend,
        filename=None,
        content_type=None,
        inline=False,
    )


def build_eprint_source_urls(
    arxiv_id: str,
    *,
    settings: Optional[Any] = None,
    backend: Optional[Any] = None,
) -> list[str]:
    urls: list[str] = []
    signed_url = build_eprint_download_url(arxiv_id, settings=settings, backend=backend)
    if signed_url:
        urls.append(signed_url)
    urls.extend(source.format(arxiv_id=arxiv_id) for source in ARXIV_EPRINT_FALLBACK_SOURCES)
    return urls
