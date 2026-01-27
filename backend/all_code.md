# 项目代码汇总: backend

> 说明：
> 1. 已忽略 `__init__.py` 及包含 `backup/test` 的文件。
> 2. 已自动折叠长 Prompt。

## 1. 项目文件结构

```text
📦 backend
└── app
    ├── api
    │   └── routes
    │       ├── arxiv.py
    │       ├── download.py
    │       ├── task.py
    │       ├── translate.py
    │       └── upload.py
    ├── core
    │   └── config.py
    ├── main.py
    └── services
        ├── agents
        │   ├── base_tool_agent.py
        │   ├── coordinator_agent.py
        │   ├── generator_agent.py
        │   ├── parser_agent.py
        │   ├── translator_agent.py
        │   └── validator_agent.py
        ├── latex
        │   ├── compiler.py
        │   ├── parser.py
        │   ├── prompts.py
        │   ├── reconstruct.py
        │   └── utils.py
        └── task_manager.py
```

---

## 2. 详细代码内容

### 📄 app\api\routes\arxiv.py

```python
"""
arXiv API Routes

Provides endpoints for downloading arXiv papers.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
import logging

from backend.app.services.latex.utils import (
    batch_download_arxiv_tex,
    extract_arxiv_ids,
    is_valid_arxiv_id
)
from backend.app.services.task_manager import get_task_manager
from backend.app.core.config import get_settings, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()


class ArxivRequest(BaseModel):
    """arXiv download request"""
    arxiv_id: str = Field(..., description="arXiv paper ID (e.g., '2508.18791' or URL)")
    

class ArxivResponse(BaseModel):
    """arXiv download response"""
    task_id: str
    arxiv_id: str
    status: str
    message: str
    source_path: str | None = None


@router.post("/arxiv", response_model=ArxivResponse)
async def download_arxiv(request: ArxivRequest):
    """
    Download arXiv paper source
    
    Args:
        request: arXiv download request with paper ID
    
    Returns:
        Task information with download status
    
    Raises:
        HTTPException: If arXiv ID is invalid or download fails
    """
    # Extract and validate arXiv ID
    arxiv_ids = extract_arxiv_ids([request.arxiv_id])
    
    if not arxiv_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid arXiv ID format: {request.arxiv_id}"
        )
    
    arxiv_id = arxiv_ids[0]
    logger.info(f"Downloading arXiv paper: {arxiv_id}")
    
    # Create task
    task_id = task_manager.create_task(source_type="arxiv")
    
    # Update task with arXiv ID
    task_manager.update_task(
        task_id=task_id,
        status=TaskStatus.PROCESSING.value,
        message=f"Downloading arXiv paper {arxiv_id}..."
    )
    
    try:
        # Download arXiv source
        source_dirs = batch_download_arxiv_tex(
            [arxiv_id],
            save_dir=str(settings.uploads_dir / task_id)
        )
        
        if not source_dirs:
            raise Exception(f"Failed to download arXiv paper {arxiv_id}")
        
        source_path = source_dirs[0]
        
        # Update task as completed
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PENDING.value,  # Ready for translation
            progress=100,
            message=f"arXiv paper {arxiv_id} downloaded successfully",
            source_path=source_path,
            source_available=True
        )
        
        logger.info(f"Successfully downloaded arXiv {arxiv_id} to {source_path}")
        
        return ArxivResponse(
            task_id=task_id,
            arxiv_id=arxiv_id,
            status="success",
            message=f"arXiv paper {arxiv_id} downloaded successfully",
            source_path=source_path
        )
    
    except Exception as e:
        logger.error(f"Failed to download arXiv {arxiv_id}: {e}")
        
        # Update task as failed
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"Failed to download arXiv paper {arxiv_id}"
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download arXiv paper: {str(e)}"
        )


@router.get("/arxiv/validate/{arxiv_id}")
async def validate_arxiv_id(arxiv_id: str):
    """
    Validate arXiv ID format
    
    Args:
        arxiv_id: arXiv paper ID to validate
    
    Returns:
        Validation result
    """
    is_valid = is_valid_arxiv_id(arxiv_id)
    
    return {
        "arxiv_id": arxiv_id,
        "is_valid": is_valid,
        "message": "Valid arXiv ID" if is_valid else "Invalid arXiv ID format"
    }

```

---

### 📄 app\api\routes\download.py

```python
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

```

---

### 📄 app\api\routes\task.py

```python
"""
Task Status API Routes

Provides endpoints for querying task status and progress.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from backend.app.services.task_manager import get_task_manager

logger = logging.getLogger(__name__)
router = APIRouter()
task_manager = get_task_manager()


class TaskStatusResponse(BaseModel):
    """Task status response"""
    task_id: str
    status: str
    progress: int
    stage: str
    message: str
    error: Optional[str] = None
    warnings: Optional[str] = None
    source_available: bool
    created_at: str
    completed_at: Optional[str] = None


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get task status and progress
    
    Args:
        task_id: Task ID
    
    Returns:
        Task status information
    
    Raises:
        HTTPException: If task not found
    """
    logger.info(f"Getting status for task: {task_id}")
    
    # Get task from manager
    task = task_manager.get_task(task_id)
    
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    return TaskStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        stage=task["stage"],
        message=task["message"],
        error=task.get("error"),
        warnings=task.get("warnings"),
        source_available=task["source_available"],
        created_at=task["created_at"],
        completed_at=task.get("completed_at")
    )


@router.get("/tasks")
async def list_all_tasks():
    """
    List all tasks (for debugging)
    
    Returns:
        Dictionary of all tasks
    """
    logger.info("Listing all tasks")
    return task_manager.get_all_tasks()


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """
    Delete a task
    
    Args:
        task_id: Task ID
    
    Returns:
        Deletion status
    
    Raises:
        HTTPException: If task not found
    """
    logger.info(f"Deleting task: {task_id}")
    
    success = task_manager.delete_task(task_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    return {
        "task_id": task_id,
        "status": "deleted",
        "message": "Task deleted successfully"
    }

```

---

### 📄 app\api\routes\translate.py

```python
"""
Translation API Routes

Provides endpoints for starting translation tasks.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
import logging
from pathlib import Path

from backend.app.services.task_manager import get_task_manager
from backend.app.services.agents.coordinator_agent import CoordinatorAgent
from backend.app.core.config import get_settings, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()


class TranslateRequest(BaseModel):
    """Translation request"""
    target_language: str = Field(default="ch", description="Target language code (e.g., 'ch', 'en')")
    source_language: str = Field(default="en", description="Source language code (e.g., 'en', 'ch')")


class TranslateResponse(BaseModel):
    """Translation response"""
    task_id: str
    status: str
    message: str


async def run_translation(task_id: str, target_language: str, source_language: str):
    """
    Background task to run translation
    
    Args:
        task_id: Task ID
        target_language: Target language code
        source_language: Source language code
    """
    logger.info(f"Starting translation for task: {task_id}")
    
    try:
        # Get task info
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return
        
        source_path = Path(task["source_path"])
        if not source_path.exists():
            raise Exception(f"Source path not found: {source_path}")
        
        # Find main .tex file
        tex_files = list(source_path.rglob("*.tex"))
        if not tex_files:
            raise Exception(f"No .tex files found in {source_path}")
        
        # Use the first .tex file (or implement logic to find main file)
        main_tex_file = tex_files[0]
        logger.info(f"Using main tex file: {main_tex_file}")
        
        # Create output directory
        output_dir = settings.outputs_dir / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Update task status
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PROCESSING.value,
            progress=0,
            message="Initializing translation..."
        )
        
        # Create progress callback
        progress_callback = task_manager.create_progress_callback(task_id)
        
        # Load LLM config
        llm_config = settings.get_llm_config()
        
        # Create coordinator agent
        coordinator = CoordinatorAgent(
            llm_config=llm_config,
            target_lang=target_language,
            source_lang=source_language
        )
        
        # Run translation workflow
        logger.info(f"Running translation workflow for {main_tex_file}")
        result = coordinator.workflow_latextrans(
            input_file=str(main_tex_file),
            output_dir=str(output_dir),
            on_progress=progress_callback
        )
        
        # Check result
        if result.get("status") == "success":
            # Find output PDF
            output_pdf = output_dir / f"{main_tex_file.stem}_translated.pdf"
            
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.COMPLETED.value,
                progress=100,
                message="Translation completed successfully",
                output_path=str(output_dir)
            )
            logger.info(f"Translation completed: {task_id}")
        
        elif result.get("status") == "completed_with_warnings":
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.COMPLETED_WITH_WARNINGS.value,
                progress=100,
                message="Translation completed with warnings",
                warnings=result.get("warnings"),
                output_path=str(output_dir)
            )
            logger.warning(f"Translation completed with warnings: {task_id}")
        
        else:
            # Handle failure
            error_msg = result.get("error", "Translation failed")
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.FAILED.value,
                error=error_msg,
                message="Translation failed"
            )
            logger.error(f"Translation failed: {task_id} - {error_msg}")
    
    except Exception as e:
        logger.error(f"Translation error for task {task_id}: {e}", exc_info=True)
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"Translation error: {str(e)}"
        )


@router.post("/translate/{task_id}", response_model=TranslateResponse)
async def start_translation(
    task_id: str,
    request: TranslateRequest,
    background_tasks: BackgroundTasks
):
    """
    Start translation for a task
    
    Args:
        task_id: Task ID from upload or arxiv endpoint
        request: Translation configuration
        background_tasks: FastAPI background tasks
    
    Returns:
        Translation start confirmation
    
    Raises:
        HTTPException: If task not found or not ready for translation
    """
    logger.info(f"Translation request for task: {task_id}")
    
    # Validate task exists
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # Validate task is ready for translation
    if not task["source_available"]:
        raise HTTPException(
            status_code=400,
            detail="Task source not available. Please upload file or download arXiv paper first."
        )
    
    if task["status"] == TaskStatus.PROCESSING.value:
        raise HTTPException(
            status_code=400,
            detail="Task is already being processed"
        )
    
    # Start background translation
    background_tasks.add_task(
        run_translation,
        task_id=task_id,
        target_language=request.target_language,
        source_language=request.source_language
    )
    
    logger.info(f"Translation started in background for task: {task_id}")
    
    return TranslateResponse(
        task_id=task_id,
        status="started",
        message="Translation started in background"
    )

```

---

### 📄 app\api\routes\upload.py

```python
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

```

---

### 📄 app\core\config.py

```python
"""
Backend Configuration Module

Loads settings from environment variables and TOML config files.
Provides configuration for LLM API, storage paths, and task status enums.
"""

import os
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
import toml


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED_COMPILATION = "failed_compilation"
    FAILED = "failed"


class CompilationStage(str, Enum):
    """Compilation stage enumeration"""
    IDLE = "idle"
    PARSING = "parsing"
    TRANSLATING = "translating"
    COMPILING = "compiling"
    COMPILATION_FAILED = "compilation_failed"
    DONE = "done"


class Settings(BaseSettings):
    """Application settings"""
    
    # Application Info
    app_name: str = "LaTeXTrans Backend"
    version: str = "0.1.0"
    
    # LLM API Configuration
    llm_api_key: str = Field(
        default="sk-SVd4dIKfuIwhQ9kUlgCr9ZMpoIWp7PEzZxpVStjSRqeqNBLu",
        env="LLM_API_KEY"
    )
    llm_base_url: str = Field(
        default="https://aicanapi.com/v1/chat/completions",
        env="LLM_BASE_URL"
    )
    llm_model: str = Field(
        default="gpt-4.1-mini",
        env="LLM_MODEL"
    )
    llm_timeout: int = Field(
        default=60,
        env="LLM_TIMEOUT"
    )
    
    # Translation Settings
    target_language: str = "ch"
    source_language: str = "en"
    
    # Storage Paths (relative to project root)
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")
    uploads_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "uploads")
    outputs_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "outputs")
    terms_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "terms")
    
    # File Upload Settings
    max_upload_size: int = 50 * 1024 * 1024  # 50MB in bytes
    allowed_extensions: set = {".zip", ".tex", ".tar", ".tar.gz"}
    
    # CORS Settings
    cors_origins: list = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure all directories exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.terms_dir.mkdir(parents=True, exist_ok=True)
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM API configuration as a dictionary"""
        return {
            "api_key": self.llm_api_key,
            "base_url": self.llm_base_url,
            "model": self.llm_model,
            "timeout": self.llm_timeout
        }
    
    def load_toml_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load additional configuration from TOML file
        
        Args:
            config_path: Path to TOML config file. Defaults to 'config/default.toml'
        
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            config_path = self.base_dir / "prototype_system" / "config" / "default.toml"
        
        if Path(config_path).exists():
            return toml.load(config_path)
        else:
            return {}


# Global settings instance
settings = Settings()


# Helper function to get settings
def get_settings() -> Settings:
    """Get application settings"""
    return settings


# Helper function to get LLM config
def get_llm_config() -> Dict[str, Any]:
    """Get LLM API configuration as a dictionary"""
    return settings.get_llm_config()

```

---

### 📄 app\main.py

```python
"""
FastAPI Main Application

Minimal MVP version with:
- Health check endpoint
- arXiv download endpoint
- Basic CORS configuration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.app.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="LaTeXTrans Backend API - MVP Version"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(f"LLM Model: {settings.llm_model}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info(f"Shutting down {settings.app_name}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Status information
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "llm_model": settings.llm_model
    }


@app.get("/")
async def root():
    """
    Root endpoint
    
    Returns:
        Welcome message
    """
    return {
        "message": "LaTeXTrans Backend API",
        "version": settings.version,
        "docs": "/docs",
        "health": "/health"
    }


# Import and include API routes
from backend.app.api.routes import arxiv, upload, task, translate, download

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(arxiv.router, prefix="/api", tags=["arxiv"])
app.include_router(translate.router, prefix="/api", tags=["translate"])
app.include_router(task.router, prefix="/api", tags=["task"])
app.include_router(download.router, prefix="/api", tags=["download"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )

```

---

### 📄 app\services\agents\base_tool_agent.py

```python
"""
Base Tool Agent

Adapted from prototype system with:
- Python logging integrated (replacing print statements)
- Progress callback mechanism added
- All functionality preserved
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
import json
import yaml
import toml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BaseToolAgent(ABC):
    """
    Abstract base class for all tool agents in the multi-agent translation system.

    Each tool agent is responsible for a specific task in the translation workflow,
    such as parsing, translating, refining, or validating documents.
    """

    def __init__(
        self,
        agent_name: str,
        config: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Callable[[str, int, str], None]] = None
    ):
        """
        Initializes the BaseToolAgent.

        Args:
            agent_name (str): The unique name of this agent (e.g., "ParserAgent", "TranslatorAgent").
            config (Optional[Dict[str, Any]]): Agent-specific configuration parameters. Defaults to None.
            on_progress (Optional[Callable]): Progress callback function(stage, percentage, message)
        """
        self.agent_name = agent_name
        self.config = config if config is not None else {}
        self.on_progress = on_progress
        
    def log(self, message: str, level: str = "info"):
        """
        Logs messages at different levels using Python logging.

        Args:
            message (str): The message to log.
            level (str): The logging level. Defaults to "info".
        """
        full_message = f"[{self.agent_name}] {message}"
        
        if level == "info":
            logger.info(full_message)
        elif level == "debug":
            logger.debug(full_message)
        elif level == "warning":
            logger.warning(full_message)
        elif level == "error":
            logger.error(full_message)
        else:
            raise ValueError(f"Unknown log level: {level}")
    
    def update_progress(self, percentage: int, message: str):
        """
        Update progress through callback if available
        
        Args:
            percentage: Progress percentage (0-100)
            message: Progress message
        """
        if self.on_progress:
            self.on_progress(self.agent_name.lower(), percentage, message)

    @abstractmethod
    def execute(self, data: Any, **kwargs: Any) -> Any:
        """
        Executes the core task of the agent.

        This method must be implemented by all concrete tool agent subclasses.
        The input `data` and the returned `Any` type will vary depending on the
        specific agent's role in the workflow (e.g., file path, text string,
        parsed document object, translation result).
        """
        raise NotImplementedError(f"{self.__class__.__name__}.execute() must be implemented.")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value for the agent.
        If the key does not exist, returns the provided default value.
        """
        return self.config.get(key, default)
    
    def read_file(self, file_path: str, file_format: str) -> Any:
        """
        Reads a file and returns its content.
        
        Args:
            file_path: Path to file
            file_format: Format of file (json, yaml, toml)
            
        Returns:
            File content parsed according to format
        """
        if file_format == "json":
            with open(file_path, "r", encoding='utf-8') as f:
                return json.load(f)
        elif file_format == "yaml":
            with open(file_path, "r", encoding='utf-8') as f:
                return yaml.safe_load(f)
        elif file_format == "toml":
            with open(file_path, "r", encoding='utf-8') as f:
                return toml.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
        
    def save_file(self, file_path: str, file_format: str, data: Any):
        """
        Saves data to a file.
        
        Args:
            file_path: Path to save file
            file_format: Format to save in (json, yaml, toml)
            data: Data to save
        """
        if file_format == "json":
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)   
        elif file_format == "yaml":
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f)
        elif file_format == "toml":
            with open(file_path, 'w', encoding='utf-8') as f:
                toml.dump(data, f)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

```

