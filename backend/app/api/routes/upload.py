"""
File Upload API Routes

Provides endpoints for uploading .zip, .tar.gz, .rar or .tex files.
Supports automatic extraction and LaTeX project validation.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging
import shutil
import zipfile
import tarfile
from pathlib import Path

from backend.app.services.task_manager import get_task_manager
from backend.app.services.latex_validator import validate_latex_directory
from backend.app.core.config import get_settings, TaskStatus
from backend.app.models.config_models import LatexValidation

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()


class LatexValidationResponse(BaseModel):
    """LaTeX validation result in response"""
    is_valid: bool
    main_file: Optional[str] = None
    tex_files: List[str] = []
    warnings: List[str] = []
    errors: List[str] = []


class UploadResponse(BaseModel):
    """File upload response with LaTeX validation"""
    task_id: str
    status: str
    message: str
    source_path: str
    latex_validation: Optional[LatexValidationResponse] = None


def extract_rar(file_path: Path, extract_dir: Path) -> None:
    """
    Extract RAR archive using rarfile library.
    
    Args:
        file_path: Path to the RAR file
        extract_dir: Directory to extract to
    
    Raises:
        ImportError: If rarfile is not installed
        Exception: If extraction fails
    """
    try:
        import rarfile
        with rarfile.RarFile(file_path, 'r') as rar_ref:
            rar_ref.extractall(extract_dir)
    except ImportError:
        # Fallback: try using unrar command line tool
        import subprocess
        try:
            result = subprocess.run(
                ['unrar', 'x', '-o+', str(file_path), str(extract_dir)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"unrar failed: {result.stderr}")
        except FileNotFoundError:
            raise ImportError(
                "RAR extraction requires 'rarfile' package or 'unrar' command line tool. "
                "Install with: pip install rarfile OR install unrar system package."
            )


def get_file_extension(filename: str) -> str:
    """
    Get file extension, handling compound extensions like .tar.gz
    
    Args:
        filename: Original filename
    
    Returns:
        File extension (e.g., ".zip", ".tar.gz", ".rar")
    """
    name = filename.lower()
    if name.endswith('.tar.gz'):
        return '.tar.gz'
    if name.endswith('.tgz'):
        return '.tgz'
    return Path(filename).suffix.lower()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload .zip, .tar.gz, .rar or .tex file
    
    Supports the following formats:
    - .zip - Standard ZIP compression
    - .tar.gz / .tgz - TAR+GZIP compression (common for arXiv)
    - .tar - TAR archive
    - .rar - RAR compression
    - .tex - Single LaTeX file
    
    After extraction, the directory is validated as a LaTeX project.
    
    Args:
        file: Uploaded file
    
    Returns:
        Task information with upload status and LaTeX validation
    
    Raises:
        HTTPException: If file type is invalid or upload fails
    """
    # Get file extension (handle compound extensions)
    file_ext = get_file_extension(file.filename)
    
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，支持的格式: {', '.join(sorted(settings.allowed_extensions))}"
        )
    
    logger.info(f"Uploading file: {file.filename} ({file_ext})")
    
    # Create task with folder_upload source type for archives
    source_type = "folder_upload" if file_ext != ".tex" else "upload"
    task_id = task_manager.create_task(source_type=source_type)
    
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
        
        # Extract based on file type
        if file_ext == ".zip":
            logger.info(f"Extracting ZIP file: {file_path}")
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(task_dir)
            logger.info("ZIP extraction complete")
        
        elif file_ext in [".tar", ".tar.gz", ".tgz"]:
            logger.info(f"Extracting TAR file: {file_path}")
            with tarfile.open(file_path, 'r:*') as tar_ref:
                tar_ref.extractall(task_dir)
            logger.info("TAR extraction complete")
        
        elif file_ext == ".rar":
            logger.info(f"Extracting RAR file: {file_path}")
            extract_rar(file_path, task_dir)
            logger.info("RAR extraction complete")
        
        # Validate LaTeX directory
        logger.info(f"Validating LaTeX directory: {task_dir}")
        validation = validate_latex_directory(task_dir)
        
        validation_response = LatexValidationResponse(
            is_valid=validation.is_valid,
            main_file=validation.main_file,
            tex_files=validation.tex_files,
            warnings=validation.warnings,
            errors=validation.errors
        )
        
        # Update task with validation results
        if validation.is_valid:
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.PENDING.value,
                progress=100,
                message=f"File {file.filename} uploaded and validated successfully",
                source_path=str(task_dir),
                source_available=True,
                latex_validation=validation.model_dump()
            )
            logger.info(f"Upload successful: {task_id}, main_file={validation.main_file}")
            
            return UploadResponse(
                task_id=task_id,
                status="success",
                message=f"File {file.filename} uploaded successfully. Main file: {validation.main_file}",
                source_path=str(task_dir),
                latex_validation=validation_response
            )
        else:
            # Not a valid LaTeX project
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.FAILED.value,
                error="; ".join(validation.errors),
                latex_validation=validation.model_dump()
            )
            
            raise HTTPException(
                status_code=400,
                detail='; '.join(validation.errors)
            )
    
    except zipfile.BadZipFile:
        logger.error(f"Invalid zip file: {file.filename}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error="ZIP 文件损坏或无效"
        )
        raise HTTPException(
            status_code=400,
            detail="ZIP 文件损坏或无效"
        )
    
    except ImportError as e:
        err_msg = "缺少 RAR 解压工具，请安装 rarfile 库或 unrar 命令行工具"
        logger.error(f"RAR extraction failed - missing dependency: {e}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=err_msg
        )
        raise HTTPException(
            status_code=500,
            detail=err_msg
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        raise
    
    except Exception as e:
        err_msg = f"文件上传失败: {str(e)}"
        logger.error(f"Upload failed: {e}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=err_msg
        )
        raise HTTPException(
            status_code=500,
            detail=err_msg
        )
