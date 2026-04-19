from __future__ import annotations

import asyncio
import base64
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import httpx

from backend.app.core.config import get_settings
from backend.app.services import paper_preview_service

THUMBNAIL_CACHE_VERSION = "v3"


def _thumbnail_cache_dir() -> Path:
    settings = get_settings()
    cache_dir = Path(settings.storage_temp_dir) / "paper_pdf_thumbnails"
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
    return _thumbnail_cache_dir() / f"{digest}.png"


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


async def ensure_pdf_thumbnail(
    *,
    cache_seed: str,
    file_path: Optional[str] = None,
    remote_url: Optional[str] = None,
) -> Optional[Path]:
    cache_path = _thumbnail_cache_path(cache_seed)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        return cache_path

    thumbnail_bytes: Optional[bytes] = None
    if file_path:
        thumbnail_bytes = await asyncio.to_thread(_render_pdf_thumbnail_bytes_from_path, Path(file_path))
    elif remote_url:
        thumbnail_bytes = await _render_pdf_thumbnail_bytes_from_url(remote_url)

    if not thumbnail_bytes:
        return None

    cache_path.write_bytes(thumbnail_bytes)
    return cache_path
