"""
下载 API 路由

提供下载翻译后的 PDF 和源文件的接口。
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from starlette.background import BackgroundTask
import httpx
import logging
import json
import subprocess
from pathlib import Path
import zipfile
import tempfile
import shutil

from typing import Optional
from backend.app.services.task_manager import get_task_manager
from backend.app.services import task_artifact_storage
from backend.app.services import arxiv_raw_cache
from backend.app.services.latex.compiler import compile_with_intelligent_fallback
from backend.app.core.config import get_settings, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()

TERMINAL_SUCCESS_STATUSES = {
    TaskStatus.COMPLETED.value,
    TaskStatus.COMPLETED_WITH_WARNINGS.value,
}


def _validate_pdf_with_pdfinfo(pdf_path: Path) -> bool:
    """使用 pdfinfo 进行 PDF 结构完整性检查。"""
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        logger.warning("pdfinfo is missing; skipping validation for %s", pdf_path)
        return True
    except Exception as exc:
        logger.error("pdfinfo validation failed for %s: %s", pdf_path, exc)
        return False
    return result.returncode == 0


def _find_translated_pdf(output_dir: Path) -> Optional[Path]:
    """
    定位翻译后的 PDF，使用严格规则避免误选复制来的源 PDF。

    优先级：
    1. task_log.json 事件中的 compilation_completed / compilation_completed_with_warnings
       - 同时支持输出根目录及其直接子目录。
    2. 根级 *_translated.pdf 文件
    3. 约定路径: output_dir/<subdir>/<subdir>.pdf（仅直接子目录）
    """

    def _iter_log_files(root: Path):
        root_log = root / "task_log.json"
        if root_log.is_file():
            yield root_log
        for child in root.iterdir():
            if not child.is_dir():
                continue
            child_log = child / "task_log.json"
            if child_log.is_file():
                yield child_log

    def _extract_pdf_from_log(log_path: Path) -> Optional[Path]:
        try:
            entries = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to parse task log for PDF resolution: {e}")
            return None

        for entry in reversed(entries):
            if entry.get("event") not in ("compilation_completed", "compilation_completed_with_warnings"):
                continue
            raw_path = entry.get("pdf_path")
            if not raw_path:
                continue
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = log_path.parent / candidate
            try:
                candidate_resolved = candidate.resolve()
                output_resolved = output_dir.resolve()
                candidate_resolved.relative_to(output_resolved)
            except Exception:
                continue
            if candidate.is_file():
                return candidate
        return None

    # 1) Use task-log explicit pdf_path first.
    for log_file in _iter_log_files(output_dir):
        resolved = _extract_pdf_from_log(log_file)
        if resolved:
            return resolved

    # 2) 根级目录查找显式命名的翻译 PDF。
    pdf_files = list(output_dir.glob("*_translated.pdf"))
    if pdf_files:
        return pdf_files[0]

    # 3) 严格约定：直接子目录中包含同名 PDF 文件。
    for child in output_dir.iterdir():
        if not child.is_dir():
            continue
        expected_pdf = child / f"{child.name}.pdf"
        if expected_pdf.is_file():
            return expected_pdf

    return None


def _candidate_output_dirs(task_id: str, task: Optional[dict]) -> list[Path]:
    """按可信度降序返回输出目录候选列表。"""
    candidates: list[Path] = []
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

    if task:
        output_path = str(task.get("output_path") or "").strip()
        if output_path:
            _add(Path(output_path))

    task_root = settings.outputs_dir / task_id
    _add(task_root)
    if task_root.exists() and task_root.is_dir():
        for child in sorted(task_root.iterdir()):
            if child.is_dir():
                _add(child)

    return candidates


def _find_translated_pdf_in_community_library(task_id: str) -> Optional[Path]:
    """当任务输出不可用但资源文件存在时的尽力回退方案。"""
    root = settings.community_papers_dir
    if not root.exists():
        return None

    task_prefix = f"{task_id}-"
    for paper_dir in sorted(root.iterdir()):
        if not paper_dir.is_dir():
            continue
        translated_dir = paper_dir / "translated"
        if not translated_dir.exists() or not translated_dir.is_dir():
            continue
        for candidate in sorted(translated_dir.glob("*.pdf")):
            if candidate.name.startswith(task_prefix) and candidate.is_file():
                return candidate
    return None


def _collect_original_pdf_candidates(source_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for pdf in source_dir.rglob("*.pdf"):
        name = pdf.name
        if (
            name.startswith("zh_")
            or "_translated" in name
            or "zh-" in name
            or name.startswith("source_compiled_")
        ):
            continue
        if pdf.is_file() and pdf.stat().st_size > 0:
            candidates.append(pdf)
    return candidates


def _pick_best_source_pdf(source_dir: Path, candidates: list[Path], preferred_stem: Optional[str]) -> Optional[Path]:
    if not candidates:
        return None

    preferred = str(preferred_stem or "").strip().lower()

    def _score(path: Path) -> tuple[int, int, int, int, int]:
        rel_parts = path.relative_to(source_dir).parts
        stem = path.stem.lower()
        exact = int(bool(preferred) and stem == preferred)
        top_level = int(len(rel_parts) <= 2)
        main_like = int(stem in {"main", "paper", "source", "manuscript"})
        depth_score = -len(rel_parts)
        size_score = int(path.stat().st_size)
        return (exact, top_level, main_like, depth_score, size_score)

    return max(candidates, key=_score)


def _find_source_pdf_in_community_library(task_id: str, preferred_arxiv_id: Optional[str] = None) -> Optional[Path]:
    """
    从社区库资源中解析源 PDF，避免不必要的网络请求。
    优先使用本地文件，而非远程获取。
    """
    root = settings.community_papers_dir
    if not root.exists():
        return None

    # 策略 1（最高优先级）：在所有社区集合中按 ArXiv ID 全局搜索。
    # 确保只要任一社区论文存在原始源 PDF，就优先使用它。
    preferred_id = str(preferred_arxiv_id or "").strip()
    if preferred_id:
        for paper_dir in sorted(root.iterdir()):
            if not paper_dir.is_dir():
                continue
            
            # 检查源目录
            source_dir = paper_dir / "source"
            if source_dir.exists() and source_dir.is_dir():
                # 直接匹配 <arxiv_id>.pdf
                expected = f"{preferred_id}.pdf"
                for candidate in source_dir.rglob(expected):
                    if candidate.is_file() and candidate.stat().st_size > 0:
                        return candidate
                
                # 启发式匹配：若此 paper_dir 属于该 arxiv_id，选取最佳 PDF。
                # 许多论文以 arxiv_id 命名的目录形式存储。
                if preferred_id in paper_dir.name:
                    candidates = _collect_original_pdf_candidates(source_dir)
                    best = _pick_best_source_pdf(source_dir, candidates, preferred_id)
                    if best:
                        return best

    # 策略 2：按任务关联解析（回退方案）
    # 查找与同一任务集群关联的论文。
    task_prefix = f"{task_id}-"
    matched_papers: list[Path] = []

    for paper_dir in sorted(root.iterdir()):
        if not paper_dir.is_dir():
            continue
        translated_dir = paper_dir / "translated"
        if not translated_dir.exists() or not translated_dir.is_dir():
            continue
        if any(candidate.name.startswith(task_prefix) for candidate in translated_dir.glob("*.pdf")):
            matched_papers.append(paper_dir)

    for paper_dir in matched_papers:
        source_dir = paper_dir / "source"
        if not source_dir.exists() or not source_dir.is_dir():
            continue
        candidates = _collect_original_pdf_candidates(source_dir)
        selected = _pick_best_source_pdf(source_dir, candidates, preferred_id)
        if selected:
            return selected

    return None


def _extract_arxiv_id_from_text(value: Optional[str]) -> Optional[str]:
    import re

    normalized = str(value or "").strip()
    if not normalized:
        return None
    match = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?", normalized)
    if not match:
        return None
    return match.group(1)


async def _proxy_arxiv_pdf(
    arxiv_id: str,
    filename: str,
    *,
    request: Optional[Request] = None,
    content_disposition: str = "inline",
) -> StreamingResponse:
    """
    通过后端代理流式传输 arXiv PDF，避免前端 CORS 问题。
    """
    raw_cache_url = arxiv_raw_cache.build_pdf_download_url(
        arxiv_id,
        filename=filename,
        inline=content_disposition != "attachment",
    )
    if raw_cache_url and content_disposition == "attachment":
        return RedirectResponse(url=raw_cache_url, status_code=307)

    arxiv_pdf_url = raw_cache_url or f"https://arxiv.org/pdf/{arxiv_id}"
    client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
    forward_headers = {"User-Agent": "LaTeXTrans-Preview/1.0"}
    range_header = request.headers.get("range") if request else None
    if range_header:
        forward_headers["Range"] = range_header

    upstream_request = client.build_request("GET", arxiv_pdf_url, headers=forward_headers)
    upstream = await client.send(upstream_request, stream=True)

    if upstream.status_code not in (200, 206):
        await upstream.aclose()
        await client.aclose()
        logger.warning(
            "arXiv PDF proxy failed: id=%s status=%s url=%s",
            arxiv_id,
            upstream.status_code,
            arxiv_pdf_url,
        )
        raise HTTPException(
            status_code=upstream.status_code if upstream.status_code >= 400 else 502,
            detail=f"Failed to fetch source PDF from arXiv ({upstream.status_code})",
        )

    async def _stream() -> bytes:
        async for chunk in upstream.aiter_bytes():
            if chunk:
                yield chunk

    async def _close_stream() -> None:
        await upstream.aclose()
        await client.aclose()

    headers = {"Content-Disposition": f"{content_disposition}; filename=\"{filename}\""}
    for source_name, target_name in (
        ("content-length", "Content-Length"),
        ("accept-ranges", "Accept-Ranges"),
        ("content-range", "Content-Range"),
        ("etag", "ETag"),
        ("last-modified", "Last-Modified"),
        ("cache-control", "Cache-Control"),
    ):
        value = upstream.headers.get(source_name)
        if value:
            headers[target_name] = value

    return StreamingResponse(
        _stream(),
        status_code=upstream.status_code,
        media_type="application/pdf",
        headers=headers,
        background=BackgroundTask(_close_stream),
    )


async def _proxy_remote_pdf_asset(
    url: str,
    *,
    filename: str,
    request: Optional[Request] = None,
    content_disposition: str = "inline",
    media_type: str = "application/pdf",
) -> StreamingResponse:
    client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)
    forward_headers = {"User-Agent": "LaTeXTrans-Preview/1.0"}
    range_header = request.headers.get("range") if request else None
    if range_header:
        forward_headers["Range"] = range_header

    upstream_request = client.build_request("GET", url, headers=forward_headers)
    upstream = await client.send(upstream_request, stream=True)

    if upstream.status_code not in (200, 206):
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(
            status_code=upstream.status_code if upstream.status_code >= 400 else 502,
            detail=f"Failed to fetch remote PDF ({upstream.status_code})",
        )

    async def _stream():
        async for chunk in upstream.aiter_bytes():
            if chunk:
                yield chunk

    async def _close_stream() -> None:
        await upstream.aclose()
        await client.aclose()

    headers = {"Content-Disposition": f'{content_disposition}; filename="{filename}"'}
    for source_name, target_name in (
        ("content-length", "Content-Length"),
        ("accept-ranges", "Accept-Ranges"),
        ("content-range", "Content-Range"),
        ("etag", "ETag"),
        ("last-modified", "Last-Modified"),
        ("cache-control", "Cache-Control"),
    ):
        value = upstream.headers.get(source_name)
        if value:
            headers[target_name] = value

    return StreamingResponse(
        _stream(),
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type") or media_type,
        headers=headers,
        background=BackgroundTask(_close_stream),
    )


@router.get("/download/{task_id}/pdf")
async def download_pdf(task_id: str):
    """
    下载翻译后的 PDF 文件

    Args:
        task_id: 任务 ID

    Returns:
        作为下载附件的 PDF 文件

    Raises:
        HTTPException: 任务不存在或 PDF 不可用时抛出
    """
    logger.info(f"PDF download request for task: {task_id}")

    # 获取任务
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # 检查任务是否已完成
    if task["status"] not in [TaskStatus.COMPLETED.value, TaskStatus.COMPLETED_WITH_WARNINGS.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Translation not completed. Current status: {task['status']}"
        )

    if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
        signed_url = task_artifact_storage.build_task_output_download_url(
            task.get("output_path", ""),
            "translated_pdf",
            filename=f"translated_{task_id}.pdf",
            content_type="application/pdf",
            inline=False,
            expires_in=600,
        )
        if not signed_url:
            raise HTTPException(status_code=404, detail="Translated PDF not found")
        return RedirectResponse(url=signed_url, status_code=307)
    
    # 在输出目录中查找 PDF 文件
    output_dir = Path(task.get("output_path", ""))
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Output directory not found"
        )
    
    # 搜索 PDF 文件
    pdf_file = _find_translated_pdf(output_dir)

    if not pdf_file:
        raise HTTPException(
            status_code=404,
            detail="Translated PDF not found"
        )

    # 返回第一个找到的 PDF
    # 已通过辅助函数找到

    # 下载前验证 PDF 文件完整性
    if pdf_file.stat().st_size == 0:
        raise HTTPException(
            status_code=503,
            detail="PDF generation in progress, please retry"
        )
    
    # 验证 PDF 文件头
    try:
        with open(pdf_file, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                raise HTTPException(
                    status_code=503,
                    detail="PDF not ready, please retry"
                )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="PDF not accessible, please retry"
        )

    if not _validate_pdf_with_pdfinfo(pdf_file):
        raise HTTPException(
            status_code=503,
            detail="PDF structure validation failed, please retry"
        )
    
    logger.info(f"Returning PDF: {pdf_file}")
    
    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=f"translated_{task_id}.pdf"
    )


@router.get("/preview/{task_id}/pdf")
async def preview_pdf(task_id: str):
    """
    预览翻译后的 PDF（内联显示，供 iframe 使用）

    Args:
        task_id: 任务 ID

    Returns:
        用于内联显示的 PDF 文件

    Raises:
        HTTPException: 任务不存在或 PDF 不可用时抛出
    """
    logger.info(f"PDF preview request for task: {task_id}")
    
    task = task_manager.get_task(task_id)
    if task and task["status"] not in TERMINAL_SUCCESS_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Translation not completed. Current status: {task['status']}"
        )

    if task and str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
        signed_url = task_artifact_storage.build_task_output_download_url(
            task.get("output_path", ""),
            "translated_pdf",
            filename=f"preview_{task_id}.pdf",
            content_type="application/pdf",
            inline=True,
            expires_in=300,
        )
        if not signed_url:
            raise HTTPException(status_code=404, detail="Translated PDF not found")
        return await _proxy_remote_pdf_asset(
            signed_url,
            filename=f"preview_{task_id}.pdf",
            content_disposition="inline",
        )

    pdf_file: Optional[Path] = None
    for output_dir in _candidate_output_dirs(task_id, task):
        pdf_file = _find_translated_pdf(output_dir)
        if pdf_file:
            break

    if not pdf_file:
        pdf_file = _find_translated_pdf_in_community_library(task_id)

    if not pdf_file:
        raise HTTPException(
            status_code=404,
            detail="Translated PDF not found"
        )
    
    # 返回第一个找到的 PDF，设置 inline 内容处置以用于预览
    # 已通过辅助函数找到

    # 验证 PDF 文件完整性
    # 检查文件大小
    if pdf_file.stat().st_size == 0:
        raise HTTPException(
            status_code=503,
            detail="PDF generation in progress, please retry"
        )
    
    # 验证 PDF 文件头
    try:
        with open(pdf_file, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                raise HTTPException(
                    status_code=503,
                    detail="PDF not ready, please retry"
                )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="PDF not accessible, please retry"
        )

    if not _validate_pdf_with_pdfinfo(pdf_file):
        raise HTTPException(
            status_code=503,
            detail="PDF structure validation failed, please retry"
        )
    
    logger.info(f"Returning PDF for preview: {pdf_file}")
    
    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=\"preview_{task_id}.pdf\""
        }
    )


async def _serve_source_pdf(
    task_id: str,
    request: Request,
    *,
    content_disposition: str = "inline",
):
    """
    预览原始源 PDF（内联显示，供 iframe 使用）

    策略：
    1. 从本地社区库资源解析源 PDF（快速路径，无网络请求）
    2. 检查 arxiv_id 并在本地源不可用时代理 arXiv PDF
    3. 在任务源目录中查找已有的原始 PDF
    4. 回退方案：编译源 tex 生成源 PDF

    Args:
        task_id: 任务 ID

    Returns:
        用于内联显示的原始 PDF 文件，或重定向到 arxiv.org

    Raises:
        HTTPException: 任务不存在或源 PDF 不可用时抛出
    """
    import re

    logger.info(f"Source PDF preview request for task: {task_id}")

    task = task_manager.get_task(task_id) or {}

    # ArXiv ID 格式: YYMM.NNNNN 或 YYMM.NNNNNvN
    arxiv_pattern = re.compile(r'(\d{4}\.\d{4,5})(v\d+)?')

    # 策略 1：优先使用本地社区库源 PDF。
    inferred_arxiv_id = _extract_arxiv_id_from_text(task_id)
    arxiv_id = task.get("arxiv_id") or inferred_arxiv_id
    local_source_pdf = _find_source_pdf_in_community_library(task_id, preferred_arxiv_id=arxiv_id)
    if local_source_pdf:
        logger.info("Using cached community source PDF for task %s: %s", task_id, local_source_pdf)
        return FileResponse(
            path=str(local_source_pdf),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"{content_disposition}; filename=\"source_{task_id}.pdf\""
            },
        )

    # 策略 2：检查任务是否有存储的 arxiv_id，回退到 task-id 推断。
    if arxiv_id:
        match = arxiv_pattern.search(arxiv_id)
        if match:
            clean_id = match.group(1)
            logger.info(f"Proxying arxiv.org PDF for source preview: {clean_id}")
            return await _proxy_arxiv_pdf(
                clean_id,
                f"source_{clean_id}.pdf",
                request=request,
                content_disposition=content_disposition,
            )

    # 获取源码路径，回退到确定的 uploads 位置。
    source_path = str(task.get("source_path") or "").strip()
    source_candidates: list[Path] = []
    if source_path:
        source_candidates.append(Path(source_path))
        if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
            try:
                hydrated_source = task_artifact_storage.materialize_task_directory(
                    source_path,
                    destination=task_artifact_storage.resolve_local_task_path(source_path),
                    force=False,
                )
                source_candidates.insert(0, hydrated_source)
            except FileNotFoundError:
                logger.warning("Source path not found in object storage for preview: %s", source_path)
    source_candidates.append(settings.uploads_dir / task_id)
    source_dir = next((candidate for candidate in source_candidates if candidate.exists() and candidate.is_dir()), None)
    if source_dir is None:
        raise HTTPException(
            status_code=404,
            detail="Source path not available for this task"
        )
    
    # 策略 3：尝试从目录名或文件名中提取 arxiv ID
    extracted_arxiv_id = None
    
    # 检查目录名
    dir_match = arxiv_pattern.search(source_dir.name)
    if dir_match:
        extracted_arxiv_id = dir_match.group(1)
    
    # 检查父目录名
    if not extracted_arxiv_id:
        parent_match = arxiv_pattern.search(source_dir.parent.name)
        if parent_match:
            extracted_arxiv_id = parent_match.group(1)
    
    # 检查目录中的文件名
    if not extracted_arxiv_id:
        for file_path in source_dir.iterdir():
            file_match = arxiv_pattern.search(file_path.name)
            if file_match:
                extracted_arxiv_id = file_match.group(1)
                break
    
    if extracted_arxiv_id:
        logger.info(f"Extracted arXiv ID for source preview: {extracted_arxiv_id}")
        return await _proxy_arxiv_pdf(
            extracted_arxiv_id,
            f"source_{extracted_arxiv_id}.pdf",
            request=request,
            content_disposition=content_disposition,
        )
    
    # 策略 4：在源目录中查找已有的原始 PDF
    original_pdfs = _collect_original_pdf_candidates(source_dir)
    selected_source_pdf = _pick_best_source_pdf(
        source_dir,
        original_pdfs,
        preferred_stem=(extracted_arxiv_id or arxiv_id),
    )

    if selected_source_pdf:
        pdf_file = selected_source_pdf
        if pdf_file.exists() and pdf_file.stat().st_size > 0:
            logger.info(f"Found original PDF: {pdf_file}")
            return FileResponse(
                path=str(pdf_file),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"{content_disposition}; filename=\"source_{task_id}.pdf\""
                }
            )
    
    # 策略 5：回退方案 - 编译源 tex 生成源 PDF
    # 查找主 tex 文件
    tex_files = list(source_dir.rglob("*.tex"))
    if not tex_files:
        raise HTTPException(
            status_code=404,
            detail="No source files available for preview. Upload from arxiv for automatic source PDF."
        )
    
    # 查找主 tex 文件（寻找 main.tex 或包含 \documentclass 的文件）
    main_tex = None
    for tex_file in tex_files:
        if tex_file.name.lower() == "main.tex":
            main_tex = tex_file
            break
    
    if not main_tex:
        # 搜索包含 \documentclass 的文件
        for tex_file in tex_files:
            try:
                content = tex_file.read_text(encoding='utf-8', errors='ignore')
                if '\\documentclass' in content:
                    main_tex = tex_file
                    break
            except:
                pass
    
    if not main_tex:
        main_tex = tex_files[0]  # 回退到第一个 tex 文件
    
    # 检查是否已编译过源 PDF
    # 对共享上传使用固定文件名（不依赖 task_id）
    compiled_pdf_path = source_dir / "source_compiled.pdf"
    if compiled_pdf_path.exists() and compiled_pdf_path.stat().st_size > 0:
        if _validate_pdf_with_pdfinfo(compiled_pdf_path):
            logger.info(f"Using cached compiled source PDF: {compiled_pdf_path}")
            return await _serve_local_pdf_preview(
                file_path=compiled_pdf_path,
                filename=f"source_{task_id}.pdf",
                request=request,
                content_disposition=content_disposition,
            )
        logger.error("Cached source PDF failed validation, removing: %s", compiled_pdf_path)
        compiled_pdf_path.unlink(missing_ok=True)
    
    # 通过统一编译器执行器编译源 tex
    logger.info(f"Compiling source PDF from: {main_tex}")
    try:
        result = compile_with_intelligent_fallback(str(main_tex), str(source_dir))
        generated_pdf = Path(result.get("pdf_path") or "")
        if generated_pdf.is_file() and generated_pdf.stat().st_size > 0:
            # 重命名为标准文件名
            shutil.copy(str(generated_pdf), str(compiled_pdf_path))
            logger.info(f"Compiled and cached source PDF: {compiled_pdf_path}")
            return FileResponse(
                path=str(compiled_pdf_path),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"{content_disposition}; filename=\"source_{task_id}.pdf\""
                }
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to compile source PDF: {result.get('errors') or result.get('warnings') or 'unknown error'}"
            )
    except Exception as e:
        logger.error(f"Failed to compile source PDF: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to compile source PDF: {str(e)}"
        )


@router.get("/preview/{task_id}/source-pdf")
async def preview_source_pdf(task_id: str, request: Request):
    return await _serve_source_pdf(task_id, request, content_disposition="inline")


@router.get("/download/{task_id}/source")
async def download_source(task_id: str):
    """
    将翻译后的源文件打包为 .zip 下载

    Args:
        task_id: 任务 ID

    Returns:
        作为下载附件的 ZIP 压缩包

    Raises:
        HTTPException: 任务不存在或源文件不可用时抛出
    """
    logger.info(f"Source download request for task: {task_id}")
    
    # 获取任务
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # 检查任务是否已完成
    if task["status"] not in [TaskStatus.COMPLETED.value, TaskStatus.COMPLETED_WITH_WARNINGS.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Translation not completed. Current status: {task['status']}"
        )

    if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
        signed_url = task_artifact_storage.build_task_output_download_url(
            task.get("output_path", ""),
            "translated_source_archive",
            filename=f"translated_source_{task_id}.zip",
            content_type="application/zip",
            inline=False,
            expires_in=600,
        )
        if not signed_url:
            raise HTTPException(status_code=404, detail="Source archive not found")
        return RedirectResponse(url=signed_url, status_code=307)
    
    # 获取输出目录
    output_dir = Path(task.get("output_path", ""))
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Output directory not found"
        )
    
    # 创建临时 zip 文件
    temp_dir = Path(tempfile.gettempdir())
    zip_path = temp_dir / f"translated_source_{task_id}.zip"
    
    try:
        # 创建 zip 压缩包
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加所有 .tex 文件及相关文件
            for file_path in output_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix in [".tex", ".bib", ".cls", ".sty", ".bst"]:
                    arcname = file_path.relative_to(output_dir)
                    zipf.write(file_path, arcname)
                    logger.debug(f"Added to zip: {arcname}")
        
        logger.info(f"Created zip archive: {zip_path}")
        
        # 返回 zip 文件
        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=f"translated_source_{task_id}.zip",
            # 发送后清理临时文件
            background=None
        )
    
    except Exception as e:
        logger.error(f"Failed to create zip archive: {e}")
        # 错误时清理临时文件
        if zip_path.exists():
            zip_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create source archive: {str(e)}"
        )


@router.get("/download/{task_id}/logs")
async def download_logs(task_id: str):
    """
    下载编译日志文件

    Args:
        task_id: 任务 ID

    Returns:
        作为下载附件的日志文件

    Raises:
        HTTPException: 任务不存在或日志不可用时抛出
    """
    logger.info(f"Logs download request for task: {task_id}")
    
    # 获取任务
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )

    if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
        signed_url = task_artifact_storage.build_task_output_download_url(
            task.get("output_path", ""),
            "logs",
            filename=f"compilation_log_{task_id}.log",
            content_type="text/plain",
            inline=False,
            expires_in=600,
        )
        if not signed_url:
            raise HTTPException(status_code=404, detail="Log files not found")
        return RedirectResponse(url=signed_url, status_code=307)
    
    # 获取输出目录
    output_dir = Path(task.get("output_path", ""))
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Output directory not found"
        )
    
    # 搜索 .log 文件
    log_files = list(output_dir.rglob("*.log"))
    if not log_files:
        raise HTTPException(
            status_code=404,
            detail="Log files not found"
        )
    
    # 返回主日志文件
    log_file = log_files[0]
    logger.info(f"Returning log: {log_file}")
    
    return FileResponse(
        path=str(log_file),
        media_type="text/plain",
        filename=f"compilation_log_{task_id}.log"
    )


@router.get("/download/{task_id}/terminology")
async def download_terminology(task_id: str):
    """
    下载术语表 CSV 文件

    Args:
        task_id: 任务 ID

    Returns:
        作为下载附件的 CSV 文件

    Raises:
        HTTPException: 任务不存在或术语表不可用时抛出
    """
    logger.info(f"Terminology table download request for task: {task_id}")
    
    # 获取任务
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # 检查任务是否已完成
    if task["status"] not in [TaskStatus.COMPLETED.value, TaskStatus.COMPLETED_WITH_WARNINGS.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Translation not completed. Current status: {task['status']}"
        )

    if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
        signed_url = task_artifact_storage.build_task_output_download_url(
            task.get("output_path", ""),
            "terminology_csv",
            filename=f"terminology_{task_id}.csv",
            content_type="text/csv",
            inline=False,
            expires_in=600,
        )
        if not signed_url:
            raise HTTPException(
                status_code=404,
                detail="Terminology table not found. Make sure 'Generate Terminology Table' was enabled during translation.",
            )
        return RedirectResponse(url=signed_url, status_code=307)
    
    # 获取输出目录
    output_dir = Path(task.get("output_path", ""))
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Output directory not found"
        )
    
    # 查找术语表 CSV 文件
    terminology_file = output_dir / "terminology_table.csv"
    
    # 同时在子目录中查找
    if not terminology_file.exists():
        found_files = list(output_dir.rglob("terminology_table.csv"))
        if found_files:
            terminology_file = found_files[0]
        else:
            raise HTTPException(
                status_code=404,
                detail="Terminology table not found. Make sure 'Generate Terminology Table' was enabled during translation."
            )
    
    logger.info(f"Returning terminology table: {terminology_file}")
    
    return FileResponse(
        path=str(terminology_file),
        media_type="text/csv",
        filename=f"terminology_{task_id}.csv"
    )
