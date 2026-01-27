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
    logger.info(f"Returning PDF: {pdf_file}")
    
    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=f"translated_{task_id}.pdf"
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