---

### 📄 app\services\agents\coordinator_agent.py

```python
import os
import shutil
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import asyncio
import logging

from .parser_agent import ParserAgent
from .translator_agent import TranslatorAgent 
from .generator_agent import GeneratorAgent
from .validator_agent import ValidatorAgent

logger = logging.getLogger(__name__)


class CoordinatorAgent:
    """
    The main orchestrator agent for the translation system.
    It coordinates the workflow of various tool agents based on document format
    and configuration.
    """

    def __init__(self, 
                 config: Dict[str, Any],
                 project_dir: str = None,
                 output_dir: Optional[str] = None,
                 on_progress: Optional[Callable[[int, str], None]] = None,
                 ):
        """
        Initializes the CoordinatorAgent.
        """
        self.config = config
        self.name = config.get("sys_name", "LaTeXTrans")
        self.target_language = config.get("target_language", "ch")
        self.source_language = config.get("source_language", "en")
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.loop = asyncio.new_event_loop()
        self.mode = config.get("mode", 0)
        self.on_progress = on_progress

    def update_progress(self, percentage: int, message: str = "") -> None:
        """Update progress via callback if available"""
        if self.on_progress:
            self.on_progress(percentage, message)

    def run_async(self, coro):
        """
        Run asynchronous coroutines in the existing event loop
        """
        return self.loop.run_until_complete(coro)

    async def workflow_latextrans_async(self) -> None:
        """
        Initializes the tool agent based on the provided agent name key.
        """
        base_name = os.path.basename(self.project_dir)
        transed_project_dir = os.path.join(self.output_dir, f"{self.target_language}_{base_name}")

        os.makedirs(transed_project_dir, exist_ok=True)

        # Step 1: Parse LaTeX (10% total progress)
        logger.info(f"Starting LaTeX parsing for {base_name}")
        self.update_progress(5, "Initializing parser")
        
        parser_agent = ParserAgent(
            config=self.config,
            project_dir=self.project_dir,
            output_dir=transed_project_dir,
            on_progress=lambda p, m: self.update_progress(5 + int(p * 0.05), m)
        )
        parser_agent.execute()
        self.update_progress(10, "Parsing completed")

        # Step 2: Translate (10% - 70% total progress)
        logger.info("Starting translation")
        self.update_progress(10, "Initializing translator")
        
        translator_agent = TranslatorAgent(
            config=self.config,
            project_dir=self.project_dir,
            output_dir=transed_project_dir,
            trans_mode=self.mode,
            on_progress=lambda p, m: self.update_progress(10 + int(p * 0.6), m)
        )
        await translator_agent.execute()
        self.update_progress(70, "Translation completed")

        # Step 3: Validate (70% - 75% total progress)
        logger.info("Validating translation")
        self.update_progress(70, "Validating translation")
        
        validator_agent = ValidatorAgent(
            config=self.config,
            project_dir=self.project_dir,
            output_dir=transed_project_dir,
            on_progress=lambda p, m: self.update_progress(70 + int(p * 0.05), m)
        )
        errors_report = validator_agent.execute()
        
        # Step 4: Retry if needed (75% - 85% total progress)
        MAX_RETRIES = 3
        retry_count = 0
        if errors_report:
            translator_agent.trans_mode = 1

        while errors_report and retry_count < MAX_RETRIES:
            logger.info(f"Retrying translation for errors, attempt {retry_count + 1}/{MAX_RETRIES}")
            self.update_progress(75 + int((retry_count / MAX_RETRIES) * 10), 
                               f"Retrying errors (attempt {retry_count + 1}/{MAX_RETRIES})")
            
            translator_agent.errors_report = errors_report
            await translator_agent.execute(error_retry_count=retry_count, Maxtry=MAX_RETRIES)
            errors_report = validator_agent.execute(errors_report)
            retry_count += 1
        
        self.update_progress(85, "Validation completed")

        # Step 5: Generate PDF (85% - 100% total progress)
        logger.info("Generating PDF")
        self.update_progress(85, "Generating PDF")
        
        generator_agent = GeneratorAgent(
            config=self.config,
            project_dir=self.project_dir,
            output_dir=transed_project_dir,
            on_progress=lambda p, m: self.update_progress(85 + int(p * 0.15), m)
        )
        
        try:
            PDF_file_path = generator_agent.execute()
        except Exception as e:
            logger.error(f"Failed to generate PDF for {base_name}: {e}")
            self.update_progress(100, f"Failed: {e}")
            return
        
        if PDF_file_path:
            new_PDF_path = os.path.join(transed_project_dir, f"{self.target_language}_{base_name}.pdf")
            shutil.move(PDF_file_path, new_PDF_path)
            logger.info(f"Successfully translated {base_name} to {new_PDF_path}")
            self.update_progress(100, "Translation completed successfully")
        else:
            logger.error(f"Failed to generate PDF for {base_name}")
            self.update_progress(100, "Failed to generate PDF")

    def workflow_latextrans(self) -> None:
        """
        Initialize the tool agent and execute the LaTeX conversion workflow 
        (with event loop security management)
        """

        if hasattr(self, 'loop') and not self.loop.is_closed():
            self.loop.close()

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self.workflow_latextrans_async())

        finally:
            # Complete all asynchronous resource recycling
            import sys
            if tasks := asyncio.all_tasks(self.loop):
                self.loop.run_until_complete(
                    asyncio.gather(*tasks, return_exceptions=True)
                )

            # Special handling of asynchronous I/O recycling in Windows
            if sys.platform == "win32":
                self.loop.run_until_complete(
                    self.loop.shutdown_asyncgens()
                )

            self.loop.run_until_complete(self.loop.shutdown_default_executor())

```

---

### 📄 app\services\agents\generator_agent.py

```python
"""
Generator Agent

Adapted from prototype system with:
- All Streamlit dependencies removed
- Integrated new compile_with_fallback() function
- Progress callback mechanism added
- Python logging integrated
"""

from typing import Dict, Any, Optional, Callable
from .base_tool_agent import BaseToolAgent
from backend.app.services.latex.reconstruct import LatexConstructor
from backend.app.services.latex.compiler import compile_with_fallback
from pathlib import Path
import os
import shutil
import logging

logger = logging.getLogger(__name__)


class GeneratorAgent(BaseToolAgent):
    def __init__(self, 
                 config: Dict[str, Any],
                 project_dir: str = None,
                 output_dir: str = None,
                 on_progress: Optional[Callable[[str, int, str], None]] = None
                 ):
        super().__init__(agent_name="GeneratorAgent", config=config, on_progress=on_progress)
        self.config = config
        self.project_dir = project_dir
        self.output_dir = output_dir

    def execute(self) -> Optional[str]:
        """
        Execute generation task: reconstruct LaTeX and compile to PDF
        
        Returns:
            Path to generated PDF file, or None if compilation failed
        """
        self.log(f"Starting generation for project: {os.path.basename(self.project_dir)}")
        self.update_progress(5, "Starting generation")

        self.update_progress(10, "Reading JSON maps")
        sections = self.read_file(Path(self.output_dir, "sections_map.json"), "json")
        self.update_progress(20, "Loading sections")
        
        captions = self.read_file(Path(self.output_dir, "captions_map.json"), "json")
        self.update_progress(30, "Loading captions")
        
        envs = self.read_file(Path(self.output_dir, "envs_map.json"), "json")
        self.update_progress(40, "Loading environments")
        
        newcommands = self.read_file(Path(self.output_dir, "newcommands_map.json"), "json")
        self.update_progress(50, "Loading newcommands")
        
        inputs = self.read_file(Path(self.output_dir, "inputs_map.json"), "json")
        self.update_progress(60, "Loading inputs")

        self.update_progress(65, "Creating translation project directory")
        transed_latex_dir = self._create_transed_latex_folder(self.project_dir)
        self.log(f"Created translation directory: {transed_latex_dir}")

        self.update_progress(70, "Reconstructing LaTeX document")
        latex_constructor = LatexConstructor(
            sections=sections,
            captions=captions,
            envs=envs,
            inputs=inputs,
            newcommands=newcommands,
            output_latex_dir=transed_latex_dir
        )
        latex_constructor.construct(on_progress=self.on_progress)

        self.update_progress(80, "Compiling PDF document")
        
        # Find main .tex file in translated directory
        from pathlib import Path as PathLib
        tex_files = list(PathLib(transed_latex_dir).glob("*.tex"))
        
        if not tex_files:
            logger.error(f"No .tex files found in {transed_latex_dir}")
            self.update_progress(100, "No .tex files to compile")
            return None
        
        # Try to find main.tex or the first .tex file
        main_tex = None
        for tex in tex_files:
            if tex.stem.lower() in ["main", "paper", "article"]:
                main_tex = tex
                break
        
        if main_tex is None:
            main_tex = tex_files[0]
        
        logger.info(f"Compiling {main_tex.name}...")
        
        # Use new intelligent compiler with fallback
        result = compile_with_fallback(
            tex_file=str(main_tex),
            output_dir=transed_latex_dir
        )

        pdf_file = result.get("pdf_path")
        
        if pdf_file:
            self.update_progress(100, "PDF generation complete")
            self.log(f"Successfully generated PDF: {pdf_file}")
            return pdf_file
        else:
            self.update_progress(100, "PDF compilation failed")
            self.log("Failed to compile PDF document", level="error")
            if result.get("errors"):
                self.log(f"Errors: {result['errors']}", level="error")
            return None
        
    def _create_transed_latex_folder(self, src_dir: str) -> str:
        """
        Create a translated folder by copying the source directory.
        
        Args:
            src_dir: Source LaTeX project directory
            
        Returns:
            Path to created translation directory
        """
        if not os.path.isdir(src_dir):
            raise NotADirectoryError(f"The path {src_dir} is not a valid directory.")

        base_name = os.path.basename(src_dir)
        dest_dir = os.path.join(self.output_dir, base_name)

        if os.path.exists(dest_dir):
            self.log(f"Removing existing directory: {dest_dir}", level="debug")
            shutil.rmtree(dest_dir)
        
        shutil.copytree(src_dir, dest_dir)
        self.log(f"Copied {src_dir} to {dest_dir}", level="debug")

        return dest_dir

```

---

### 📄 app\services\agents\parser_agent.py

```python
"""
Parser Agent

Adapted from prototype system with:
- Streamlit dependencies removed
- Python logging integrated
- Progress callback mechanism added
- LLM config from backend.app.core.config
"""

from typing import Dict, Any, Optional, Callable
from .base_tool_agent import BaseToolAgent
from backend.app.services.latex import prompts as pm
from backend.app.services.latex.parser import LatexParser
from backend.app.core.config import get_settings
from pathlib import Path
import os
import requests
import time
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)


class ParserAgent(BaseToolAgent):
    def __init__(self, 
                 config: Dict[str, Any], 
                 project_dir: str = None,
                 output_dir: str = None,
                 on_progress: Optional[Callable[[str, int, str], None]] = None
                 ):
        super().__init__(agent_name="ParserAgent", config=config, on_progress=on_progress)
        self.config = config
        self.project_dir = project_dir
        self.output_dir = output_dir
        
        # Get LLM config
        settings = get_settings()
        llm_config = settings.get_llm_config()
        self.model = config.get("llm_config", {}).get("model", llm_config["model"])
        self.base_url = config.get("llm_config", {}).get("base_url", llm_config["base_url"])
        self.API_KEY = config.get("llm_config", {}).get("api_key", llm_config["api_key"])

    def execute(self) -> Any:
        """Execute parsing task"""
        pm.init_prompts(self.config.get("source_language", "en"), 
                       self.config.get("target_language", "ch"))
        
        self.log(f"Starting parsing for project: {os.path.basename(self.project_dir)}")
        self.update_progress(0, f"Parsing {os.path.basename(self.project_dir)}")

        latex_parser = LatexParser(self.project_dir, self.output_dir)
        latex_parser.parse(on_progress=self.on_progress)

        env_need_trans = []
        if latex_parser.envs_json:
            for env in latex_parser.envs_json:
                if env["need_trans"] and env["env_name"] not in ['abstract', 'itemize']:
                    env_need_trans.append(env)

        if env_need_trans:
            self.log(f"Setting need_trans for {len(env_need_trans)} environments")
            self.update_progress(70, "Determining translation requirements for environments")

            placeholder_to_index = {
                env["placeholder"]: i for i, env in enumerate(latex_parser.envs_json)
            }
            
            for env in tqdm(env_need_trans, desc=f"Setting need trans", total=len(env_need_trans), unit="env"):
                i = placeholder_to_index.get(env["placeholder"])
                if i is not None:
                    latex_parser.envs_json[i]["need_trans"] = self._request_llm_for_judge(
                        pm.set_need_trans_for_envs_system_prompt,
                        env["content"]
                    )

        self.update_progress(90, "Saving parsed data to JSON files")
        
        self.save_file(Path(self.output_dir, "inputs_map.json"), "json", latex_parser.inputs_json)
        self.save_file(Path(self.output_dir, "envs_map.json"), "json", latex_parser.envs_json)
        self.save_file(Path(self.output_dir, "captions_map.json"), "json", latex_parser.captions_json)
        self.save_file(Path(self.output_dir, "newcommands_map.json"), "json", latex_parser.newcommands_json)
        self.save_file(Path(self.output_dir, "sections_map.json"), "json", latex_parser.sections_json)

        self.update_progress(100, "Parsing complete")
        self.log(f"Successfully parsed {os.path.basename(self.project_dir)}")
        self.log(f"Parsed files saved in {self.output_dir}")

    def _request_llm_for_judge(self, system_prompt: str, text: str) -> bool:
        """
        Request LLM API to determine if environment needs translation
        """
        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"{text}"
                }
            ],
            "temperature": 0,
            "max_tokens": 50
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(1, 4):
            try:
                response = requests.post(self.base_url, json=payload, headers=headers, timeout=100)
                response.raise_for_status()
                result = response.json()
                output = result["choices"][0]["message"]["content"].strip()

                if output.lower() == "true":
                    return True
                elif output.lower() == "false":
                    return False
                else:
                    return True
            except requests.exceptions.RequestException as e:
                if attempt < 3:
                    logger.warning(f"LLM request failed (attempt {attempt}): {e}")
                    time.sleep(3)
                else:
                    logger.error(f"Failed to determine translation need, defaulting to True")
                    return True

```

---

### 📄 app\services\agents\translator_agent.py

