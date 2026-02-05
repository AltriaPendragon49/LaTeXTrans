"""
Download API Routes

Provides endpoints for downloading translated PDFs and source files.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import logging
from pathlib import Path
import zipfile
import tempfile
import shutil

from backend.app.services.task_manager import get_task_manager
from backend.app.core.config import get_settings, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()


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
    
    # Find PDF file in output directory
    output_dir = Path(task.get("output_path", ""))
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Output directory not found"
        )
    
    # Search for PDF files
    pdf_files = list(output_dir.rglob("*_translated.pdf"))
    if not pdf_files:
        # Try finding any PDF
        pdf_files = list(output_dir.rglob("*.pdf"))
    
    if not pdf_files:
        raise HTTPException(
            status_code=404,
            detail="Translated PDF not found"
        )
    
    # Return the first PDF found
    pdf_file = pdf_files[0]
    
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
    
    # Find PDF file in output directory
    output_dir = Path(task.get("output_path", ""))
    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Output directory not found"
        )
    
    # Search for PDF files
    pdf_files = list(output_dir.rglob("*_translated.pdf"))
    if not pdf_files:
        # Try finding any PDF
        pdf_files = list(output_dir.rglob("*.pdf"))
    
    if not pdf_files:
        raise HTTPException(
            status_code=404,
            detail="Translated PDF not found"
        )
    
    # Return the first PDF found with inline content disposition for preview
    pdf_file = pdf_files[0]
    
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
    
    logger.info(f"Returning PDF for preview: {pdf_file}")
    
    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=\"preview_{task_id}.pdf\""
        }
    )


@router.get("/preview/{task_id}/source-pdf")
async def preview_source_pdf(task_id: str):
    """
    Preview original source PDF (inline display for iframe)
    
    Strategy:
    1. Check if task has an associated arxiv_id -> redirect to arxiv.org
    2. Try to extract arxiv ID from directory/file names -> redirect to arxiv.org
    3. Look for existing original PDF in source directory (not translated)
    4. Fallback: compile source tex to generate source PDF
    
    Args:
        task_id: Task ID
    
    Returns:
        Original PDF file for inline display, or redirect to arxiv.org
    
    Raises:
        HTTPException: If task not found or source PDF not available
    """
    import re
    import subprocess
    from fastapi.responses import RedirectResponse
    
    logger.info(f"Source PDF preview request for task: {task_id}")
    
    # Get task
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # ArXiv ID pattern: YYMM.NNNNN or YYMM.NNNNNvN
    arxiv_pattern = re.compile(r'(\d{4}\.\d{4,5})(v\d+)?')
    
    # Strategy 1: Check if task has arxiv_id stored
    arxiv_id = task.get("arxiv_id")
    if arxiv_id:
        # Extract just the ID part (remove any version suffix for PDF URL)
        match = arxiv_pattern.search(arxiv_id)
        if match:
            clean_id = match.group(1)
            arxiv_pdf_url = f"https://arxiv.org/pdf/{clean_id}.pdf"
            logger.info(f"Redirecting to arxiv.org PDF: {arxiv_pdf_url}")
            return RedirectResponse(url=arxiv_pdf_url, status_code=302)
    
    # Get source path
    source_path = task.get("source_path")
    if not source_path:
        raise HTTPException(
            status_code=404,
            detail="Source path not available for this task"
        )
    
    source_dir = Path(source_path)
    if not source_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Source directory not found"
        )
    
    # Strategy 2: Try to extract arxiv ID from directory name or file names
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
        arxiv_pdf_url = f"https://arxiv.org/pdf/{extracted_arxiv_id}.pdf"
        logger.info(f"Extracted arxiv ID {extracted_arxiv_id}, redirecting to: {arxiv_pdf_url}")
        return RedirectResponse(url=arxiv_pdf_url, status_code=302)
    
    # Strategy 3: Look for existing original PDF in source directory
    all_pdfs = list(source_dir.rglob("*.pdf"))
    
    # Filter to find original PDF (not translated, not zh prefixed)
    original_pdfs = [
        pdf for pdf in all_pdfs 
        if not pdf.name.startswith("zh_") 
        and "_translated" not in pdf.name
        and "zh-" not in pdf.name
        and not pdf.name.startswith("source_compiled_")  # Our compiled PDFs
    ]
    
    if original_pdfs:
        pdf_file = original_pdfs[0]
        if pdf_file.exists() and pdf_file.stat().st_size > 0:
            logger.info(f"Found original PDF: {pdf_file}")
            return FileResponse(
                path=str(pdf_file),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename=\"source_{task_id}.pdf\""
                }
            )
    
    # Strategy 4: Fallback - compile source tex to generate source PDF
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
    compiled_pdf_path = source_dir / f"source_compiled_{task_id}.pdf"
    if compiled_pdf_path.exists() and compiled_pdf_path.stat().st_size > 0:
        logger.info(f"Using cached compiled source PDF: {compiled_pdf_path}")
        return FileResponse(
            path=str(compiled_pdf_path),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=\"source_{task_id}.pdf\""
            }
        )
    
    # Compile the source tex
    logger.info(f"Compiling source PDF from: {main_tex}")
    try:
        # Use pdflatex for compilation (2 passes for references)
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(source_dir), str(main_tex)],
                cwd=str(source_dir),
                capture_output=True,
                timeout=120
            )
        
        # Find generated PDF
        expected_pdf = main_tex.with_suffix(".pdf")
        if expected_pdf.exists() and expected_pdf.stat().st_size > 0:
            # Rename to our standard name
            shutil.copy(str(expected_pdf), str(compiled_pdf_path))
            logger.info(f"Compiled and cached source PDF: {compiled_pdf_path}")
            return FileResponse(
                path=str(compiled_pdf_path),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename=\"source_{task_id}.pdf\""
                }
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="Failed to compile source PDF. Try using arxiv ID for automatic source PDF."
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=503,
            detail="Source PDF compilation timed out"
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="LaTeX compiler not available. Use arxiv ID for automatic source PDF."
        )
    except Exception as e:
        logger.error(f"Failed to compile source PDF: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to compile source PDF: {str(e)}"
        )


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
