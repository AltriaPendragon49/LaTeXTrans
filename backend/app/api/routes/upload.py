"""
File Upload API Routes

Provides endpoints for uploading .zip or .tex files.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import logging
import shutil
import zipfile
from pathlib import Path

from backend.app.services.task_manager import get_task_manager
from backend.app.core.config import get_settings, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()


class UploadResponse(BaseModel):
    """File upload response"""
    task_id: str
    status: str
    message: str
    source_path: str


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload .zip or .tex file
    
    Args:
        file: Uploaded file (.zip, .tex, .tar, .tar.gz)
    
    Returns:
        Task information with upload status
    
    Raises:
        HTTPException: If file type is invalid or upload fails
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file_ext}. Allowed types: {', '.join(settings.allowed_extensions)}"
        )
    
    logger.info(f"Uploading file: {file.filename} ({file_ext})")
    
    # Create task
    task_id = task_manager.create_task(source_type="upload")
    
    # Create task directory
    task_dir = settings.uploads_dir / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Update task status
    task_manager.update_task(
        task_id=task_id,
        status=TaskStatus.PROCESSING.value,
        message=f"Uploading {file.filename}..."
    )
    
    try:
        # Save uploaded file
        file_path = task_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved to: {file_path}")
        
        # Extract if compressed
        if file_ext == ".zip":
            logger.info(f"Extracting zip file: {file_path}")
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(task_dir)
            logger.info(f"Extraction complete")
        
        elif file_ext in [".tar", ".tar.gz"]:
            logger.info(f"Extracting tar file: {file_path}")
            import tarfile
            with tarfile.open(file_path, 'r:*') as tar_ref:
                tar_ref.extractall(task_dir)
            logger.info(f"Extraction complete")
        
        # Update task as ready for translation
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PENDING.value,
            progress=100,
            message=f"File {file.filename} uploaded successfully",
            source_path=str(task_dir),
            source_available=True
        )
        
        logger.info(f"Upload successful: {task_id}")
        
        return UploadResponse(
            task_id=task_id,
            status="success",
            message=f"File {file.filename} uploaded successfully",
            source_path=str(task_dir)
        )
    
    except zipfile.BadZipFile:
        logger.error(f"Invalid zip file: {file.filename}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error="Invalid or corrupted zip file"
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted zip file"
        )
    
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )
