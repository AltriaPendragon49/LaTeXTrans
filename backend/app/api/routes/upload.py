"""
File Upload API Routes

Provides endpoints for uploading .zip, .tar.gz, .rar or .tex files.
Supports automatic extraction and LaTeX project validation.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Any, Optional, List
import json
import logging
import shutil
import zipfile
import tarfile
import re
import uuid
from pathlib import Path

from backend.app.core.auth import optional_current_user, require_current_user, resolve_current_user_id
from backend.app.services.task_manager import get_task_manager
from backend.app.services import task_artifact_storage
from backend.app.services.latex_validator import validate_latex_directory
from backend.app.core.config import get_settings, TaskStatus
from backend.app.models.config_models import AdvancedConfig, LatexValidation
from backend.app.api.routes.translate import BatchTranslateResponse

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()

# Allow missing Authorization header (guest mode)
security = HTTPBearer(auto_error=False)
required_security = HTTPBearer(auto_error=True)


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


def _parse_advanced_config_form(raw_value: Optional[str]) -> AdvancedConfig:
    if not raw_value or not str(raw_value).strip():
        return AdvancedConfig()

    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="advanced_config must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="advanced_config must be a JSON object")

    try:
        return AdvancedConfig(**payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid advanced_config: {exc}") from exc


def _safe_upload_filename(filename: Optional[str]) -> str:
    safe_name = Path(filename or "upload").name.strip()
    return safe_name or "upload"


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


def get_file_extension(filename: Optional[str]) -> str:
    """
    Get file extension, handling compound extensions like .tar.gz
    
    Args:
        filename: Original filename
    
    Returns:
        File extension (e.g., ".zip", ".tar.gz", ".rar")
    """
    filename = filename or ""
    name = filename.lower()
    if name.endswith('.tar.gz'):
        return '.tar.gz'
    if name.endswith('.tgz'):
        return '.tgz'
    return Path(filename).suffix.lower()


@router.post("/upload/batch-translate", response_model=BatchTranslateResponse)
async def batch_upload_translate(
    files: List[UploadFile] = File(...),
    source_language: str = Form("en"),
    target_language: str = Form("ch"),
    advanced_config: Optional[str] = Form(None),
    credentials: HTTPAuthorizationCredentials = Depends(required_security),
    current_user: dict[str, Any] = Depends(require_current_user),
):
    """
    Upload multiple source packages and start translations with one atomic
    daily-quota reservation before any upload task is created.
    """
    from backend.app.api.routes import translate as translate_route

    user_id = resolve_current_user_id(current_user, credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required for batch upload translation")
    user_roles = current_user.get("roles") if isinstance(current_user, dict) else None

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 9:
        raise HTTPException(
            status_code=400,
            detail=f"Batch limit exceeded: maximum 9 files per request, got {len(files)}",
        )

    invalid_files = [
        f"{file.filename}: {get_file_extension(file.filename)}"
        for file in files
        if get_file_extension(file.filename) not in settings.allowed_extensions
    ]
    if invalid_files:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type in batch: {', '.join(invalid_files)}",
        )

    parsed_advanced_config = _parse_advanced_config_form(advanced_config)

    tq = translate_route.get_task_queue()
    if tq:
        user_active = tq.get_user_active_count(user_id)
        remaining = settings.max_user_active_tasks - user_active
        if remaining <= 0:
            raise HTTPException(
                status_code=429,
                detail=f"Quota exceeded: you have {user_active}/{settings.max_user_active_tasks} active tasks. Please wait for existing tasks to complete.",
            )
        if len(files) > remaining:
            raise HTTPException(
                status_code=429,
                detail=f"Quota exceeded: you can submit at most {remaining} more tasks (currently {user_active}/{settings.max_user_active_tasks} active).",
            )

    quota_service = translate_route.get_translation_quota_service()
    reserved_count = len(files)
    try:
        quota_service.reserve_latex_translation(
            user_id=user_id,
            requested_count=reserved_count,
            roles=user_roles,
        )
    except translate_route.DailyQuotaExceededError as exc:
        raise HTTPException(status_code=429, detail=translate_route._quota_exceeded_detail(exc)) from exc

    task_ids: list[str] = []
    errors: list[str] = []
    accepted_count = 0
    batch_id = str(uuid.uuid4())

    for file in files:
        filename = _safe_upload_filename(file.filename)
        try:
            if hasattr(file.file, "seek"):
                file.file.seek(0)

            upload_response = await upload_file(
                file=file,
                credentials=credentials,
                current_user=current_user,
            )
            translate_request = translate_route.TranslateRequest(
                source_language=source_language,
                target_language=target_language,
                advanced_config=parsed_advanced_config,
            )
            await translate_route._start_translation_for_task(
                task_id=upload_response.task_id,
                request=translate_request,
                credentials=credentials,
                current_user=current_user,
                reserve_daily_quota=False,
            )
            task_ids.append(upload_response.task_id)
            accepted_count += 1
        except HTTPException as exc:
            errors.append(f"{filename}: {exc.detail}")
        except Exception as exc:
            logger.error("[BatchUploadTranslate] Failed to process %s: %s", filename, exc, exc_info=True)
            errors.append(f"{filename}: {exc}")

    unaccepted_count = max(reserved_count - accepted_count, 0)
    if unaccepted_count:
        try:
            quota_service.release_latex_translation(user_id=user_id, count=unaccepted_count, roles=user_roles)
        except Exception:
            logger.warning("Failed to release daily quota for unaccepted batch uploads", exc_info=True)

    if not task_ids:
        raise HTTPException(
            status_code=400,
            detail=f"All batch upload translations failed: {'; '.join(errors)}",
        )

    return BatchTranslateResponse(
        batch_id=batch_id,
        task_ids=task_ids,
        message=f"Batch upload translation started: {len(task_ids)} tasks queued" + (
            f" ({len(errors)} failed)" if errors else ""
        ),
        queued_count=len(task_ids),
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    current_user: Optional[dict] = Depends(optional_current_user),
):
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
    
    user_id = resolve_current_user_id(current_user, credentials)
    if user_id:
        logger.info(f"Authenticated user uploading file: {user_id}")
    
    # Create task with folder_upload source type for archives
    source_type = "folder_upload" if file_ext != ".tex" else "upload"
    task_id = task_manager.create_task(
        source_type=source_type, 
        user_id=user_id,
        persist_to_db=False  # 延迟到翻译时才持久化
    )
    
    # Create task directory
    task_dir = settings.uploads_dir / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Update task status
    task_manager.update_task(
        task_id=task_id,
        status=TaskStatus.PROCESSING.value,
        message=f"Uploading {file.filename}...",
        user_id=user_id
    )
    
    # 标记上传是否成功,用于失败时清理临时目录
    upload_success = False
    
    try:
        # Save uploaded file
        file_path = task_dir / _safe_upload_filename(file.filename)
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
            try:
                # Use 'r:*' to auto-detect compression format
                with tarfile.open(file_path, mode='r:*') as tar_ref:
                    # Filter for security - avoid absolute paths and path traversal
                    for member in tar_ref.getmembers():
                        if member.name.startswith('/') or '..' in member.name:
                            logger.warning(f"Skipping potentially unsafe path: {member.name}")
                            continue
                        tar_ref.extract(member, path=task_dir)
                logger.info("TAR extraction complete")
            except tarfile.ReadError as e:
                logger.error(f"Invalid tar file format: {e}")
                raise ValueError(f"TAR 文件格式无效或已损坏: {e}")
            except tarfile.TarError as e:
                logger.error(f"TAR extraction error: {e}")
                raise ValueError(f"TAR 文件解压失败: {e}")
        
        elif file_ext == ".rar":
            logger.info(f"Extracting RAR file: {file_path}")
            extract_rar(file_path, task_dir)
            logger.info("RAR extraction complete")
        
        # Try to infer arxiv_id and deduplicate
        arxiv_pattern = re.compile(r'(\d{4}\.\d{4,5})(v\d+)?')
        inferred_arxiv_id = None
        
        # Check uploaded file name
        match = arxiv_pattern.search(file.filename)
        if match:
            inferred_arxiv_id = match.group(1)
        
        # Check directory contents if not found
        if not inferred_arxiv_id:
            for item in task_dir.iterdir():
                match = arxiv_pattern.search(item.name)
                if match:
                    inferred_arxiv_id = match.group(1)
                    break
        
        # If arxiv_id inferred, try to use/create the shared arxiv_ directory
        final_source_path = task_dir
        if inferred_arxiv_id:
            shared_upload_dir = settings.uploads_dir / f"arxiv_{inferred_arxiv_id}"
            if shared_upload_dir.exists() and shared_upload_dir != task_dir:
                logger.info(f"Found existing upload for arxiv_id {inferred_arxiv_id}, reusing: {shared_upload_dir}")
                # Clean up the newly uploaded directory
                shutil.rmtree(task_dir)
                final_source_path = shared_upload_dir
                # Update task metadata for arxiv reuse
                task = task_manager.get_task(task_id)
                if task:
                    task["arxiv_id"] = inferred_arxiv_id
                    task["source_type"] = "arxiv"
                    # Update source_path and arxiv_id in DB
                    task_manager.update_task(
                        task_id=task_id,
                        source_path=str(final_source_path),
                        arxiv_id=inferred_arxiv_id,
                        user_id=user_id
                    )
            else:
                # Shared directory doesn't exist yet — rename UUID dir to standard arxiv_ format
                logger.info(f"Renaming upload directory {task_dir.name} → arxiv_{inferred_arxiv_id}")
                try:
                    shutil.move(str(task_dir), str(shared_upload_dir))
                    final_source_path = shared_upload_dir
                    # Update task metadata to reflect the arxiv identity
                    task = task_manager.get_task(task_id)
                    if task:
                        task["arxiv_id"] = inferred_arxiv_id
                        task["source_type"] = "arxiv"
                        task_manager.update_task(
                            task_id=task_id,
                            source_path=str(final_source_path),
                            arxiv_id=inferred_arxiv_id,
                            user_id=user_id
                        )
                    logger.info(f"Successfully renamed to: {shared_upload_dir}")
                except Exception as rename_err:
                    logger.warning(
                        f"Failed to rename upload dir to arxiv_ format: {rename_err}. "
                        f"Keeping UUID directory name: {task_dir.name}"
                    )
                    # Rename failure is non-fatal; keep UUID dir and continue
        
        # Validate LaTeX directory
        logger.info(f"Validating LaTeX directory: {final_source_path}")
        validation = validate_latex_directory(final_source_path)
        
        validation_response = LatexValidationResponse(
            is_valid=validation.is_valid,
            main_file=validation.main_file,
            tex_files=validation.tex_files,
            warnings=validation.warnings,
            errors=validation.errors
        )
        
        # Update task with validation results
        if validation.is_valid:
            stored_source_path = str(final_source_path)
            if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
                stored_source_path = task_artifact_storage.persist_task_directory(
                    Path(final_source_path),
                    stored_path=task_artifact_storage.normalize_stored_task_path(final_source_path),
                    delete_local=True,
                )

            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.PENDING.value,
                progress=100,
                message=f"File {file.filename} uploaded and validated successfully",
                source_path=stored_source_path,
                source_available=True,
                latex_validation=validation.model_dump(),
                user_id=user_id
            )
            
            upload_success = True  # 标记上传成功
            
            return UploadResponse(
                task_id=task_id,
                status="success",
                message=f"File {file.filename} uploaded successfully. Main file: {validation.main_file}",
                source_path=stored_source_path,
                latex_validation=validation_response
            )
        else:
            # Not a valid LaTeX project
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.FAILED.value,
                error="; ".join(validation.errors),
                latex_validation=validation.model_dump(),
                user_id=user_id
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
            error="ZIP 文件损坏或无效",
            user_id=user_id
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
            error=err_msg,
            user_id=user_id
        )
        raise HTTPException(
            status_code=500,
            detail=err_msg
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        raise
    
    except ValueError as e:
        # Extraction format errors (TAR/RAR issues) - 422 Unprocessable Entity
        err_msg = str(e)
        logger.error(f"Extraction failed due to format issue: {e}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=err_msg,
            user_id=user_id
        )
        raise HTTPException(
            status_code=422,
            detail=err_msg
        )
    
    except Exception as e:
        err_msg = f"文件上传失败: {str(e)}"
        logger.error(f"Upload failed: {e}")
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=err_msg,
            user_id=user_id
        )
        raise HTTPException(
            status_code=500,
            detail=err_msg
        )
    
    finally:
        # 如果上传失败,清理临时目录(避免垃圾缓存)
        if not upload_success and task_dir.exists():
            try:
                shutil.rmtree(task_dir)
                logger.info(f"Cleaned up failed upload directory: {task_dir}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up directory {task_dir}: {cleanup_error}")