```python
from typing import Dict, Any, List, Optional, Callable
from .base_tool_agent import BaseToolAgent
import backend.app.services.latex.prompts as pm
from backend.app.services.latex.utils import *
from pathlib import Path
import os
import re
import regex
import asyncio
import aiohttp
import time
import pandas as pd
import logging
import json

logger = logging.getLogger(__name__)


class TranslatorAgent(BaseToolAgent):
    def __init__(self, 
                 config: Dict[str, Any], 
                 trans_mode: int = 0,
                 project_dir: Optional[str] = None,
                 output_dir: Optional[str] = None,
                 errors_report: Optional[List[Dict]] = None,
                 on_progress: Optional[Callable[[int, str], None]] = None,
                 ):
        super().__init__(agent_name="TranslatorAgent", config=config, on_progress=on_progress)
        self.config = config
        self.update_term = config.get("update_term", False)
        self.model = config["llm_config"].get("model", "gpt-4o")
        self.base_url = config["llm_config"].get("base_url", None)
        self.API_KEY = config["llm_config"].get("api_key", None)
        self.user_term = config.get("user_term", None)
        self.target_language = config.get("target_language", "ch")
        self.category = config.get("category", None)
        self.project_dir = project_dir  # Project path for parsing
        self.output_dir = output_dir  # Output directory for parsed files
        self.fail_section_nums = []
        self.fail_caption_phs = []
        self.fail_env_phs = []
        self.have_fail_parts = False
        self.errors_report = errors_report if errors_report is not None else []
        self.trans_mode = trans_mode if trans_mode is not None else 0
        self.term_dict = {}
        self.summary = ''
        self.prev_text = ''
        self.prev_transed_text = ''
        self.currant_content = ''

    async def execute(self, error_retry_count=0, Maxtry=3):

        pm.init_prompts(self.config["source_language"], self.config["target_language"])
        self.add_placeholder()
        self.build_term_dict()

        sections = self.read_file(Path(self.output_dir, "sections_map.json"), "json")
        captions = self.read_file(Path(self.output_dir, "captions_map.json"), "json")
        envs = self.read_file(Path(self.output_dir, "envs_map.json"), "json")

        if self.trans_mode == 0 or self.trans_mode == 2:
            logger.info(f"Starting translating for project: {os.path.basename(self.project_dir)}")
            self.update_progress(5, f"Starting translating for project: {os.path.basename(self.project_dir)}")

            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(10)

                async def process_section(i, sec):
                    async with sem:
                        translated = await self.translate(sec, envs, captions, session)
                        return i, translated

                tasks = [process_section(i, sec) for i, sec in enumerate(sections)]

                completed = 0
                total = len(tasks)

                for future in asyncio.as_completed(tasks):
                    i, translated_section = await future
                    sections[i] = translated_section
                    
                    completed += 1
                    progress = int(5 + 90 * completed / total)
                    self.update_progress(progress, f"Translated {completed}/{total} sections")

                    # Save progress
                    self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                    self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                    self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)

                self.update_progress(95, "Validating translation results")

                await self._val_fail_parts(Maxtry=Maxtry,
                                     sections=sections,
                                     captions=captions,
                                     envs=envs,
                                     session=session)

                logger.info("Successfully translated sections!")
                self.update_progress(100, "Successfully translated sections!")

        elif self.trans_mode == 1:
            async with aiohttp.ClientSession() as session:
                error_parts = [error_part["num_or_ph"] for error_part in self.errors_report]
                logger.info(f"Starting retranslating for error parts: {error_parts}, attempt {error_retry_count + 1}/{Maxtry}")
                
                await self._retranslate_error_parts(secs=sections,
                                                    caps=captions,
                                                    envs=envs,
                                                    session=session)

                self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)

                self.fail_section_nums.clear()
                self.fail_caption_phs.clear()
                self.fail_env_phs.clear()
                self.have_fail_parts = False

                await self._val_fail_parts(Maxtry=Maxtry,
                                           sections=sections,
                                           captions=captions,
                                           envs=envs,
                                           session=session)

            logger.info("Successfully retranslated error parts!")

    async def translate(self,
                        section: Dict[str, Any],
                        envs: List[Dict[str, Any]],
                        captions: List[Dict[str, Any]],
                        session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Translates the input data
        """
        placeholder_pattern_cap = r"<PLACEHOLDER_CAP_\d+>"
        placeholder_pattern_env = r"<PLACEHOLDER_ENV_\d+>"
        placeholders_cap = re.findall(placeholder_pattern_cap, section["content"])
        placeholders_env = re.findall(placeholder_pattern_env, section["content"])


        if(section["section"] == "-1" or section["section"] == "0"):
            section = section
        else:
            section = await self._translate_section(section, session)  

        for placeholder in placeholders_env:
            for i, env in enumerate(envs):
                if placeholder == env["placeholder"]:
                    placeholders_cap_in_env = re.findall(placeholder_pattern_cap, env["content"])
                    placeholders_cap.extend(placeholders_cap_in_env)
                    envs[i] = await self._translate_env(env, session)  
                    break

        # remove duplicates
        placeholders_cap = list(dict.fromkeys(placeholders_cap))

        for placeholder in placeholders_cap:
            for i, caption in enumerate(captions):
                if placeholder == caption["placeholder"]:
                    captions[i] = await self._translate_caption(caption, session)  
                    break

        return section
    
    async def _val_fail_parts(self, sections, captions, envs, Maxtry, session: aiohttp.ClientSession, fail_retry_count=0) -> str:
            while fail_retry_count < Maxtry and self.have_fail_parts:
                fail_parts = self.fail_section_nums + self.fail_caption_phs + self.fail_env_phs
                if fail_retry_count == Maxtry:
                    logger.error(f"Failed to translate {fail_parts}")
                    break
                    
                logger.info(f"Retranslating fail parts: {fail_parts}, attempt {fail_retry_count+1}/{Maxtry}")
                
                await self._retranslate_fail_parts(secs=sections,
                                            caps=captions,
                                            envs=envs,
                                            session=session)
                self.save_file(Path(self.output_dir, "sections_map.json"), "json", sections)
                self.save_file(Path(self.output_dir, "captions_map.json"), "json", captions)
                self.save_file(Path(self.output_dir, "envs_map.json"), "json", envs)
                
                fail_retry_count += 1

    async def _retranslate_fail_parts(self,
                                secs: List[Dict[str, Any]], 
                                caps: List[Dict[str, Any]], 
                                envs: List[Dict[str, Any]],
                                session: aiohttp.ClientSession) -> Any:
        sec_nums = self.fail_section_nums[:]
        cap_phs = self.fail_caption_phs[:]
        env_phs = self.fail_env_phs[:]
        self.fail_section_nums.clear()
        self.fail_caption_phs.clear()
        self.fail_env_phs.clear()
        self.have_fail_parts = False

        sec_dict = {s["section"]: i for i, s in enumerate(secs)}
        cap_dict = {c["placeholder"]: i for i, c in enumerate(caps)}
        env_dict = {e["placeholder"]: i for i, e in enumerate(envs)}

        if sec_nums:
            self.log(f"Retranslating for {sec_nums}")
            for sec_num in sec_nums:
                if sec_num == "-1" or sec_num == "0":
                    continue
                if sec_num in sec_dict:
                    i = sec_dict[sec_num]
                    secs[i] = await self._translate_section(secs[i], session)
            # else:
            #     print(f"[Warning] Section {sec_num} not found.")
        if cap_phs:
            self.log(f"Retranslating for {cap_phs}")
            for cap_ph in cap_phs:
                if cap_ph in cap_dict:
                    i = cap_dict[cap_ph]
                    caps[i] = await self._translate_caption(caps[i], session) 
            # else:
            #     print(f"[Warning] Caption placeholder {cap_ph} not found.")
        if env_phs:
            self.log(f"Retranslating for {env_phs}")
            for env_ph in env_phs:
                if env_ph in env_dict:
                    i = env_dict[env_ph]
                    envs[i] = await self._translate_env(envs[i], session) 
            # else:
            #     print(f"[Warning] Environment placeholder {env_ph} not found.")

    async def _retranslate_error_parts(self, secs, caps, envs, session) -> Any:

        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(20)
            
            completed = 0
            total = len(self.errors_report)
            
            async def process_ErrorPart(i, error_report):
                async with sem:
                    error_message = []
                    if "command_error" in error_report:
                        error_message.append(error_report["command_error"])
                    if "ph_error" in error_report:
                        error_message.append(error_report["ph_error"])
                    if "bracket_error" in error_report:
                        error_message.append(error_report["bracket_error"])
                    error_message = "\n".join(error_message)

                    if error_report["part"] == "sec":
                        async def process_section(i, sec):
                            async with sem:
                                if error_report["num_or_ph"] == sec["section"]:
                                    sec_async = await self._translate_section(section=sec, error_message=error_message,
                                                                              session=session)
                                    return {"index": i, "result": sec_async, "is_valid": True}
                                else:
                                    return {"index": None, "result": None, "is_valid": False}

                        tasks_sec = [process_section(i, sec) for i, sec in enumerate(secs)]
                        for future in asyncio.as_completed(tasks_sec):
                            result = await future
                            
                            if result["is_valid"]:
                                i = result["index"]
                                _sec = result["result"]
                                secs[i] = _sec
                    elif error_report["part"] == "env":
                        async def process_env(i, env):
                            async with sem:
                                if error_report["num_or_ph"] == env["placeholder"]:
                                    env_async = await self._translate_env(env=env, error_message=error_message,
                                                                          session=session)
                                    return {"index": i, "result": env_async, "is_valid": True}
                                else:
                                    return {"index": None, "result": None, "is_valid": False}

                        tasks_env = [process_env(i, env) for i, env in enumerate(envs)]
                        for future in asyncio.as_completed(tasks_env):
                            result = await future
                            
                            if result["is_valid"]:
                                i = result["index"]
                                _env = result["result"]
                                envs[i] = _env
                    elif error_report["part"] == "cap":
                        async def process_cap(i, cap):
                            async with sem:
                                if error_report["num_or_ph"] == cap["placeholder"]:
                                    cap_async = await self._translate_caption(caption=cap, error_message=error_message,
                                                                              session=session)
                                    return {"index": i, "result": cap_async, "is_valid": True}
                                else:
                                    return {"index": None, "result": None, "is_valid": False}

                        tasks_cap = [process_cap(i, cap) for i, cap in enumerate(caps)]
                        for future in asyncio.as_completed(tasks_cap):
                            result = await future
                            
                            if result["is_valid"]:
                                i = result["index"]
                                _cap = result["result"]
                                caps[i] = _cap
                    return i

            tasks_ErrorPart = [process_ErrorPart(i, error_report) for i, error_report in enumerate(self.errors_report)]
            for future in asyncio.as_completed(tasks_ErrorPart):
                result = await future
                completed += 1
                progress_pct = int(100 * completed / total) if total > 0 else 100
                self.update_progress(progress_pct, f"Retranslated {completed}/{total} error parts")
                
                if result is not None:
                    i = result
            
            logger.info("Completed retranslation of error parts")

    async def _translate_section(self, section: Dict[str, Any], session: aiohttp.ClientSession, error_message=None) -> Dict[str, Any]:
        
        transed_section = section.copy()
        section_num = section["section"]
        if self.trans_mode == 0:
            
            transed_section["trans_content"] = await self._request_llm_for_trans(
                pm.section_system_prompt,
                section["content"],
                fail_part=section_num,
                type="sec",
                session=session
            )
        elif self.trans_mode == 1:
            transed_section["trans_content"] = await self._request_llm_for_retrans_error_parts(
            pm.retrans_error_parts_system_prompt,
            part=transed_section,
            error_message=error_message,
            fail_part=section_num,
            type="sec",
            session=session)

        elif self.trans_mode == 2:
            """
            Combined with terminology translation
            """
            if not self.term_dict:
                transed_section["trans_content"] = await self._request_llm_for_trans(
                    pm.section_system_prompt,
                    section["content"],
                    fail_part=section_num,
                    type="sec",
                    session=session
                )
            else:
                transed_section["trans_content"] = await self._request_llm_for_trans_with_terms(
                                                            pm.section_system_prompt_with_dict,
                                                            section["content"], 
                                                            fail_part=section_num,
                                                            type="sec",
                                                            session=session
                                                            )
                
            try:
                if self.update_term == True:
                    src_text = self._extract_text_from_tex(transed_section["content"])
                    tgt_text = self._extract_text_from_tex(transed_section["trans_content"])
                    term_text = await self._request_llm_for_extract_terms(pm.extract_terminology_system_prompt,
                                                            src_text,
                                                            tgt_text,
                                                            session=session
                                                            )

                    # self._updated_term_dict(term_text)
                    self._updated_term_dict_v2(term_text)
            except Exception as e:
                return transed_section

        return transed_section

    async def _translate_caption(self, caption: Dict[str, Any], session: aiohttp.ClientSession, error_message=None) -> Dict[str, Any]:
        """
        Translates the captions of the input data.
        """
        transed_caption = caption.copy()
        placeholder = caption["placeholder"]
        if self.trans_mode == 0:
            transed_caption["trans_content"] = await self._request_llm_for_trans(pm.caption_system_prompt,
                                                        caption["content"],
                                                        fail_part=placeholder,
                                                        type="cap",
                                                        session=session
                                                        )
        elif self.trans_mode == 1:
            """先不改"""
            print("translate_caption_mode_1")
            transed_caption["trans_content"] = await self._request_llm_for_retrans_error_parts(pm.retrans_error_parts_system_prompt,
                                                                                         part=transed_caption,
                                                                                         error_message=error_message,
                                                                                         fail_part=placeholder,
                                                                                         type="cap",
                                                                                         session=session)
            
        elif self.trans_mode == 2:
            if not self.term_dict:
                transed_caption["trans_content"] = await self._request_llm_for_trans(pm.caption_system_prompt,
                                                        caption["content"], 
                                                        fail_part=placeholder,
                                                        type="cap",
                                                        session=session
                                                        )
            else:
                transed_caption["trans_content"] = await self._request_llm_for_trans_with_terms(pm.caption_system_prompt_with_dict,
                                                                                          caption["content"],
                                                                                          fail_part=placeholder,
                                                                                          type="cap",
                                                                                          session=session)
            try:
                if self.update_term == True:
                    src_text = self._extract_text_from_tex(transed_caption["content"])
                    tgt_text = self._extract_text_from_tex(transed_caption["trans_content"])
                    term_text = await self._request_llm_for_extract_terms(pm.extract_terminology_system_prompt,
                                                            src_text,
                                                            tgt_text,
                                                            session=session
                                                            )

                    # self._updated_term_dict(term_text)
                    self._updated_term_dict_v2(term_text)
            except Exception as e:
                return transed_caption

        return transed_caption

    async def _translate_env(self, env: Dict[str, Any], session: aiohttp.ClientSession, error_message=None) -> Dict[str, Any]:
        """
        Translates an environment block (env) based on whether translation is needed.
        """
        transed_env = env.copy()
        placeholder = env["placeholder"]
        if self.trans_mode == 0: # sum
            if env["need_trans"]:
                transed_env["trans_content"] = await self._request_llm_for_trans(pm.env_system_prompt,
                                                            env["content"], 
                                                            fail_part=placeholder,
                                                            type="env",
                                                            session=session
                                                            )                
            else:
                transed_env["trans_content"] = env["content"]
        elif self.trans_mode == 1:
                transed_env["trans_content"] = await self._request_llm_for_retrans_error_parts(pm.retrans_error_parts_system_prompt,
                                                                                         part=transed_env,
                                                                                         error_message=error_message,
                                                                                         fail_part=placeholder,
                                                                                         type="env",
                                                                                         session = session)
        elif self.trans_mode == 2: # dict or sum+dict
            if not self.term_dict:
                if env["need_trans"]:
                    transed_env["trans_content"] = await self._request_llm_for_trans(pm.env_system_prompt,
                                                            env["content"], 
                                                            fail_part=placeholder,
                                                            type="env",
                                                            session=session
                                                            )
                else:
                    transed_env["trans_content"] = env["content"]
            else:
                if env["need_trans"]:
                    transed_env["trans_content"] = await self._request_llm_for_trans_with_terms(pm.env_system_prompt_with_dict,
                                                                                            env["content"],
                                                                                            fail_part=placeholder,
                                                                                            type="env",
                                                                                            session=session)
                else:
                    transed_env["trans_content"] = env["content"]

            if env["need_trans"]:
                try:
                    if self.update_term == True:
                        src_text = self._extract_text_from_tex(transed_env["content"])
                        tgt_text = self._extract_text_from_tex(transed_env["trans_content"])
                        text = await self._request_llm_for_extract_terms(pm.extract_terminology_system_prompt,
                                                                src_text,
                                                                tgt_text,
                                                                session=session
                                                                )

                            # self._updated_term_dict(term_text)
                        self._updated_term_dict_v2(text)
                except Exception as e:
                    return transed_env


        return transed_env

    async def _request_llm_for_trans(self,
                                     system_prompt: str,
                                     text: str,
                                     fail_part: str,
                                     type: str,
                                     session: aiohttp.ClientSession) -> str:
        
        payload = {
            "model": f"{self.model}",
            "messages": [
                {"role": "system", "content": f"{system_prompt}"},
                {"role": "user", "content": f"{text}"}
            ],
            "temperature": 0.7,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        for attempt in range(1, 4):
            try:
                async with session.post(self.base_url, json=payload, headers=headers, timeout=100) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < 3:
                    await asyncio.sleep(5)
                else:
                    self.have_fail_parts = True
                    if type == 'sec':
                        self.fail_section_nums.append(fail_part)
                    elif type == 'cap':
                        self.fail_caption_phs.append(fail_part)
                    else:
                        self.fail_env_phs.append(fail_part)

                    print(f"❌ Failed to translate text, return the original text:{fail_part}. {e}")
                    return text

    async def _request_llm_for_trans_with_terms(self,
                                          system_prompt: str,
                                          text: str,
                                          fail_part: str,
                                          type: str,
                                          session: aiohttp.ClientSession) -> str:

        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system",
                    "content": f"{system_prompt}\nWhen translating, you must strictly use the following glossary for substitution. This is the highest priority rule to ensure the consistency of terms throughout the text.\n<Glossary>:\n{self.term_dict}\nNow, please translate the following new paragraph. Maintain the terminology from the glossary provided."
                },
                {
                    "role": "user",
                    "content": f"[Current LaTeX Paragraph]:\n{text}"
                }
            ],
            "temperature": 0.7,
            # "max_length": 100000,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        for attempt in range(1, 4):
            try:
                async with session.post(self.base_url, json=payload, headers=headers, timeout=100) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < 3:
                    await asyncio.sleep(5)
                else:
                    self.have_fail_parts = True
                    if type == 'sec':
                        self.fail_section_nums.append(fail_part)
                    elif type == 'cap':
                        self.fail_caption_phs.append(fail_part)
                    else:
                        self.fail_env_phs.append(fail_part)

                    print(f"❌ Failed to translate text, return the original text:{fail_part}. {e}")

                    return text

    async def _request_llm_for_retrans_error_parts(self,
                                                   system_prompt: str,
                                                   part: Dict[str, Any],
                                                   error_message: str,
                                                   fail_part: str,
                                                   type: str,
                                                   session: aiohttp.ClientSession) -> str:

        user_prompt = f"[Original]:\n{part['content']}\n[Translation]:\n{part['trans_content']}\n[Error]:\n{error_message}"
        # print(user_prompt,'\n')
        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system",
                    "content": f"{system_prompt}\nWhen translating, you must strictly use the following glossary for substitution. This is the highest priority rule to ensure the consistency of terms throughout the text.\n<Glossary>:\n{self.term_dict}\nNow, please translate the following new paragraph. Maintain the terminology from the glossary provided."
                },
                {
                    "role": "user",
                    "content": f"{user_prompt}"
                }
            ],
            "temperature": 0.7,
            # "max_length": 100000,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        for attempt in range(1, 4):
            try:
                async with session.post(self.base_url, json=payload, headers=headers, timeout=100) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()

            except requests.exceptions.RequestException as e:
                # print(f"⚠️ The {attempt}th request to translate {fail_part} failed: {e}")
                if attempt < 3:
                    await asyncio.sleep(5)
                else:
                    self.have_fail_parts = True
                    if type == 'sec':
                        self.fail_section_nums.append(fail_part)
                    elif type == 'cap':
                        self.fail_caption_phs.append(fail_part)
                    else:
                        self.fail_env_phs.append(fail_part)

                    print(f"❌ Failed to translate text, return the original text:{fail_part}. {e}")
                    return part["trans_content"]

    async def _request_llm_for_extract_terms(self, system_prompt, src, tgt,
                                       session: aiohttp.ClientSession) -> str:

        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<en source>\n{src}\n<zh translation>\n{tgt}"
                }
            ],
            "temperature": 0.7,
            # "max_length": 100000,
            # "max_tokens": 50
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        for attempt in range(1, 4):
            try:
                async with session.post(self.base_url, json=payload, headers=headers, timeout=100) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < 3:
                    await asyncio.sleep(5)
                else:
                    print(f"⚠️ Failed to extract terms, set N/A.")
                    return "N/A"

    async def _request_llm_for_summary(self, system_prompt: str, text: str, session: aiohttp.ClientSession) -> str:
        """
        Requests the LLM to summarize the given text.
        """
        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<Text to summarize>:\n{text}\n<Summary>:\n"
                }
            ],
            "temperature": 0.7,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(1, 4):
            try:
                async with session.post(self.base_url, json=payload, headers=headers, timeout=100) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < 3:
                    logger.warning(f"Summary attempt {attempt} failed: {e}")
                    await asyncio.sleep(3)
                else:
                    logger.warning("Failed to summarize text, set N/A.")
                    return "N/A"

    async def _request_llm_for_refine_summary(self, system_prompt: str, text: str, sum: str, session: aiohttp.ClientSession) -> str:
        """
        Requests the LLM to refine the given summary.
        """
        payload = {
            "model": f"{self.model}",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{system_prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<prev_summary>:\n{sum}\n<new_section>:\n{text}\n<refined_summary>:\n"
                }
            ],
            "temperature": 0.7,
            "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(1, 4):
            try:
                async with session.post(self.base_url, json=payload, headers=headers, timeout=100) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < 3:
                    logger.warning(f"Refine summary attempt {attempt} failed: {e}")
                    await asyncio.sleep(3)
                else:
                    logger.warning("Failed to refine summary, set N/A.")
                    return "N/A"

    def _updated_term_dict(self, text: str) -> None:
        """
        Updates the term dictionary with new terms.
        """
        pattern = r'"([^"]+)"\s*-\s*"([^"]+)"'
        matches = re.findall(pattern, text)

        seen_lower = {k.lower() for k in self.term_dict}
        
        for en, zh in matches:
            en_lower = en.lower()
            if en_lower not in seen_lower:
                self.term_dict[en] = zh  
                seen_lower.add(en_lower)

        self.save_file(Path(self.output_dir, "term_dict.json"), "json", self.term_dict)

    def _updated_term_dict_v2(self, text: str) -> None:

        new_term_dict = {}
        lines = text.split('\n')[1:]
        for line in lines:
            line = line.strip()
            if not line:
                continue  

            match = re.match(r'^"(.+?)"\s*-\s*"(.+?)"$', line)
            if match:
                english = match.group(1)
                chinese = match.group(2)
                new_term_dict[english] = chinese

        for en, zh in new_term_dict.items():
            if en not in self.term_dict:
                self.term_dict[en] = zh

    def _process_latex_to_eva(self, latex_code):
        latex_code = replace_href(latex_code)
        latex_code = replace_includegraphics(latex_code)
        return latex_code

    def _extract_text_from_tex(self, tex):
        # convert = CustomLatexNodes2Text()
        # text = convert.latex_to_text(tex)
        tex = self._process_latex_to_eva(tex)
        text = LatexNodes2Text().latex_to_text(tex)
        text = delete_ph(text)
        return text
    
    def _merge_with_prev_sections(self, sections: list[dict], idx: int) -> str:
        """
        Merge content of current section with previous two sections (if valid).
        Ignore sections whose 'section' field is "-1" or "0".

        Parameters:
            sections (list of dict): A list of sections, each with keys "section" and "content".
            idx (int): The index of the current section in the list.

        Returns:
            str: The merged content string.
        """
        if not (0 <= idx < len(sections)):
            raise IndexError("Index out of range.")

        merged_content = []
        merged_trans_content = []

        # Check second previous section
        # if idx >= 2:
        #     sec = sections[idx - 2]
        #     if sec["section"] not in {"-1", "0"}:
        #         try:
        #             content = self._extract_text_from_tex(sec["content"])
        #             transed_content = self._extract_text_from_tex(sec["trans_content"])
        #             merged_content.append(content)
        #             merged_trans_content.append(transed_content)
        #         except Exception as e:
        #             pass
                

        # Check first previous section
        if idx >= 1:
            sec = sections[idx - 1]
            if sec["section"] not in {"-1", "0"}:
                try:
                    content = self._extract_text_from_tex(sec["content"])
                    transed_content = self._extract_text_from_tex(sec["trans_content"])
                    merged_content.append(content)
                    merged_trans_content.append(transed_content)
                except Exception as e:
                    pass

        # Always include current section
        try:
            content = self._extract_text_from_tex(sections[idx]["content"])
            transed_content = self._extract_text_from_tex(sections[idx]["trans_content"])
            merged_content.append(content)
            merged_trans_content.append(transed_content)
        except Exception as e:
            pass

        return "\n".join(merged_content)

    def build_term_dict(self):
        if self.user_term:
            df = pd.read_csv(self.user_term, header=None, names=['English Term', 'Chinese Translation'])
            self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
        else:
            arxiv_id = os.path.basename(self.project_dir)
            if self.category.get(arxiv_id):
                term_dict_loaded = False
                for category in self.category[arxiv_id]:
                    file_path = os.path.join('terms', f'{category}.csv')
                    try:
                        df = pd.read_csv(file_path, header=None, names=['English Term', 'Chinese Translation'])
                        self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
                        term_dict_loaded = True

                    except FileNotFoundError:
                        continue

                if not term_dict_loaded:
                    try:
                        df = pd.read_csv('terms/default.csv', header=None,
                                         names=['English Term', 'Chinese Translation'])
                        self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
                    except FileNotFoundError as e:
                        print(f"Error: Default terminology file not found: {e}")
            else:
                try:
                    df = pd.read_csv('terms/default.csv', header=None,
                                     names=['English Term', 'Chinese Translation'])
                    self.term_dict.update(zip(df['English Term'], df['Chinese Translation']))
                except FileNotFoundError as e:
                    print(f"Error: Default terminology file not found: {e}")

    def add_placeholder(self):

        # Add placeholders from caption, env, input, and newcommand to the vocabulary
        caption_path = os.path.join(self.output_dir, "captions_map.json")
        input_path = os.path.join(self.output_dir, "inputs_map.json")
        env_path = os.path.join(self.output_dir, "envs_map.json")
        command_path = os.path.join(self.output_dir, "newcommands_map.json")

        placeholder_list = []

        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "begin" in item:
                placeholder_list.append(item["begin"])
            if "end" in item:
                placeholder_list.append(item["end"])

        with open(env_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "placeholder" in item:
                placeholder_list.append(item["placeholder"])

        with open(caption_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "placeholder" in item:
                placeholder_list.append(item["placeholder"])

        with open(command_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            if "placeholder" in item:
                placeholder_list.append(item["placeholder"])

        for item in placeholder_list:
            self.term_dict[item] = item


```

---

### 📄 app\services\agents\validator_agent.py

```python
"""
Validator Agent

Adapted from prototype system with:
- All Streamlit dependencies removed
- Progress callback mechanism added
- Python logging integrated
- Validation logic completely preserved
"""

from typing import Dict, Any, List, Optional, Callable
from .base_tool_agent import BaseToolAgent
from pathlib import Path
from collections import Counter
from pylatexenc.latexwalker import LatexWalker
import os
import re
import logging

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseToolAgent):
    def __init__(self, 
                 config: Dict[str, Any],
                 project_dir: str = None,
                 output_dir: str = None,
                 on_progress: Optional[Callable[[str, int, str], None]] = None
                 ):
        super().__init__(agent_name="ValidatorAgent", config=config, on_progress=on_progress)
        self.config = config
        self.project_dir = project_dir
        self.output_dir = output_dir

    def execute(self, errors_report: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Validate translated LaTeX content
        
        Args:
            errors_report: Optional previous error report to re-validate specific parts
            
        Returns:
            List of error reports for parts that failed validation
        """
        self.log(f"Starting validation for project: {os.path.basename(self.project_dir)}")
        self.update_progress(10, "Loading JSON maps")
        
        sections = self.read_file(Path(self.output_dir, "sections_map.json"), "json")
        captions = self.read_file(Path(self.output_dir, "captions_map.json"), "json")
        envs = self.read_file(Path(self.output_dir, "envs_map.json"), "json")

        self.update_progress(30, "Extracting parts to validate")
        
        if errors_report is None:
            parts_need_val = self._extract_parts_need_validate(secs=sections,
                                                               caps=captions,
                                                               envs=envs)
        else:
            parts_need_val = self._extract_parts_from_report(secs=sections, 
                                                               caps=captions,
                                                               envs=envs,
                                                               errors_report=errors_report)
        
        self.update_progress(50, f"Validating {len(parts_need_val)} parts")
        
        errors_report = []
        for i, part in enumerate(parts_need_val):
            if i % 10 == 0:
                progress = 50 + int(40 * (i / len(parts_need_val)))
                self.update_progress(progress, f"Validating part {i+1}/{len(parts_need_val)}")
            
            error_report = self._validate(part)
            if error_report:
                errors_report.append(error_report)
        
        if errors_report:
            self.save_file(Path(self.output_dir, "errors_report.json"), "json", errors_report)

        self.update_progress(100, f"Validation complete: {len(errors_report)} errors found")
        self.log(f"Validation complete for {os.path.basename(self.project_dir)}, remaining errors: {len(errors_report)}")
        return errors_report

    def _validate(self, part: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate a single part (section/caption/environment)"""
        command_error = self._validate_command(part)
        ph_error = self._validate_placeholder(part)
        bracket_error = self._validate_closed_brackets(part)
        error_report = {}

        if not command_error and not ph_error and not bracket_error:
            return None
        else: 
            if "section" in part:
                error_report["part"] = "sec"
                error_report["num_or_ph"] = part["section"]
            elif "env_name" in part:
                error_report["part"] = "env"
                error_report["num_or_ph"] = part["placeholder"]
            elif "cap_type" in part:
                error_report["part"] = "cap"
                error_report["num_or_ph"] = part["placeholder"]

            if command_error:
                error_report["command_error"] = command_error
            if ph_error:
                error_report["ph_error"] = ph_error
            if bracket_error:
                error_report["bracket_error"] = bracket_error

        return error_report

    def _validate_command(self, part: Dict[str, Any]) -> Optional[str]:
        """Validate LaTeX commands are preserved in translation"""
        content = part.get("content", "")
        trans = part.get("trans_content", "")

        src_counter = self.extract_command_counts(content)
        trans_counter = self.extract_command_counts(trans)
        
        if src_counter == trans_counter:
            return None

        errors = []
        for elem, count in src_counter.items():
            match = re.findall(re.escape(elem), trans)
            if len(match) < count:
                errors.append(f"'{elem}' — expected {count}, found {len(match)}")

        if errors:
            return "LaTeX command translation error or is missing:\n" + "\n".join(errors)
        return None        

    def _validate_placeholder(self, part: Dict[str, Any]) -> Optional[str]:
        """Validate placeholders are preserved in translation"""
        original_placeholders = self._extract_placeholders(part["content"])
        translated_placeholders = self._extract_placeholders(part["trans_content"])
        missing = original_placeholders - translated_placeholders
        extra = translated_placeholders - original_placeholders
        errors = []
        
        if missing:
            errors.append(f"Missing placeholders: {', '.join(sorted(missing))} translation error or is missing!") 
        if extra:
            errors.append(f"Extra placeholders: {', '.join(sorted(extra))} translation error or is redundant")
        
        return "\n".join(errors) if errors else None
        
    def _validate_closed_brackets(self, part: Dict[str, Any]) -> Optional[str]:
        """Validate brackets are properly closed"""
        content = part.get("content", "")
        trans_content = part.get("trans_content", "")
        org_errors = self._find_brackets_errors(content, org=1)
        errors = self._find_brackets_errors(trans_content)

        if errors and not org_errors:
            return "Brackets error:\n" + "\n".join(errors)
        else:
            return None
        
    def _find_brackets_errors(self, content, org=None):
        """Find unmatched brackets in content"""
        if org:
            bracket_pairs = {'[': ']', '{': '}'}    
        else:
            bracket_pairs = {'(': ')', '[': ']', '{': '}'}
        
        opening_brackets = set(bracket_pairs.keys())
        closing_brackets = set(bracket_pairs.values())

        stack = []
        errors = []
        for idx, char in enumerate(content):
            if char in opening_brackets:
                stack.append((char, idx))
            elif char in closing_brackets:
                if not stack:
                    fragment = content[max(0, idx - 10): idx + 10]
                    errors.append(f"Extra closing bracket '{char}' at position {idx}, context: {fragment}")
                else:
                    last_open, open_idx = stack.pop()
                    if bracket_pairs[last_open] != char:
                        fragment = content[open_idx: idx + 1]
                        errors.append(f"Bracket mismatch: '{last_open}' opened at {open_idx} does not match '{char}' at {idx}, fragment: {fragment}")

        # Any unmatched opening brackets left in stack
        for open_bracket, pos in stack:
            fragment = content[pos: pos + 20]
            errors.append(f"Unmatched opening bracket '{open_bracket}' at position {pos}, fragment: {fragment}")

        return errors

    def extract_command_counts(self, latex_code: str) -> Counter:
        """Extract and count LaTeX commands using AST"""
        walker = LatexWalker(latex_code)
        nodes, _, _ = walker.get_latex_nodes()
        counter = Counter()
        
        ignored_commands = {'eg', 'ie'}

        def recurse(nodes):
            for node in nodes:
                clsname = node.__class__.__name__

                if clsname == "LatexMacroNode":
                    macro_name = node.macroname

                    if macro_name in ignored_commands:
                        continue
                    if len(macro_name) == 1 and not macro_name.isalpha():
                        continue

                    command = f"\\{macro_name}"
                    counter[command] += 1

                    if node.nodeargd:
                        for arg in node.nodeargd.argnlist:
                            if arg is not None:
                                recurse([arg])

                elif clsname == "LatexEnvironmentNode":
                    env_name = node.environmentname
                    counter[f"\\begin{{{env_name}}}"] += 1
                    recurse(node.nodelist)
                    counter[f"\\end{{{env_name}}}"] += 1

                elif hasattr(node, 'nodelist') and node.nodelist:
                    recurse(node.nodelist)

        recurse(nodes)
        return counter

    def _extract_placeholders(self, content):
        """Extract all placeholders from content"""
        input_pattern = re.compile(r"<PLACEHOLDER_[^>]+?_begin>|<PLACEHOLDER_[^>]+?_end>")
        placeholder_pattern_cap = re.compile(r"<PLACEHOLDER_CAP_\d+>")
        placeholder_pattern_env = re.compile(r"<PLACEHOLDER_ENV_\d+>")
        placeholders = set()
        for pattern in [input_pattern, placeholder_pattern_cap, placeholder_pattern_env]:
            placeholders.update(pattern.findall(content))
        return placeholders

    def _extract_parts_need_validate(self, secs, caps, envs):
        """Extract parts that need validation"""
        secs_need_val = [sec for sec in secs if sec["section"] != "0" and sec["section"] != "-1"]
        caps_need_val = caps
        
        if envs:
            if "need_trans" in envs[0]:
                envs_need_val = [env for env in envs if env["need_trans"]]
            else:
                envs_need_val = [env for env in envs if env["content"] != env["trans_content"]]
        else:
            envs_need_val = []

        return secs_need_val + caps_need_val + envs_need_val
    
    def _extract_parts_from_report(
        self,
        secs: List[Dict],
        caps: List[Dict],
        envs: List[Dict],
        errors_report: List[Dict]) -> List[Dict]:
        """Extract specific parts from error report for re-validation"""
        section_lookup = {s["section"]: s for s in secs}
        caption_lookup = {c["placeholder"]: c for c in caps}
        environment_lookup = {e["placeholder"]: e for e in envs}
        
        parts_to_validate = []
        
        for error in errors_report:
            part_type = error.get("part")
            identifier = error.get("num_or_ph")
            
            if not part_type or not identifier:
                continue
                
            part = None
            if part_type == "sec":
                part = section_lookup.get(identifier)
            elif part_type == "cap":
                part = caption_lookup.get(identifier)
            elif part_type == "env":
                part = environment_lookup.get(identifier)
            
            if part:
                parts_to_validate.append(part)
                
        return parts_to_validate

```

