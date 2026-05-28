"""PDF 缩略图服务

为论文 PDF 生成第一页缩略图，支持本地缓存和对象存储分发。
"""

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
from backend.app.services.storage_backend import LocalDiskStorageBackend, build_storage_backend

# 缩略图缓存版本（变更版本号可使所有缓存失效）
THUMBNAIL_CACHE_VERSION = "v3"


def _thumbnail_cache_dir() -> Path:
    """获取缩略图本地缓存目录"""
    settings = get_settings()
    cache_dir = Path(settings.storage_temp_dir) / "paper_pdf_thumbnails"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _decode_png_data_uri(payload: Optional[str]) -> Optional[bytes]:
    """解码 PNG data URI 为原始字节"""
    normalized = str(payload or "")
    if not normalized.startswith("data:image/png;base64,"):
        return None
    encoded = normalized.split(",", 1)[1]
    try:
        return base64.b64decode(encoded)
    except Exception:
        return None


def _thumbnail_cache_path(cache_seed: str) -> Path:
    """根据缓存种子生成缩略图缓存文件路径"""
    digest = hashlib.sha256(f"{THUMBNAIL_CACHE_VERSION}:{cache_seed}".encode("utf-8")).hexdigest()
    return _thumbnail_cache_dir() / f"{digest}.png"


def _thumbnail_digest(cache_seed: str) -> str:
    """根据缓存种子生成缩略图摘要值"""
    return hashlib.sha256(f"{THUMBNAIL_CACHE_VERSION}:{cache_seed}".encode("utf-8")).hexdigest()


def _thumbnail_object_key(cache_seed: str) -> str:
    """根据缓存种子生成缩略图 COS 对象键"""
    return f"data/paper_pdf_thumbnails/{_thumbnail_digest(cache_seed)}.png"


def _get_storage_backend():
    """获取存储后端实例"""
    return build_storage_backend(get_settings())


def _storage_backend_is_object_store(backend) -> bool:
    """判断存储后端是否为对象存储（非本地磁盘）"""
    return not isinstance(backend, LocalDiskStorageBackend)


def _render_pdf_thumbnail_bytes_from_path(pdf_path: Path) -> Optional[bytes]:
    """从本地 PDF 路径渲染第一页为 PNG 缩略图字节"""
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
    """从远程 URL 下载 PDF 并渲染第一页为 PNG 缩略图字节"""
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
    """确保 PDF 缩略图已生成并缓存

    参数:
        cache_seed: 缓存种子（通常为 arXiv ID 或文件哈希）
        file_path: 本地 PDF 文件路径（可选）
        remote_url: 远程 PDF 文件 URL（可选）

    返回:
        缓存缩略图文件的路径，失败时返回 None
    """
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


async def ensure_pdf_thumbnail_delivery(
    *,
    cache_seed: str,
    file_path: Optional[str] = None,
    remote_url: Optional[str] = None,
    expires_in: int = 600,
) -> Optional[dict[str, str]]:
    """确保 PDF 缩略图可通过合适的渠道分发

    本地存储时直接返回文件路径，对象存储时返回签名 URL。

    参数:
        cache_seed: 缓存种子
        file_path: 本地 PDF 文件路径（可选）
        remote_url: 远程 PDF URL（可选）
        expires_in: 签名 URL 有效期（秒），默认 600

    返回:
        包含 file_path 或 signed_url 的字典，失败时返回 None
    """
    backend = _get_storage_backend()
    if not _storage_backend_is_object_store(backend):
        cache_path = await ensure_pdf_thumbnail(
            cache_seed=cache_seed,
            file_path=file_path,
            remote_url=remote_url,
        )
        return {"file_path": str(cache_path)} if cache_path else None

    object_key = _thumbnail_object_key(cache_seed)
    if not backend.object_exists(object_key=object_key):
        cache_path = await ensure_pdf_thumbnail(
            cache_seed=cache_seed,
            file_path=file_path,
            remote_url=remote_url,
        )
        if not cache_path:
            return None
        backend.put_file(
            local_path=cache_path,
            object_key=object_key,
            content_type="image/png",
            delete_local=False,
        )

    signed_url = backend.build_download_url(
        object_key=object_key,
        expires_in=expires_in,
        params={"response-content-type": "image/png"},
    )
    return {"signed_url": signed_url} if signed_url else None
