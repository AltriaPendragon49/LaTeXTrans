"""
Download API Routes

Provides endpoints for downloading translated PDFs and source files.
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
    """Hard PDF structure gate using pdfinfo."""
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
    Locate translated PDF with strict rules to avoid selecting copied source PDFs.

    Priority:
    1. task_log.json events: compilation_completed / compilation_completed_with_warnings
       - Support both output root and its direct child directories.
    2. Root-level *_translated.pdf
    3. Convention path: output_dir/<subdir>/<subdir>.pdf (direct child only)
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

    # 2) Explicit translated naming in root.
    pdf_files = list(output_dir.glob("*_translated.pdf"))
    if pdf_files:
        return pdf_files[0]

    # 3) Strict convention: direct child folder with same-name PDF.
    for child in output_dir.iterdir():
        if not child.is_dir():
            continue
        expected_pdf = child / f"{child.name}.pdf"
        if expected_pdf.is_file():
            return expected_pdf

    return None


def _candidate_output_dirs(task_id: str, task: Optional[dict]) -> list[Path]:
    """Return output directory candidates in descending confidence order."""
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
    """Best-effort fallback when task outputs are unavailable but assets exist."""
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
    Resolve source PDF from community library assets to avoid unnecessary network fetches.
    Prioritizes local file resolution over remote fetches.
    """
    root = settings.community_papers_dir
    if not root.exists():
        return None

    # Strategy 1 (Highest Priority): Global search by ArXiv ID in ALL community collections.
    # This ensures that if ANY community paper has the original source PDF, we use it.
    preferred_id = str(preferred_arxiv_id or "").strip()
    if preferred_id:
        for paper_dir in sorted(root.iterdir()):
            if not paper_dir.is_dir():
                continue
            
            # Check source directory
            source_dir = paper_dir / "source"
            if source_dir.exists() and source_dir.is_dir():
                # Direct match for <arxiv_id>.pdf
                expected = f"{preferred_id}.pdf"
                for candidate in source_dir.rglob(expected):
                    if candidate.is_file() and candidate.stat().st_size > 0:
                        return candidate
                
                # Heuristic match: If this paper_dir belongs to this arxiv_id, pick its best PDF.
                # Many papers are stored as directories named after their arxiv_id.
                if preferred_id in paper_dir.name:
                    candidates = _collect_original_pdf_candidates(source_dir)
                    best = _pick_best_source_pdf(source_dir, candidates, preferred_id)
                    if best:
                        return best

    # Strategy 2: Task-correlated resolution (fallback)
    # Finding papers that were translated as part of the same task cluster.
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
    Stream arXiv PDF through backend to avoid frontend CORS issues.
    """
    arxiv_pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
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


async def _proxy_remote_asset(
    url: str,
    *,
    filename: str,
    media_type: str,
    request: Optional[Request] = None,
) -> StreamingResponse:
    client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
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
            detail=f"Failed to fetch remote asset ({upstream.status_code})",
        )

    async def _stream():
        async for chunk in upstream.aiter_bytes():
            if chunk:
                yield chunk

    async def _close_stream() -> None:
        await upstream.aclose()
        await client.aclose()

    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
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
        media_type=media_type,
        headers=headers,
        background=BackgroundTask(_close_stream),
    )


@router.get("/download/{task_id}/pdf")
async def download_pdf(task_id: str):
    """
    Download translated PDF
    
    Args:
        task_id: Task ID
    
    Returns:
        PDF file as download attachment
    
    Raises:
        HTTPException: If task not found or PDF not available
    """
    logger.info(f"PDF download request for task: {task_id}")
    
    # Get task
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # Check if task is completed
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
    
    # Find PDF file in output directory
    output_dir = Path(task.get("output_path", ""))
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Output directory not found"
        )
    
    # Search for PDF files
    pdf_file = _find_translated_pdf(output_dir)
    
    if not pdf_file:
        raise HTTPException(
            status_code=404,
            detail="Translated PDF not found"
        )
    
    # Return the first PDF found
    # Already found via helper
    
    # Verify PDF file integrity before download
    if pdf_file.stat().st_size == 0:
        raise HTTPException(
            status_code=503,
            detail="PDF generation in progress, please retry"
        )
    
    # Verify PDF header
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
    Preview translated PDF (inline display for iframe)
    
    Args:
        task_id: Task ID
    
    Returns:
        PDF file for inline display
    
    Raises:
        HTTPException: If task not found or PDF not available
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
        return await _proxy_remote_asset(
            signed_url,
            filename=f"preview_{task_id}.pdf",
            media_type="application/pdf",
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
    
    # Return the first PDF found with inline content disposition for preview
    # Already found via helper
    
    # Verify PDF file integrity
    # Check file size
    if pdf_file.stat().st_size == 0:
        raise HTTPException(
            status_code=503,
            detail="PDF generation in progress, please retry"
        )
    
    # Verify PDF header
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
    Preview original source PDF (inline display for iframe)
    
    Strategy:
    1. Resolve source PDF from local community library assets (fast path, no network)
    2. Check arxiv_id and proxy arXiv PDF when local source is unavailable
    3. Look for existing original PDF in task source directory
    4. Fallback: compile source tex to generate source PDF
    
    Args:
        task_id: Task ID
    
    Returns:
        Original PDF file for inline display, or redirect to arxiv.org
    
    Raises:
        HTTPException: If task not found or source PDF not available
    """
    import re

    logger.info(f"Source PDF preview request for task: {task_id}")

    task = task_manager.get_task(task_id) or {}

    # ArXiv ID pattern: YYMM.NNNNN or YYMM.NNNNNvN
    arxiv_pattern = re.compile(r'(\d{4}\.\d{4,5})(v\d+)?')

    # Strategy 1: local community-library source PDF first.
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

    # Strategy 2: Check if task has arxiv_id stored, fallback to task-id inference.
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

    # Get source path with fallback to deterministic uploads location.
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
    
    # Strategy 3: Try to extract arxiv ID from directory name or file names
    extracted_arxiv_id = None
    
    # Check directory name
    dir_match = arxiv_pattern.search(source_dir.name)
    if dir_match:
        extracted_arxiv_id = dir_match.group(1)
    
    # Check parent directory name
    if not extracted_arxiv_id:
        parent_match = arxiv_pattern.search(source_dir.parent.name)
        if parent_match:
            extracted_arxiv_id = parent_match.group(1)
    
    # Check file names in directory
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
    
    # Strategy 4: Look for existing original PDF in source directory
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
    
    # Strategy 5: Fallback - compile source tex to generate source PDF
    # Look for main tex file
    tex_files = list(source_dir.rglob("*.tex"))
    if not tex_files:
        raise HTTPException(
            status_code=404,
            detail="No source files available for preview. Upload from arxiv for automatic source PDF."
        )
    
    # Find main tex file (look for main.tex or file with \documentclass)
    main_tex = None
    for tex_file in tex_files:
        if tex_file.name.lower() == "main.tex":
            main_tex = tex_file
            break
    
    if not main_tex:
        # Search for file with \documentclass
        for tex_file in tex_files:
            try:
                content = tex_file.read_text(encoding='utf-8', errors='ignore')
                if '\\documentclass' in content:
                    main_tex = tex_file
                    break
            except:
                pass
    
    if not main_tex:
        main_tex = tex_files[0]  # Fallback to first tex file
    
    # Check if we already compiled a source PDF
    # Use fixed name for shared uploads (no task_id dependency)
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
    
    # Compile the source tex via unified compiler executor
    logger.info(f"Compiling source PDF from: {main_tex}")
    try:
        result = compile_with_intelligent_fallback(str(main_tex), str(source_dir))
        generated_pdf = Path(result.get("pdf_path") or "")
        if generated_pdf.is_file() and generated_pdf.stat().st_size > 0:
            # Rename to our standard name
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
    Download translated source files as .zip
    
    Args:
        task_id: Task ID
    
    Returns:
        ZIP archive as download attachment
    
    Raises:
        HTTPException: If task not found or source not available
    """
    logger.info(f"Source download request for task: {task_id}")
    
    # Get task
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # Check if task is completed
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
    
    # Get output directory
    output_dir = Path(task.get("output_path", ""))
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Output directory not found"
        )
    
    # Create temporary zip file
    temp_dir = Path(tempfile.gettempdir())
    zip_path = temp_dir / f"translated_source_{task_id}.zip"
    
    try:
        # Create zip archive
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all .tex files and related files
            for file_path in output_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix in [".tex", ".bib", ".cls", ".sty", ".bst"]:
                    arcname = file_path.relative_to(output_dir)
                    zipf.write(file_path, arcname)
                    logger.debug(f"Added to zip: {arcname}")
        
        logger.info(f"Created zip archive: {zip_path}")
        
        # Return zip file
        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=f"translated_source_{task_id}.zip",
            # Clean up temp file after sending
            background=None
        )
    
    except Exception as e:
        logger.error(f"Failed to create zip archive: {e}")
        # Clean up temp file on error
        if zip_path.exists():
            zip_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create source archive: {str(e)}"
        )


@router.get("/download/{task_id}/logs")
async def download_logs(task_id: str):
    """
    Download compilation logs
    
    Args:
        task_id: Task ID
    
    Returns:
        Log file as download attachment
    
    Raises:
        HTTPException: If task not found or logs not available
    """
    logger.info(f"Logs download request for task: {task_id}")
    
    # Get task
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
    
    # Get output directory
    output_dir = Path(task.get("output_path", ""))
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Output directory not found"
        )
    
    # Search for .log files
    log_files = list(output_dir.rglob("*.log"))
    if not log_files:
        raise HTTPException(
            status_code=404,
            detail="Log files not found"
        )
    
    # Return the main log file
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
    Download terminology table CSV
    
    Args:
        task_id: Task ID
    
    Returns:
        CSV file as download attachment
    
    Raises:
        HTTPException: If task not found or terminology table not available
    """
    logger.info(f"Terminology table download request for task: {task_id}")
    
    # Get task
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # Check if task is completed
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
    
    # Get output directory
    output_dir = Path(task.get("output_path", ""))
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Output directory not found"
        )
    
    # Look for terminology table CSV
    terminology_file = output_dir / "terminology_table.csv"
    
    # Try to find it in subdirectories as well
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