---

### 📄 app\services\latex\compiler.py

```python
"""
Intelligent LaTeX Compiler with Fallback

Implements multi-stage compilation strategy:
1. Try pdflatex first
2. If fails or has errors, try xelatex
3. Compare error counts from .log files
4. Select PDF with fewer errors or return best available
"""

import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)


class CompilationResult:
    """Result of a compilation attempt"""
    
    def __init__(
        self,
        success: bool,
        pdf_path: Optional[str] = None,
        log_path: Optional[str] = None,
        error_count: int = 0,
        errors: Optional[List[str]] = None,
        exit_code: int = 0
    ):
        self.success = success
        self.pdf_path = pdf_path
        self.log_path = log_path
        self.error_count = error_count
        self.errors = errors or []
        self.exit_code = exit_code


def parse_log_errors(log_path: str) -> Tuple[int, List[str]]:
    """
    Parse LaTeX .log file and count errors
    
    Matches patterns:
    - ! LaTeX Error
    - ! Undefined control sequence
    - ! Missing
    
    Args:
        log_path: Path to .log file
    
    Returns:
        Tuple of (error_count, error_lines)
    """
    if not os.path.exists(log_path):
        return 0, []
    
    error_patterns = [
        r'^! LaTeX Error',
        r'^! Undefined control sequence',
        r'^! Missing',
        r'^! .*Error',
    ]
    
    errors = []
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                for pattern in error_patterns:
                    if re.match(pattern, line):
                        errors.append(line)
                        break
    except Exception as e:
        logger.warning(f"Failed to parse log file {log_path}: {e}")
        return 0, []
    
    return len(errors), errors


def compile_latex(
    tex_file: str,
    output_dir: str,
    engine: str = "pdflatex",
    max_runs: int = 2
) -> CompilationResult:
    """
    Compile LaTeX file with specified engine
    
    Args:
        tex_file: Path to .tex file
        output_dir: Output directory
        engine: LaTeX engine ("pdflatex" or "xelatex")
        max_runs: Maximum compilation runs (for references)
    
    Returns:
        CompilationResult object
    """
    if not os.path.exists(tex_file):
        logger.error(f"TeX file not found: {tex_file}")
        return CompilationResult(success=False, exit_code=-1)
    
    tex_path = Path(tex_file)
    tex_filename = tex_path.name
    tex_basename = tex_path.stem
    
    # Prepare output directory
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Compiling {tex_filename} with {engine}...")
    
    # Run compilation (may need multiple runs for references)
    last_exit_code = 0
    for run in range(max_runs):
        try:
            # -interaction=nonstopmode: continue on errors
            # -halt-on-error: stop on first error (we use nonstopmode instead)
            # -output-directory: specify output directory
            cmd = [
                engine,
                "-interaction=nonstopmode",
                "-output-directory", str(output_dir),
                tex_filename
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(tex_path.parent),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            last_exit_code = result.returncode
            
            logger.info(f"{engine} run {run + 1}/{max_runs} completed with exit code {result.returncode}")
            
        except subprocess.TimeoutExpired:
            logger.error(f"{engine} compilation timed out")
            return CompilationResult(success=False, exit_code=-2)
        except Exception as e:
            logger.error(f"{engine} compilation failed: {e}")
            return CompilationResult(success=False, exit_code=-3)
    
    # Check for output PDF
    pdf_path = out_path / f"{tex_basename}.pdf"
    log_path = out_path / f"{tex_basename}.log"
    
    pdf_exists = pdf_path.exists()
    
    # Parse errors from log file
    error_count = 0
    errors = []
    if log_path.exists():
        error_count, errors = parse_log_errors(str(log_path))
    
    success = pdf_exists and error_count == 0
    
    logger.info(
        f"{engine} compilation result: "
        f"PDF={'✓' if pdf_exists else '✗'}, "
        f"Errors={error_count}, "
        f"Exit Code={last_exit_code}"
    )
    
    return CompilationResult(
        success=success,
        pdf_path=str(pdf_path) if pdf_exists else None,
        log_path=str(log_path) if log_path.exists() else None,
        error_count=error_count,
        errors=errors,
        exit_code=last_exit_code
    )


def compile_with_fallback(tex_file: str, output_dir: str) -> Dict:
    """
    Intelligent LaTeX compilation with fallback strategy
    
    Strategy:
    1. Try pdflatex first
    2. If perfect (zero errors), return immediately
    3. If failed or has errors, try xelatex
    4. Compare error counts and select best PDF
    5. If both fail to produce PDF, raise exception
    
    Args:
        tex_file: Path to .tex file
        output_dir: Output directory
    
    Returns:
        Dictionary with:
        - pdf_path: Path to best PDF
        - status: "completed" | "completed_with_warnings" | "failed_compilation"
        - engine: Engine that produced the PDF
        - error_count: Number of errors in selected PDF
        - warnings: Warning message if errors present
        - errors: Combined error details if compilation failed
    
    Raises:
        Exception: If both compilers fail to produce any PDF
    """
    logger.info(f"Starting intelligent compilation for {tex_file}")
    
    # Step 1: Try pdflatex
    pdflatex_result = compile_latex(tex_file, output_dir, engine="pdflatex")
    
    # Perfect compilation - return immediately
    if pdflatex_result.success and pdflatex_result.error_count == 0:
        logger.info("✅ pdflatex produced perfect compilation (zero errors)")
        return {
            "pdf_path": pdflatex_result.pdf_path,
            "status": "completed",
            "engine": "pdflatex",
            "error_count": 0,
            "warnings": None,
            "errors": None
        }
    
    # Step 2: Try xelatex fallback
    logger.info("⚡ Attempting xelatex fallback...")
    xelatex_result = compile_latex(tex_file, output_dir, engine="xelatex")
    
    # Perfect xelatex compilation
    if xelatex_result.success and xelatex_result.error_count == 0:
        logger.info("✅ xelatex produced perfect compilation (zero errors)")
        return {
            "pdf_path": xelatex_result.pdf_path,
            "status": "completed",
            "engine": "xelatex",
            "error_count": 0,
            "warnings": None,
            "errors": None
        }
    
    # Step 3: Compare results and select best
    pdflatex_has_pdf = pdflatex_result.pdf_path is not None
    xelatex_has_pdf = xelatex_result.pdf_path is not None
    
    # Case 1: Only pdflatex produced PDF
    if pdflatex_has_pdf and not xelatex_has_pdf:
        logger.warning(f"⚠️ Only pdflatex produced PDF (with {pdflatex_result.error_count} errors)")
        return {
            "pdf_path": pdflatex_result.pdf_path,
            "status": "completed_with_warnings",
            "engine": "pdflatex",
            "error_count": pdflatex_result.error_count,
            "warnings": f"Compilation completed with {pdflatex_result.error_count} errors. xelatex failed to produce output.",
            "errors": None
        }
    
    # Case 2: Only xelatex produced PDF
    if xelatex_has_pdf and not pdflatex_has_pdf:
        logger.warning(f"⚠️ Only xelatex produced PDF (with {xelatex_result.error_count} errors)")
        return {
            "pdf_path": xelatex_result.pdf_path,
            "status": "completed_with_warnings",
            "engine": "xelatex",
            "error_count": xelatex_result.error_count,
            "warnings": f"Compilation completed with {xelatex_result.error_count} errors. pdflatex failed to produce output.",
            "errors": None
        }
    
    # Case 3: Both produced PDFs - select one with fewer errors
    if pdflatex_has_pdf and xelatex_has_pdf:
        if pdflatex_result.error_count <= xelatex_result.error_count:
            engine = "pdflatex"
            result = pdflatex_result
        else:
            engine = "xelatex"
            result = xelatex_result
        
        logger.warning(
            f"⚠️ Selected {engine} PDF with {result.error_count} errors "
            f"(pdflatex: {pdflatex_result.error_count}, xelatex: {xelatex_result.error_count})"
        )
        
        return {
            "pdf_path": result.pdf_path,
            "status": "completed_with_warnings",
            "engine": engine,
            "error_count": result.error_count,
            "warnings": f"Compilation completed with {result.error_count} errors using {engine}.",
            "errors": None
        }
    
    # Case 4: Both failed to produce PDF
    logger.error("❌ Both pdflatex and xelatex failed to produce PDF")
    
    # Combine error messages
    combined_errors = "Compilation failed with both engines:\n\n"
    combined_errors += f"pdflatex ({pdflatex_result.error_count} errors):\n"
    combined_errors += "\n".join(pdflatex_result.errors[:10])  # First 10 errors
    combined_errors += f"\n\nxelatex ({xelatex_result.error_count} errors):\n"
    combined_errors += "\n".join(xelatex_result.errors[:10])
    
    return {
        "pdf_path": None,
        "status": "failed_compilation",
        "engine": None,
        "error_count": pdflatex_result.error_count + xelatex_result.error_count,
        "warnings": None,
        "errors": combined_errors
    }


class LaTeXCompiler:
    """
    LaTeX Compiler wrapper for backward compatibility with prototype system
    """
    
    def __init__(self, output_latex_dir: str):
        self.output_latex_dir = output_latex_dir
    
    def compile(self) -> Optional[str]:
        """
        Compile LaTeX document in the output directory
        
        Returns:
            Path to PDF file or None if compilation failed
        """
        # Find main .tex file
        tex_files = list(Path(self.output_latex_dir).glob("*.tex"))
        
        if not tex_files:
            logger.error(f"No .tex files found in {self.output_latex_dir}")
            return None
        
        # Try to find main.tex or the first .tex file
        main_tex = None
        for tex in tex_files:
            if tex.stem.lower() in ["main", "paper", "article"]:
                main_tex = tex
                break
        
        if main_tex is None:
            main_tex = tex_files[0]
        
        logger.info(f"Compiling {main_tex.name}...")
        
        try:
            result = compile_with_fallback(str(main_tex), self.output_latex_dir)
            
            if result["pdf_path"]:
                logger.info(f"✅ Compilation succeeded: {result['pdf_path']}")
                return result["pdf_path"]
            else:
                logger.error(f"❌ Compilation failed: {result.get('errors', 'Unknown error')}")
                raise Exception(result.get("errors", "Compilation failed"))
        
        except Exception as e:
            logger.error(f"Compilation error: {e}")
            raise

```

---

### 📄 app\services\latex\parser.py

```python
"""
LaTeX Parser with AST Processing

Adapted from prototype system with:
- All Streamlit dependencies removed  
- Progress callback mechanism added
- Python logging integrated
- sys.stderr redirection removed
"""

from typing import Any, Dict, Optional, Callable
from .utils import *
import tiktoken
import logging

logger = logging.getLogger(__name__)


class LatexParser:
    def __init__(self, dir: str, output_dir: str):
        self.inputs_json = []
        self.envs_json = []
        self.captions_json = []
        self.newcommands_json = []
        self.sections_json = []
        self.dir = dir  # LaTeX project directory
        self.output_dir = output_dir  # Output directory for parsed files
        self.env_count = 0
        self.caption_count = 0

    def parse(self, on_progress: Optional[Callable[[str, int, str], None]] = None):
        """
        Parse the LaTeX document and return the parsed content.
        
        Args:
            on_progress: Optional callback function(stage, percentage, message)
        """
        if on_progress:
            on_progress("parsing", 0, "Starting LaTeX parsing...")
        
        logger.info("Starting LaTeX document parsing")

        main_tex_file = find_main_tex_file(self.dir)
        if not main_tex_file:
            logger.warning("No main tex file found in directory")
            print("⚠️ Warning: There is no main tex file to compile in this directory.")
            return None

        if on_progress:
            on_progress("parsing", 10, "Finding main tex file...")

        main_tex = read_tex_file(main_tex_file)
        if not main_tex:
            logger.warning("Main tex file is empty")
            print("⚠️ Warning: The main tex file is empty.")
            return None
        
        if on_progress:
            on_progress("parsing", 20, "Reading main tex file...")

        main_tex = remove_comments(main_tex)
        full_tex = self._merge_inputs(main_tex)
        full_tex = self._extract_newcommands(full_tex)

        # Delete redundant blank lines to prevent LLM from missing placeholders during translation
        full_tex = compress_newlines(full_tex)

        self._split_to_sections(full_tex)

        # Merge short sections to avoid too many sections
        self._merge_short_sections(min_tokens=50)

        total_sections = len(self.sections_json)
        if on_progress:
            on_progress("parsing", 80, f"Processing {total_sections} sections...")

        for i, section in enumerate(self.sections_json):
            if on_progress:
                progress = 80 + int(15 * (i / total_sections))
                on_progress("parsing", progress, f"Processing section {i+1}/{total_sections}")

            if section["section"] == "0" or section["section"] == "-1":
                section_content = self._extract_captions(section["content"])
                self.sections_json[i]["trans_content"] = self._extract_envs(section_content)
                self.sections_json[i]["content"] = self.sections_json[i]["trans_content"]
            else:
                section_content = self._extract_captions(section["content"])
                self.sections_json[i]["content"] = self._extract_envs(section_content)

        if on_progress:
            on_progress("parsing", 100, "Parsing complete")
        
        logger.info(f"Parsing complete: {total_sections} sections processed")

    def _merge_inputs(self, tex: str) -> str:
        """
        Merge all the inputs in the main tex file and generate a json file for the inputs.
        """
        main_tex = remove_comments(tex)
        command_name = r'input|include'
        pattern_input = get_command_pattern(command_name)
        pos = 0
        
        while True:
            result = pattern_input.search(main_tex, pos)
            if result is None:
                break
            begin, end = result.span()
            pos = result.end()
            match = result.group(4)
            inputfilepath = os.path.join(self.dir, match)

            if os.path.exists(f'{inputfilepath}'):
                inputfilepath = f'{inputfilepath}'
            elif os.path.exists(f'{inputfilepath}.tex'):
                inputfilepath = f'{inputfilepath}.tex'
            else:
                logger.warning(f"File not found: {inputfilepath}.tex or {inputfilepath}")
                print(f"⚠️ Warning: File not found: {inputfilepath}.tex or {inputfilepath}")
                pos = result.end()
                continue

            input_tex = read_tex_file(inputfilepath)
            input_tex = remove_comments(input_tex)
            input_begin = f"<PLACEHOLDER_{match}_begin>"
            input_end = f"<PLACEHOLDER_{match}_end>"
            input_tex = input_begin + input_tex + input_end
            main_tex = main_tex[:begin] + input_tex + main_tex[end:]
            self.inputs_json.append({
                "command": result.group(0),
                "begin": input_begin,
                "end": input_end,
                "path": match
            })

        return main_tex

    def _extract_envs(self, tex: str) -> str:
        """
        Extract all the environments in the full tex and generate a json file for the environments.
        The environments are replaced with placeholders in the full tex.
        """
        full_tex = remove_comments(tex)
        command_name = r'.*?'
        pattern_env = get_env_pattern(command_name)
        placeholder_pattern_cap = r"<PLACEHOLDER_CAP_\d+>"
        
        no_translate_envs = [
            'equation', 'align', 'align*', 'gather', 'gather*', 'verbatim', 'verbatim*', 'lstlisting*', 'minted', 'minted*',
            'equation*', 'alignat', 'alignat*', 'flalign', 'flalign*', 'split', 'split*', 'cases', 'cases*', 'subequations',
            'figure', 'figure*', 'wrapfigure', 'SCfigure', 'tikzpicture', 'CJK', 'scope',
            'tabularx', 'tabulary', 'longtable*', 'sidewaystable', 'table', 'table*', 'tabular', 'tabular*', 'longtable',
            'multline', 'multline*', 'lstlisting', 'tcolorbox', 'thebibliography', 'bibliography', 'bibitem',
            'algorithm', 'algorithmic', 'algorithmicx', 'algorithm2e', 'algorithmicx*', 'algorithmic*', 'algorithm*'
        ]
        
        while True:
            result = pattern_env.search(full_tex)
            if result is None:
                break
            self.env_count += 1
            env_name = result.group(1)
            env_content = result.group(0)
            placeholders_cap_in_env = re.findall(placeholder_pattern_cap, env_content)

            need_trans = True

            if env_name in no_translate_envs:
                need_trans = False

            if placeholders_cap_in_env:
                # If there are placeholders in the environment, we do not translate it.
                need_trans = False

            placeholder = f"<PLACEHOLDER_ENV_{self.env_count}>"
            full_tex = full_tex.replace(env_content, placeholder, 1)
            self.envs_json.append({
                "placeholder": placeholder,
                "env_name": env_name,
                "content": env_content,
                "trans_content": '',
                "need_trans": need_trans
            })
        
        return full_tex

    def _extract_captions(self, tex: str) -> str:
        """
        Extract all the captions in the full tex and generate a json file for the captions.
        The captions are replaced with placeholders in the full tex.
        """
        full_tex = remove_comments(tex)
        command_name = r'caption|caption\*|subcaption|subcaption\*|title|keywords|abstract|icmltitle|icmltitlerunning'
        pattern_caption = get_command_pattern(command_name)

        while True:
            result = pattern_caption.search(full_tex)
            if result is None:
                break
            self.caption_count += 1
            placeholder = f"<PLACEHOLDER_CAP_{self.caption_count}>"
            full_tex = full_tex.replace(result.group(0), placeholder, 1)
            self.captions_json.append({
                "placeholder": placeholder,
                "cap_type": result.group(1),
                "content": result.group(0),
                "trans_content": ''
            })

        return full_tex
    
    def _extract_newcommands(self, tex: str) -> str:
        """
        Extract all the newcommands in the full tex and generate a json file for the newcommands.
        """
        def get_nonNone(*args):
            result = [arg for arg in args if arg is not None]
            assert len(result) == 1
            return result[0]
        
        full_tex = remove_comments(tex)
        pattern = get_newcommand_pattern()
        count = 0
        
        while True:
            match = pattern.search(full_tex)
            if match is None:
                break
            name1 = match.group(1)
            name2 = match.group(2)
            name = get_nonNone(name1, name2)
            n_arguments = match.group(3)
            if n_arguments is None:
                n_arguments = 0
            else:
                n_arguments = int(n_arguments)
            placeholder = f"<PLACEHOLDER_NEWCOMMAND_{count}>"
            full_tex = full_tex.replace(match.group(0), placeholder, 1)
            self.newcommands_json.append({
                "placeholder": placeholder,
                "name": name,
                "content": match.group(0)
            })
            count += 1

        return full_tex
    
    def _split_to_sections(self, tex: str) -> Any:
        """
        Split the full tex to sections and generate a json file for the sections.
        """
        full_tex = remove_comments(tex)
        command_name_section = r'section|subsection|subsubsection|section\*|subsection\*|subsubsection\*'
        pattern_section = get_command_pattern(command_name_section)
        begin_document_pattern = get_begin_document_pattern()
        begin_document_match = begin_document_pattern.search(full_tex)
        preamble = full_tex[:begin_document_match.start()] if begin_document_match else full_tex

        self.sections_json.append({
            "section": "-1",
            "content": preamble,
            "trans_content": preamble
        })

        document = full_tex[begin_document_match.start():] if begin_document_match else full_tex

        section_count = 0
        subsection_count = 0
        subsubsection_count = 0
        first_section_match = pattern_section.search(document)

        if not first_section_match:
            logger.info("No sections found in document")
            print("There is no section in the full tex.")
            self.sections_json.append({
                "section": "0",
                "content": document,
                "trans_content": ''
            })
            return

        before_section = document[:first_section_match.start()] if first_section_match else document
        sections_tex = document[first_section_match.start():] if first_section_match else document
        
        self.sections_json.append({
            "section": "0",
            "content": before_section,
            "trans_content": before_section
        })

        last_pos = 0
        last_result = first_section_match

        for result in pattern_section.finditer(sections_tex):
            if last_pos != result.start():
                if last_result.group(1) == "section" or last_result.group(1) == "section*":
                    section_count += 1
                    subsection_count = 0
                    subsubsection_count = 0
                    self.sections_json.append({
                        "section": f'{section_count}',
                        "content": sections_tex[last_pos:result.start()],
                        "trans_content": ''
                    })
                elif last_result.group(1) == "subsection" or last_result.group(1) == "subsection*":
                    subsection_count += 1
                    subsubsection_count = 0
                    self.sections_json.append({
                        "section": f'{section_count}_{subsection_count}',
                        "content": sections_tex[last_pos:result.start()],
                        "trans_content": ''
                    })
                elif last_result.group(1) == "subsubsection" or last_result.group(1) == "subsubsection*":
                    subsubsection_count += 1
                    self.sections_json.append({
                        "section": f'{section_count}_{subsection_count}_{subsubsection_count}',
                        "content": sections_tex[last_pos:result.start()],
                        "trans_content": ''
                    })
            last_pos = result.start()
            last_result = result

        if last_result.group(1) == "section" or last_result.group(1) == "section*":
            section_count += 1
            subsection_count = 0
            subsubsection_count = 0
            self.sections_json.append({
                "section": f'{section_count}',
                "content": sections_tex[last_pos:],
                "trans_content": ''
            })
        elif last_result.group(1) == "subsection" or last_result.group(1) == "subsection*":
            subsection_count += 1
            subsubsection_count = 0
            self.sections_json.append({
                "section": f'{section_count}_{subsection_count}',
                "content": sections_tex[last_pos:],
                "trans_content": ''
            })
        elif last_result.group(1) == "subsubsection" or last_result.group(1) == "subsubsection*":
            subsubsection_count += 1
            self.sections_json.append({
                "section": f'{section_count}_{subsection_count}_{subsubsection_count}',
                "content": sections_tex[last_pos:],
                "trans_content": ''
            })

    def _merge_short_sections(self, min_tokens=20):
        """
        Merge sections that are too short to save the number of API requests
        """
        enc = tiktoken.encoding_for_model("gpt-4")
        merged_sections = []
        i = 0
        sections = self.sections_json

        while i < len(sections):
            combined_content = sections[i]["content"]
            combined_section_ids = [sections[i]["section"]]
            total_tokens = len(enc.encode(combined_content))
            start_section = sections[i]
            j = i + 1

            while total_tokens < min_tokens and j < len(sections):
                combined_content += "\n" + sections[j]["content"]
                combined_section_ids.append(sections[j]["section"])
                total_tokens = len(enc.encode(combined_content))
                j += 1

            if total_tokens < min_tokens and len(merged_sections) > 0:
                merged_sections[-1]["content"] += "\n" + combined_content
                merged_sections[-1]["section"] += "+" + "+".join(combined_section_ids)
                logger.debug(f"Merged sections: {merged_sections[-1]['section']}")
                print(merged_sections[-1]["section"])
            else:
                merged_section = start_section.copy()
                merged_section["content"] = combined_content
                merged_section["section"] = "+".join(combined_section_ids)
                merged_sections.append(merged_section)

            i = j

        self.sections_json = merged_sections

```

---

### 📄 app\services\latex\prompts.py

```python
import argparse
import toml
import os
import sys

# base_dir = os.getcwd()
# sys.path.append(base_dir)


# parser = argparse.ArgumentParser()
# parser.add_argument("--config", type=str, default="config/default.toml")
# args = parser.parse_args()
# config = toml.load(args.config)
#
# #这里后续应该接收args
# target_language = config.get("target_language", "ch")
caption_system_prompt = None
section_system_prompt = None
env_system_prompt = None
caption_system_prompt_with_dict = None
section_system_prompt_with_dict = None
env_system_prompt_with_dict = None
set_need_trans_for_envs_system_prompt = None
retrans_error_parts_system_prompt = None
extract_terminology_system_prompt = None
refine_summary_system_prompt = None
section_system_prompt_with_sum = None
caption_system_prompt_with_sum = None
env_system_prompt_with_sum = None
section_system_prompt_with_terms_sum = None
section_system_prompt_with_prev = None
section_system_prompt_with_terms_prev = None


def init_prompts(source_lang: str, target_lang: str):
    global caption_system_prompt, section_system_prompt, env_system_prompt, caption_system_prompt_with_dict, section_system_prompt_with_dict, \
        env_system_prompt_with_dict, set_need_trans_for_envs_system_prompt, retrans_error_parts_system_prompt, extract_terminology_system_prompt, \
        get_summary_system_prompt, refine_summary_system_prompt, section_system_prompt_with_sum, caption_system_prompt_with_sum, env_system_prompt_with_sum, \
        section_system_prompt_with_terms_sum, section_system_prompt_with_prev, section_system_prompt_with_terms_prev

    if(source_lang == "en"):
        source_lang = "English"
    if(target_lang == "ch"):
        target_lang = "Chinese"


    caption_system_prompt = f"""
    ... [Prompt Content Hidden: 2780 chars / 17 lines] ...
    """
    section_system_prompt = f"""
    ... [Prompt Content Hidden: 3209 chars / 19 lines] ...
    """
    env_system_prompt = f"""
    ... [Prompt Content Hidden: 2756 chars / 17 lines] ...
    """

    caption_system_prompt_with_dict = f"""
    ... [Prompt Content Hidden: 2789 chars / 17 lines] ...
    """

    section_system_prompt_with_dict = f"""
    ... [Prompt Content Hidden: 2974 chars / 18 lines] ...
    """
    env_system_prompt_with_dict = f"""
    ... [Prompt Content Hidden: 2756 chars / 17 lines] ...
    """

    set_need_trans_for_envs_system_prompt = f"""
    ... [Prompt Content Hidden: 2231 chars / 64 lines] ...
    """

    retrans_error_parts_system_prompt = f"""
    ... [Prompt Content Hidden: 2928 chars / 46 lines] ...
    """

    extract_terminology_system_prompt = f"""
    ... [Prompt Content Hidden: 1986 chars / 45 lines] ...
    """

    get_summary_system_prompt = f"""
    ... [Prompt Content Hidden: 881 chars / 14 lines] ...
    """

    refine_summary_system_prompt = f"""
    ... [Prompt Content Hidden: 1018 chars / 15 lines] ...
    """

    section_system_prompt_with_sum = f"""
    ... [Prompt Content Hidden: 3293 chars / 22 lines] ...
    """

    caption_system_prompt_with_sum  = f"""
    ... [Prompt Content Hidden: 3024 chars / 17 lines] ...
    """

    env_system_prompt_with_sum = f"""
    ... [Prompt Content Hidden: 3063 chars / 18 lines] ...
    """

    section_system_prompt_with_terms_sum = f"""
    ... [Prompt Content Hidden: 3853 chars / 29 lines] ...
    """

    section_system_prompt_with_prev = f"""
    ... [Prompt Content Hidden: 3079 chars / 20 lines] ...
    """

    section_system_prompt_with_terms_prev = f"""
    ... [Prompt Content Hidden: 2974 chars / 18 lines] ...
    """

```

---

### 📄 app\services\latex\reconstruct.py

```python
"""
LaTeX Reconstructor

Adapted from prototype system with:
- Python logging added
- Optional progress callback mechanism
- All functionality preserved
"""

from typing import List, Dict, Any, Optional, Callable
import os
import re
import logging
from .utils import *

logger = logging.getLogger(__name__)


class LatexConstructor:
    def __init__(self, 
                 sections: List[Dict[str, Any]], 
                 captions: List[Dict[str, Any]], 
                 envs: List[Dict[str, Any]],
                 inputs: List[Dict[str, Any]],
                 newcommands: List[Dict[str, Any]],
                 output_latex_dir: str
                 ):
        self.sections = sections
        self.captions = captions
        self.envs = envs
        self.inputs = inputs
        self.newcommands = newcommands
        self.output_latex_dir = output_latex_dir

    def construct(self, on_progress: Optional[Callable[[str, int, str], None]] = None):
        """
        Construct the translated LaTeX project from the sections, envs, captions and inputs
        
        Args:
            on_progress: Optional callback function(stage, percentage, message)
        """
        logger.info("Starting LaTeX reconstruction")
        
        if on_progress:
            on_progress("reconstructing", 10, "Merging sections...")
        
        tex = self._merge_sections()
        
        if on_progress:
            on_progress("reconstructing", 30, "Reverting environments...")
        
        tex = self._revert_envs(tex)
        
        if on_progress:
            on_progress("reconstructing", 50, "Reverting captions...")
        
        tex = self._revert_captions(tex)
        
        if on_progress:
            on_progress("reconstructing", 70, "Reverting newcommands...")
        
        tex = self._revert_newcommands(tex)

        # Process japanese specific packages if needed
        # tex = self._comment_out_latex_packages_for_ja(tex)
        # tex = self._add_lualatex_option_to_documentclass_for_ja(tex)

        if on_progress:
            on_progress("reconstructing", 90, "Writing output files...")
        
        self._revert_inputs(tex)
        
        if on_progress:
            on_progress("reconstructing", 100, "Reconstruction complete")
        
        logger.info("LaTeX reconstruction complete")
    
    def _merge_sections(self) -> str:
        """Merge all the sections to a tex"""
        logger.debug(f"Merging {len(self.sections)} sections")
        tex = ""
        for section in self.sections:
            # Use trans_content if available, otherwise use original content
            content = section["trans_content"] if section["trans_content"] else section["content"]
            tex += content + "\n"
        return tex

    def _revert_envs(self, tex: str) -> str:
        """Revert all the envs to tex"""
        logger.debug(f"Reverting {len(self.envs)} environments")
        for env in self.envs:
            placeholder = env["placeholder"]
            # Use trans_content if available, otherwise use original content
            content = env["trans_content"] if env["trans_content"] else env["content"]
            tex = tex.replace(placeholder, content)
        return tex
             
    def _revert_captions(self, tex: str) -> str:
        """Revert all the captions to tex"""
        logger.debug(f"Reverting {len(self.captions)} captions")
        for caption in self.captions:
            placeholder = caption["placeholder"]
            # Use trans_content if available, otherwise use original content
            content = caption["trans_content"] if caption["trans_content"] else caption["content"]
            tex = tex.replace(placeholder, content)
        return tex                              
    
    def _revert_newcommands(self, tex: str) -> str:
        """Revert all the newcommands to tex"""
        logger.debug(f"Reverting {len(self.newcommands)} newcommands")
        for newcommand in self.newcommands:
            placeholder = newcommand["placeholder"]
            tex = tex.replace(placeholder, newcommand["content"])
        return tex
                                          
    def _revert_inputs(self, tex: str):
        """Revert input placeholders and write separate files"""
        begin_map = {sec["begin"]: sec for sec in self.inputs}
        end_map = {sec["end"]: sec for sec in self.inputs}
        pattern = re.compile(r"<PLACEHOLDER_[^>]+?_begin>|<PLACEHOLDER_[^>]+?_end>")

        stack = []
        pos = 0

        while True:
            match = pattern.search(tex, pos)
            if not match:
                break

            tag = match.group()

            if tag in begin_map:
                stack.append((tag, match.start()))
                pos = match.end()
            elif tag in end_map:
                if not stack:
                    logger.error(f"Unmatched end tag: {tag}")
                    raise ValueError(f"Unmatched end tag: {tag}")
                begin_tag, begin_pos = stack.pop()
                if end_map[tag] != begin_map[begin_tag]:
                    logger.error(f"Mismatched tags: {begin_tag} vs {tag}")
                    raise ValueError(f"Mismatched tags: {begin_tag} vs {tag}")

                input_info = begin_map[begin_tag]
                end_pos = match.end()

                inner_start = begin_pos + len(begin_tag)
                inner_end = match.start()
                inner_content = tex[inner_start:inner_end].strip()

                relative_path = input_info["path"]
                if not relative_path.endswith(".tex"):
                    relative_path += ".tex"
                output_path = os.path.join(self.output_latex_dir, relative_path)
                
                logger.debug(f"Writing input file: {output_path}")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(inner_content + "\n")

                tex = tex[:begin_pos] + input_info["command"] + tex[end_pos:]
                pos = begin_pos + len(input_info["command"])

            else:
                pos = match.end()

        if stack:
            unclosed_tags = [tag for tag, _ in stack]
            logger.warning(f"Unclosed begin placeholder(s) found and skipped: {unclosed_tags}")
            print(f"⚠️ Warning: Unclosed begin placeholder(s) found and skipped: {unclosed_tags}")
        
        residual_matches = re.findall(r"<PLACEHOLDER_[^>]*>", tex)
        if residual_matches:
            logger.warning(f"Residual placeholders found and removed: {residual_matches}")
            print(f"⚠️ Warning: Residual placeholders found and removed: {residual_matches}")
            tex = re.sub(r"<PLACEHOLDER_[^>]*>", "", tex)

        # Add language-specific packages
        tex = add_ctex_package(tex)  # Chinese support
        # tex = add_ja_package(tex)  # Japanese support

        main_file_path = find_main_tex_file(self.output_latex_dir)
        if os.path.exists(main_file_path):
            logger.info(f"Writing main tex file: {main_file_path}")
            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(tex)
        else:
            logger.warning(f"No main.tex file found in {self.output_latex_dir}, creating a new one")
            print(f"⚠️ Warning: No main.tex file found in {self.output_latex_dir}, creating a new one.")
            main_file_path = os.path.join(self.output_latex_dir, "main.tex")
            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(tex)

    def _comment_out_latex_packages_for_ja(self, tex):
        """Comment out packages that conflict with Japanese typesetting"""
        packages_to_comment = [
            r'\usepackage[utf8]{inputenc}',
            r'\usepackage[T1]{fontenc}',
            r'\usepackage{times}',
            r'\usepackage{mathptmx}',
            r'\pdfoutput=1'
        ]
        
        lines = tex.splitlines()
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            for package in packages_to_comment:
                if stripped_line.startswith(package) and not stripped_line.startswith('%'):
                    lines[i] = line.replace(package, f'% {package}')
                    break
        
        return '\n'.join(lines)        

    def _add_lualatex_option_to_documentclass_for_ja(self, tex):
        """Add lualatex option to documentclass for Japanese support"""
        import re
        
        pattern = re.compile(r'\\documentclass(?:\[([^\]]*)\])?(\{.*?\})')
        
        def replacer(match):
            options = match.group(1)
            class_name = match.group(2)
            
            if options:
                if 'lualatex' not in options:
                    new_options = options + ', lualatex'
                else:
                    new_options = options
                return f'\\documentclass[{new_options}]{class_name}'
            else:
                return f'\\documentclass[lualatex]{class_name}'
        
        modified_source = pattern.sub(replacer, tex)
        return modified_source
```

---

### 📄 app\services\latex\utils.py

```python
"""
LaTeX Utilities for Web Backend

Complete adaptation from prototype system with:
- All Streamlit dependencies removed
- Python logging added
- sys.stderr redirection removed
- Full AST processing and LaTeX manipulation functionality preserved
"""

from pylatexenc.latexwalker import (
    LatexWalker, LatexMacroNode, LatexEnvironmentNode, LatexGroupNode, LatexCharsNode,
    LatexSpecialsNode, LatexMathNode
)
from pylatexenc.latex2text import LatexNodes2Text
import os
import re
import json
import zipfile
import tarfile
from tqdm import tqdm
import regex
import subprocess
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import time
import logging

logger = logging.getLogger(__name__)

# Regex pattern constants
options = r"\[[^\[\]]*?\]"
spaces = r"[ \t]*"
get_pattern_brace = lambda index: rf"\{{((?:[^{{}}]++|(?{index}))*+)\}}"


def get_pattern_command_full(name, n=None):
    """Generate regex pattern for LaTeX commands"""
    pattern = rf'\\({name})'
    if n is None:
        pattern += rf'{spaces}({options})?'
        n = 1
        begin_brace = 3
    else:
        begin_brace = 2
    for i in range(n):
        tmp = get_pattern_brace(i*2+begin_brace)
        pattern += rf'{spaces}({tmp})'
    if n == 0:
        pattern += r'(?=[^a-zA-Z])'
    return pattern


def extract_compressed_files(folder_path):
    """
    Traverse the given folder and extract all compressed files (zip, tar, tar.gz, etc.).
    After extraction, delete the source compressed files.
    
    Args:
        folder_path (str): Path to the folder containing compressed files.
    """
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    extract_path = os.path.join(root, file.replace('.zip', ''))
                    zip_ref.extractall(extract_path)
                    logger.info(f"Extracted {file} to {extract_path}")
                os.remove(file_path)
            elif tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, 'r:*') as tar_ref:
                    extract_path = os.path.join(root, file.replace('.tar', '').replace('.gz', ''))
                    tar_ref.extractall(extract_path)
                    logger.info(f"Extracted {file} to {extract_path}")
                os.remove(file_path)


def get_profect_dirs(folder_path):
    """
    Get a list of all subdirectories in the given folder.
    
    Args:
        folder_path (str): Path to the folder.
    
    Returns:
        list: A list of subdirectory paths.
    """
    projects = []
    for d in os.listdir(folder_path):
        if os.path.isdir(os.path.join(folder_path, d)):
            project_path = os.path.join(folder_path, d)
            projects.append(project_path)
    return projects


def has_appendix(latex_code):
    """Check if LaTeX code contains appendix"""
    appendix_pattern = re.compile(r"\\appendix\b")
    return bool(appendix_pattern.search(latex_code))


def remove_appendix_content(latex_code):
    """Remove appendix content from LaTeX code"""
    appendix_pattern = re.compile(r"\\appendix\b.*?(?=\\end\{document\})", re.DOTALL)
    modified_code = appendix_pattern.sub("", latex_code)
    return modified_code


def extract_latex_nodes(tex):
    """Extract LaTeX AST nodes using pylatexenc"""
    walker = LatexWalker(tex)
    nodes, npos, nlen = walker.get_latex_nodes()
    return nodes


def extract_text_from_tex(tex):
    """Convert LaTeX to plain text"""
    text = LatexNodes2Text().latex_to_text(tex)
    return text


def extract_structure(nodes, depth=0):
    """
    Extract structural information from LaTeX nodes
    
    Args:
        nodes: LaTeX nodes from pylatexenc
        depth: Current depth in the tree
    
    Returns:
        Dictionary containing commands, environments, specials, and math
    """
    structure = {
        'command': [],
        'environment': [],
        'special': [],
        'math': []
    }

    for node in nodes:
        if isinstance(node, LatexMacroNode):
            structure['command'].append({'name': node.macroname, 'depth': depth})
            if node.nodeargd:
                sub_structure = extract_structure(node.nodeargd.argnlist, depth + 1)
                for key in sub_structure:
                    structure[key].extend(sub_structure[key])
        elif isinstance(node, LatexEnvironmentNode):
            structure['environment'].append({'name': node.envname, 'depth': depth})
            sub_structure = extract_structure(node.nodelist, depth + 1)
            for key in sub_structure:
                structure[key].extend(sub_structure[key])
        elif isinstance(node, LatexGroupNode):
            sub_structure = extract_structure(node.nodelist, depth + 1)
            for key in sub_structure:
                structure[key].extend(sub_structure[key])
        elif isinstance(node, LatexSpecialsNode):
            structure['special'].append({'chars': node.specials_chars, 'depth': depth})
        elif isinstance(node, LatexMathNode):
            structure['math'].append({'type': node.displaytype, 'depth': depth})
            sub_structure = extract_structure(node.nodelist, depth + 1)
            for key in sub_structure:
                structure[key].extend(sub_structure[key])

    return structure


def extract_title(latex_code):
    """Extract title from LaTeX code"""
    title_start = latex_code.find(r"\title{")
    if title_start == -1:
        title_start = latex_code.find(r"\title[")
    if title_start == -1:
        return "No title"
    
    brace_start = latex_code.find("{", title_start)
    if brace_start == -1:
        return "No title"
    
    stack = []
    for i in range(brace_start, len(latex_code)):
        if latex_code[i] == "{":
            stack.append(i)
        elif latex_code[i] == "}":
            stack.pop()
            if not stack:
                return latex_code[brace_start + 1:i].strip()

    return "No title"


def extract_abstract(latex_code):
    """Extract abstract from LaTeX code"""
    abstract_pattern = regex.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", regex.DOTALL)
    match = abstract_pattern.search(latex_code)
    
    if match:
        abstract = match.group(1).strip()
        return abstract
    
    abstract_start = latex_code.find(r"\abstract{")
    if abstract_start == -1:
        return "No abstract"

    brace_start = latex_code.find("{", abstract_start)
    if brace_start == -1:
        return "No abstract"

    stack = []
    for i in range(brace_start, len(latex_code)):
        if latex_code[i] == "{":
            stack.append(i)
        elif latex_code[i] == "}":
            stack.pop()
            if not stack:
                return latex_code[brace_start + 1:i].strip()

    return "No abstract"


def extract_keywords(latex_code):
    """Extract keywords from LaTeX code"""
    keywords_pattern = regex.compile(r"\\keywords\{(?:\{([^{}]*)\}|([^{}]*))\}", regex.DOTALL)
    match = keywords_pattern.search(latex_code)
    keywords = match.group(1) or match.group(2) if match else None
    return keywords.strip() if keywords else None


def extract_sections(latex_code):
    """Split LaTeX code into before and after first section"""
    section_pattern = regex.compile(r"\\(section|chapter)\b")
    match = section_pattern.search(latex_code)
    if not match:
        return latex_code, ""
    
    section_index = match.start()
    before_section = latex_code[:section_index]
    after_section = latex_code[section_index:]
    return before_section, after_section


def extract_captions(latex_code):
    """Extract caption from LaTeX code"""
    caption_start = latex_code.find(r"\caption{")
    if caption_start == -1:
        caption_start = latex_code.find(r"\caption[")
    if caption_start == -1:
        return "No caption"
    
    brace_start = latex_code.find("{", caption_start)
    if brace_start == -1:
        return "No caption"
    
    stack = []
    for i in range(brace_start, len(latex_code)):
        if latex_code[i] == "{":
            stack.append(i)
        elif latex_code[i] == "}":
            stack.pop()
            if not stack:
                return latex_code[brace_start + 1:i].strip()

    return "No caption"


def replace_figures(latex_code):
    """Replace figure environments with placeholders"""
    figure_pattern = regex.compile(
        r"\\begin\{(figure\*?|wrapfigure|SCfigure|tikzpicture)\}.*?\\end\{\1\}",
        regex.DOTALL
    )
    
    def replace_match(match):
        figure_code = match.group(0)
        caption = extract_captions(figure_code)
        return f"<FIGURE: {caption}>"
    
    latex_code = figure_pattern.sub(replace_match, latex_code)
    return latex_code


def replace_tables(latex_code):
    """Replace table environments with placeholders"""
    table_pattern = regex.compile(
        r"\\begin\{(table\*?|tabular|tabularx|longtable)\}.*?\\end\{\1\}",
        regex.DOTALL
    )
    
    def replace_match(match):
        table_code = match.group(0)
        caption = extract_captions(table_code)
        return f"<TABLE: {caption}>"
    
    latex_code = table_pattern.sub(replace_match, latex_code)
    return latex_code


def replace_newcommand(newcommand, latex_code):
    """Replace custom LaTeX commands with their definitions"""
    command_name, n_arguments, content = newcommand
    pattern = regex.compile(get_pattern_command_full(command_name, n_arguments), regex.DOTALL)

    def replace_function(match):
        this_content = content
        name = match.group(1)
        assert re.match(command_name, name)
        for i in range(n_arguments):
            text = match.group(3 + i * 2)
            this_content = this_content.replace(f'#{i+1}', f' {text} ')
        return this_content

    return pattern.sub(replace_function, latex_code)


def process_newcommands(latex_code):
    """Process and expand all newcommand definitions"""
    
    def get_nonNone(*args):
        result = [arg for arg in args if arg is not None]
        assert len(result) == 1
        return result[0]

    pattern_newcommand = rf'\\(?:newcommand\*?|def|renewcommand){spaces}(?:\{{\\([a-zA-Z]+)\}}|\\([a-zA-Z]+)){spaces}(?:\[(\d)\])?{spaces}({get_pattern_brace(4)})'
    pattern = regex.compile(pattern_newcommand, regex.DOTALL)
    count = 0
    full_newcommands = []
    match = pattern.search(latex_code)
    
    while match:
        name1 = match.group(1)
        name2 = match.group(2)
        name = get_nonNone(name1, name2)
        n_arguments = match.group(3)
        if n_arguments is None:
            n_arguments = 0
        else:
            n_arguments = int(n_arguments)
        content = match.group(5)
        latex_code = latex_code.replace(match.group(), f'REPLACE_{count}_NEWCOMMAND')
        full_newcommands.append(match.group(0))
        latex_code = replace_newcommand((name, n_arguments, content), latex_code)
        count += 1
        match = pattern.search(latex_code)
    
    for i in range(count):
        latex_code = latex_code.replace(f'REPLACE_{i}_NEWCOMMAND', full_newcommands[i])
    return latex_code


def replace_href(latex_code):
    """Remove href commands, keeping only the text"""
    href_pattern = regex.compile(r"\\href\{[^{}]*\}\{(.*?)\}")
    latex_code = href_pattern.sub(r"\1", latex_code)
    return latex_code


def replace_includegraphics(latex_code):
    """Remove includegraphics commands"""
    includegraphics_pattern = regex.compile(r"\\includegraphics(?:\[[^\]]*\])?\{[^\}]*\}", regex.DOTALL)
    latex_code = includegraphics_pattern.sub("", latex_code)
    return latex_code


def process_latex_to_eva(latex_code):
    """Process LaTeX code for evaluation/extraction"""
    latex_code = replace_href(latex_code)
    latex_code = replace_includegraphics(latex_code)
    latex_code = process_newcommands(latex_code)
    before_section, after_section = extract_sections(latex_code)
    title = extract_title(before_section) if extract_title(before_section) else 'No title'
    abstract = extract_abstract(before_section) if extract_abstract(before_section) else 'No abstract'
    keywords = extract_keywords(before_section) if extract_keywords(before_section) else ''
    after_section = replace_figures(after_section)
    after_section = replace_tables(after_section)
    tex_to_eva = f"{title}\n\n{abstract}\n\n{keywords}\n\n{after_section}"
    return tex_to_eva


def delete_ph(text) -> str:
    """Delete placeholders from text"""
    pattern = r'§(\.§){0,2}'
    text = re.sub(pattern, '', text)
    placeholder_pattern = r"<.*?PLACEHOLDER.*?>"
    text = re.sub(placeholder_pattern, "", text).strip()
    text = text.replace('\n', ' ')
    text = re.sub(r' +', ' ', text)
    return text.strip()


def extract_pure_text(dir):
    """Extract pure text from LaTeX project"""
    main_file_path = find_main_tex_file(dir)
    if main_file_path is None:
        raise FileNotFoundError(f"Main TeX file not found in {dir}")
    full_latex_code = merge_tex_from_inputs(main_file_path)
    main_latex_code = process_latex_to_eva(full_latex_code)
    pure_text = extract_text_from_tex(main_latex_code)
    return pure_text


def get_texts_from_data(folder_path, output_folder):
    """Extract text from all projects in a folder"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    extract_compressed_files(folder_path)
    projects = get_profect_dirs(folder_path)
    
    for project in tqdm(projects, desc="Processing projects", unit="project"):
        try:
            text = extract_pure_text(project)
            project_name = os.path.basename(project)
            output_file = os.path.join(output_folder, f"{project_name}.txt")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            logger.error(f"Error processing project {project}: {e}")
            continue


def extract_pure_tags(dir):
    """Extract tag structure from LaTeX project"""
    main_file_path = find_main_tex_file(dir)
    if main_file_path is None:
        raise FileNotFoundError(f"Main TeX file not found in {dir}")
    main_latex_code = merge_tex_from_inputs(main_file_path)
    nodes = extract_latex_nodes(main_latex_code)
    tag_structure = extract_structure(nodes)
    return tag_structure


def loop_files(dir):
    """Recursively list all files in a directory"""
    all_files = []
    for root, dirs, files in os.walk(dir):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


def read_tex_file(path):
    """Read LaTeX file"""
    with open(path, 'r', encoding='utf-8') as f:
        latex_code = f.read()
    return latex_code


def read_json_file(path):
    """Read JSON file"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def find_tex_files(dir):
    """Find all .tex files in a directory"""
    all_files = loop_files(dir)
    tex_files = [f for f in all_files if f.endswith('.tex')]
    return tex_files


def remove_comments(tex: str) -> str:
    """
    Remove both % line comments and \\begin{comment} ... \\end{comment} blocks from LaTeX code.
    """
    # Remove \begin{comment}...\end{comment} environments
    tex = re.sub(r'\\begin\s*\{comment\}.*?\\end\s*\{comment\}', '', tex, flags=re.DOTALL)

    lines = tex.splitlines()
    cleaned = []
    for line in lines:
        stripped_line = line.lstrip()
        # Skip full-line comments (ignoring leading whitespace)
        if re.match(r'^(?<!\\)%', stripped_line):
            continue
        # Remove inline comments (ignore escaped %)
        line = re.sub(r'(?<!\\)%.*', '', line)
        cleaned.append(line.rstrip())

    return '\n'.join(cleaned)


def compress_newlines(tex):
    """
    Replace consecutive newlines (including spaces) exceeding four with exactly two newlines.
    """
    return re.sub(r'(\s*\n\s*){3,}', '\n\n', tex)


def get_env_pattern(command_name):
    """Get the regex pattern for matching environments"""
    get_command_env = lambda name: rf"\\begin{spaces}\{{(?!document\b|center\b|proof\b|multicols\b)({name})\}}{spaces}({options})?(.*?)\\end{spaces}\{{\1\}}"
    command_env = get_command_env(command_name)
    env_pattern = regex.compile(command_env, regex.DOTALL)
    return env_pattern


def get_abstract_pattern():
    """Get the regex pattern for matching \\begin{abstract} and \\end{abstract} commands"""
    command_name = r'abstract'
    get_command_env = lambda name: rf"\\begin{spaces}\{{({name})\}}{spaces}({options})?(.*?)\\end{spaces}\{{\1\}}"
    command_abstract = get_command_env(command_name)
    abstract_pattern = regex.compile(command_abstract, regex.DOTALL)
    return abstract_pattern


def get_keywords_pattern():
    """Get the regex pattern for matching \\keywords commands"""
    command_name = r'keywords'
    command = get_pattern_command_full(command_name)
    keywords_pattern = regex.compile(command, regex.DOTALL)
    return keywords_pattern


def get_section_pattern():
    """Get the regex pattern for matching section commands"""
    command_name = r'section|subsection|subsubsection'
    command = get_pattern_command_full(command_name)
    section_pattern = regex.compile(command, regex.DOTALL)
    return section_pattern


def get_begin_document_pattern():
    """Get the regex pattern for matching \\begin{document} command"""
    pattern = regex.compile(r'\\begin\s*\{\s*document\s*\}', regex.DOTALL)
    return pattern


def get_newcommand_pattern():
    """Get the regex pattern for matching \\newcommand commands"""
    newcommand = rf'\\(?:newcommand\*?|def|renewcommand|newenvironment|renewenvironment){spaces}(?:\{{\\([a-zA-Z]+)\}}|\\([a-zA-Z]+)){spaces}(?:\[(\d)\])?{spaces}({get_pattern_brace(4)})'
    newcommand_pattern = regex.compile(newcommand, regex.DOTALL)
    return newcommand_pattern


def get_command_pattern(name):
    """Get the regex pattern for matching LaTeX commands"""
    command = get_pattern_command_full(name)
    command_pattern = regex.compile(command, regex.DOTALL)
    return command_pattern


def get_captionof_pattern():
    """Match \\captionof{env}{text} structure using regex with support for nested braces"""
    pattern = regex.compile(r"""
        \\captionof          # match \captionof
        \s*                  # optional whitespace
        (?P<braces>          # named group 'braces' to handle nested {}
            \{               # opening {
                (?:          # non-capturing group
                    [^{}]+   # non-brace characters
                    |        # OR
                    (?&braces)  # recursive match for nested braces
                )*
            \}               # closing }
        )
        \s*                  # optional whitespace
        (?P=braces)          # repeat the same structure for the second argument
    """, regex.VERBOSE | regex.DOTALL)
    return pattern


def add_ctex_package(latex_code):
    """Add ctex package for Chinese support"""
    if "\\usepackage[UTF8]{ctex}" not in latex_code:
        ctex_package = "\\usepackage[UTF8]{ctex}"
        documentclass = r'documentclass'
        documentclass_pattern = get_command_pattern(documentclass)
        match = documentclass_pattern.search(latex_code)
        if match:
            position = match.end()
            latex_code = latex_code[:position] + "\n" + ctex_package + "\n" + latex_code[position:]
    return latex_code


def add_ja_package(latex_code):
    """Add Japanese package support"""
    if "\\usepackage{luatex-ja}" not in latex_code:
        ctex_package = "\\usepackage{luatexja}"
        documentclass = r'documentclass'
        documentclass_pattern = get_command_pattern(documentclass)
        match = documentclass_pattern.search(latex_code)
        if match:
            position = match.end()
            latex_code = latex_code[:position] + "\n" + ctex_package + "\n" + latex_code[position:]
    return latex_code


def find_main_tex_file(dir):
    """
    Find the main LaTeX file in the given directory.
    
    Looks for 00README.json first, then searches for files with \\documentclass.
    """
    readme_path = os.path.join(dir, '00README.json')
    if os.path.exists(readme_path):
        config = read_json_file(readme_path)
        for source in config.get("sources", []):
            if source.get("usage") == "toplevel":
                main_file_name = source.get("filename")
                main_file_path = os.path.join(dir, main_file_name)
                return main_file_path if os.path.exists(main_file_path) else None

    tex_files = find_tex_files(dir)
    documentclass_pattern = re.compile(r"\\document(class|style)(\[.*?\])?\{.*?\}", re.DOTALL)
    
    for tex_file in tex_files:
        with open(tex_file, 'r', encoding='utf-8') as f:
            latex_code = f.read()
        latex_code = remove_comments(latex_code)
        
        if not documentclass_pattern.search(latex_code):
            continue

        return tex_file
    
    return None


def merge_tex_from_inputs(main_file_path):
    """
    Merge all \\input and \\include files into a single LaTeX document.
    """
    if main_file_path is None:
        return None
    dirname = os.path.dirname(main_file_path)
    maincontent = read_tex_file(main_file_path)
    maincontent = remove_comments(maincontent)
    pattern_input = re.compile(r'\\(input|include){(.*?)}')
    
    while True:
        result = pattern_input.search(maincontent)
        if result is None:
            break
        begin, end = result.span()
        match = result.group(2)
        inputfilepath = os.path.join(dirname, match)
        
        if match.endswith('.tex'):
            if os.path.exists(f'{inputfilepath}'):
                inputfilepath = f'{inputfilepath}'
            else:
                raise FileNotFoundError(f"File not found: {inputfilepath}")
        else:
            if os.path.exists(f'{inputfilepath}.tex'):
                inputfilepath = f'{inputfilepath}.tex'
            else:
                raise FileNotFoundError(f"File not found: {inputfilepath}.tex")
        
        input_tex = read_tex_file(inputfilepath)
        input_tex = remove_comments(input_tex)
        maincontent = maincontent[:begin] + input_tex + maincontent[end:]

    return maincontent


def save_to_tex(data, output_file):
    """Save data to .tex file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(data)


def save_to_json(data, output_file):
    """Save data to JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def compile_with_latexmk(tex_file: str, out_dir: str = "out", engine: str = "pdflatex"):
    """
    Compile LaTeX file using latexmk (deprecated - use compiler.py instead)
    """
    os.makedirs(out_dir, exist_ok=True)
    
    cmd = [
        "latexmk",
        f"-{engine}",
        "-interaction=nonstopmode",
        f"-outdir={out_dir}",
        f"-synctex=1",
        f"-f",
        tex_file
    ]
    
    try:
        subprocess.run(cmd, check=True)
        logger.info("✅ Compilation successful")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Compilation failed: {e}")


def collect_latex_errors_with_logpath(folder: str):
    """
    Collect LaTeX compilation errors from log files in project folders.
    """
    error_keyword = re.compile(r"latex error", re.IGNORECASE)
    summary = {}
    error_project_count = 0

    for project_name in os.listdir(folder):
        project_path = os.path.join(folder, project_name)
        if not os.path.isdir(project_path):
            continue

        preferred_builds = ["build_pdflatex", "build"]
        build_path = None
        for build_dir in preferred_builds:
            candidate = os.path.join(project_path, build_dir)
            if os.path.isdir(candidate):
                build_path = candidate
                break

        if build_path is None:
            continue

        log_files = [f for f in os.listdir(build_path) if f.endswith(".log")]
        if not log_files:
            continue

        log_path = os.path.join(build_path, log_files[0])
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                error_count = len(error_keyword.findall(content))
        except Exception as e:
            logger.error(f"Error reading {log_path}: {e}")
            continue

        if error_count > 0:
            summary[project_name] = {
                "total_errors": error_count,
                "log_path": log_path
            }
            error_project_count += 1

    output_path = os.path.join(folder, "latex_error_summary.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Summary saved to: {output_path}")
    logger.info(f"🔍 Total projects with LaTeX errors: {error_project_count}")


# ============================================================================
# arXiv Download Utilities (Web-adapted, Streamlit removed)
# ============================================================================

def get_tex_url(arxiv_id: str, headers: dict) -> str:
    """
    Get TeX source download link from arXiv
    """
    abs_url = f"https://arxiv.org/abs/{arxiv_id}"
    try:
        resp = requests.get(abs_url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    
    soup = BeautifulSoup(resp.text, "html.parser")
    link = soup.find("a", class_="abs-button download-eprint")
    if link and link.get("href"):
        return f"https://arxiv.org{link['href']}"
    return ""


def is_already_downloaded(arxiv_id: str, save_dir: str) -> bool:
    """Check if tar.gz file or extracted directory already exists"""
    tar_path = os.path.join(save_dir, f"{arxiv_id}.tar.gz")
    extracted_dir = os.path.join(save_dir, arxiv_id)
    return os.path.exists(tar_path) or os.path.isdir(extracted_dir)


def download_tex(arxiv_id: str, tex_url: str, save_dir: str, headers: dict):
    """
    Download TeX source .tar.gz file (Streamlit removed)
    """
    file_path = os.path.join(save_dir, f"{arxiv_id}.tar.gz")

    try:
        with requests.get(tex_url, headers=headers, stream=True, timeout=20) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("Content-Length", 0))

            with open(file_path, "wb") as f, tqdm(
                desc=f"Download: {arxiv_id}",
                total=total_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
        
        logger.info(f"[SUCCESS] {arxiv_id} successfully downloaded to {file_path}.")
        return os.path.join(save_dir, f"{arxiv_id}")

    except requests.RequestException as e:
        logger.error(f"[FAIL] {arxiv_id} download failed: {e}")


def batch_download_arxiv_tex(arxiv_ids: List[str], save_dir: str = "./tex_sources"):
    """
    Batch download multiple arXiv paper TeX sources (Streamlit removed)
    """
    source_dirs = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for arxiv_id in arxiv_ids:
        if is_already_downloaded(arxiv_id, save_dir):
            source_dirs.append(os.path.join(save_dir, arxiv_id))
            logger.info(f"[SKIP] Already downloaded: {arxiv_id}")
            continue

        tex_url = get_tex_url(arxiv_id, headers)
        if tex_url:
            dir = download_tex(arxiv_id, tex_url, save_dir, headers)
            source_dirs.append(dir)
        else:
            logger.warning(f"[SKIP] No TeX source found for {arxiv_id}. Please check the arXiv ID or the availability of the source.")

        # Download PDF file
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_path = os.path.join(save_dir, arxiv_id, f"{arxiv_id}.pdf")
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        try:
            response = requests.get(pdf_url, headers=headers)
            response.raise_for_status()
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"[SUCCESS] Downloaded PDF for {arxiv_id}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to download PDF for {arxiv_id}: {str(e)}")

    return source_dirs


def get_arxiv_category(arxiv_ids: List[str]) -> dict:
    """Get arXiv categories for papers"""
    results = {}
    headers = {"User-Agent": "Mozilla/5.0"}
    for arxiv_id in arxiv_ids:
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        categories = []

        try:
            resp = requests.get(abs_url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            subjects_div = soup.find("div", class_="subjects")
            if subjects_div:
                matches = re.findall(r"\(([a-z]+\.[A-Z]+)\)", subjects_div.text)
                categories.extend(matches)
            else:
                td_subjects = soup.find("td", class_="tablecell subjects")
                if td_subjects:
                    matches = re.findall(r'\(([a-z]+\.[A-Z]+)\)', td_subjects.text)
                    categories.extend(matches)

            if not categories:
                logger.warning(f"No categories found for {arxiv_id}")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch {arxiv_id}: {e}")
            categories = []

        results[arxiv_id] = (categories)
        time.sleep(1)

    return results


def is_valid_arxiv_id(id_str):
    """Validate arXiv ID format"""
    # Modern format: YYYY.NNNNN or YYYY.NNNNNNN
    if re.match(r'^\d{4}\.\d{5,7}$', id_str):
        return True
    # Old format: subject/YYMMNNN (e.g., hep-th/9901001)
    if re.match(r'^[\w\-]+/\d{7}$', id_str):
        return True
    return False


def extract_arxiv_ids(arxiv_input):
    """
    Extract valid arXiv IDs from string or list of strings/URLs
    
    Args:
        arxiv_input: Single string or list of strings containing arXiv IDs/URLs
        
    Returns:
        List of validated arXiv IDs
        
    Examples:
        >>> extract_arxiv_ids("2508.18791")
        ['2508.18791']
        >>> extract_arxiv_ids("https://arxiv.org/abs/2508.18791")
        ['2508.18791']
        >>> extract_arxiv_ids(["2508.18791", "https://arxiv.org/pdf/1234.56789.pdf"])
        ['2508.18791', '1234.56789']
    """
    # 统一转换为列表处理
    if isinstance(arxiv_input, str):
        arxiv_input = [arxiv_input]
    
    ids = []
    for item in arxiv_input:
        if is_valid_arxiv_id(item):
            ids.append(item)
            continue

        url_pattern = r'(?:arxiv\.org/)(?:abs|pdf|e-print)/([\w\-]+/\d{7}|\d{4}\.\d{5,7})(?:\.pdf)?'
        match = re.search(url_pattern, item)
        if match:
            ids.append(match.group(1))
    return ids
```

---

### 📄 app\services\task_manager.py

```python
"""
Task Manager Service

In-memory task status tracking with thread-safe operations.
Manages task state, progress updates, and status queries.
"""

import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from backend.app.core.config import TaskStatus, CompilationStage


class TaskManager:
    """
    Thread-safe in-memory task manager for tracking translation tasks
    """
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_task(self, source_type: str = "upload") -> str:
        """
        Create a new task and return its ID
        
        Args:
            source_type: "upload" or "arxiv"
        
        Returns:
            Task ID (UUID string)
        """
        task_id = str(uuid.uuid4())
        
        with self._lock:
            self._tasks[task_id] = {
                "task_id": task_id,
                "status": TaskStatus.PENDING.value,
                "progress": 0,
                "stage": CompilationStage.IDLE.value,
                "message": "Task created",
                "error": None,
                "warnings": None,
                "source_available": False,
                "created_at": datetime.utcnow().isoformat(),
                "completed_at": None,
                "source_type": source_type,
                "source_path": None,
                "output_path": None
            }
        
        return task_id
    
    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        warnings: Optional[str] = None,
        source_available: Optional[bool] = None,
        source_path: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> bool:
        """
        Update task fields
        
        Args:
            task_id: Task ID
            status: New status (optional)
            progress: Progress percentage 0-100 (optional)
            stage: Current stage (optional)
            message: Status message (optional)
            error: Error message (optional)
            warnings: Warning message (optional)
            source_available: Whether source is available (optional)
            source_path: Path to source files (optional)
            output_path: Path to output files (optional)
        
        Returns:
            True if task exists and was updated, False otherwise
        """
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            
            if status is not None:
                task["status"] = status
                # Auto-complete timestamp
                if status in [TaskStatus.COMPLETED.value, 
                             TaskStatus.COMPLETED_WITH_WARNINGS.value, 
                             TaskStatus.FAILED.value,
                             TaskStatus.FAILED_COMPILATION.value]:
                    task["completed_at"] = datetime.utcnow().isoformat()
            
            if progress is not None:
                task["progress"] = max(0, min(100, progress))
            
            if stage is not None:
                task["stage"] = stage
            
            if message is not None:
                task["message"] = message
            
            if error is not None:
                task["error"] = error
            
            if warnings is not None:
                task["warnings"] = warnings
            
            if source_available is not None:
                task["source_available"] = source_available
            
            if source_path is not None:
                task["source_path"] = source_path
            
            if output_path is not None:
                task["output_path"] = output_path
            
            return True
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID
        
        Args:
            task_id: Task ID
        
        Returns:
            Task dictionary or None if not found
        """
        with self._lock:
            return self._tasks.get(task_id, None).copy() if task_id in self._tasks else None
    
    def task_exists(self, task_id: str) -> bool:
        """Check if task exists"""
        with self._lock:
            return task_id in self._tasks
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task
        
        Args:
            task_id: Task ID
        
        Returns:
            True if task was deleted, False if not found
        """
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all tasks (for debugging)"""
        with self._lock:
            return {k: v.copy() for k, v in self._tasks.items()}
    
    def create_progress_callback(self, task_id: str) -> Callable:
        """
        Create a progress callback function for a specific task
        
        Args:
            task_id: Task ID
        
        Returns:
            Callback function with signature: on_progress(stage, percentage, message)
        """
        def on_progress(stage: str, percentage: int, message: str):
            """Progress callback"""
            self.update_task(
                task_id=task_id,
                status=TaskStatus.PROCESSING.value,
                progress=percentage,
                stage=stage,
                message=message
            )
        
        return on_progress


# Global task manager instance
task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """Get the global task manager instance"""
    return task_manager

```

---

