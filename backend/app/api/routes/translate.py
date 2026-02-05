"""
Translation API Routes

Provides endpoints for starting translation tasks.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import asyncio
import logging
from pathlib import Path

from backend.app.services.task_manager import get_task_manager
from backend.app.services.agents.coordinator_agent import CoordinatorAgent
from backend.app.services.latex_validator import find_main_tex_file
from backend.app.core.config import get_settings, TaskStatus
from backend.app.models.config_models import AdvancedConfig, TRANSLATION_MODE_MAP

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()


class TranslateRequest(BaseModel):
    """Translation request with advanced configuration"""
    target_language: str = Field(default="ch", description="Target language code (e.g., 'ch', 'en')")
    source_language: str = Field(default="en", description="Source language code (e.g., 'en', 'ch')")
    advanced_config: AdvancedConfig = Field(default_factory=AdvancedConfig, description="Advanced configuration options")


class TranslateResponse(BaseModel):
    """Translation response"""
    task_id: str
    status: str
    message: str


def build_llm_config(advanced_config: AdvancedConfig) -> Dict[str, Any]:
    """
    Build LLM configuration from advanced config.
    
    Supports custom API configuration with automatic fallback to author API.
    
    Args:
        advanced_config: Advanced configuration from request
    
    Returns:
        LLM configuration dictionary for agent
    """
    # Default: use author's API
    if advanced_config.use_author_api:
        logger.info("Using author's API configuration")
        return settings.get_llm_config()
    
    # Check if custom config is complete
    if not advanced_config.custom_base_url or not advanced_config.custom_api_key:
        logger.warning("Custom API configuration incomplete, falling back to author's API")
        return settings.get_llm_config()
    
    # Build custom API config
    base_url = advanced_config.custom_base_url.rstrip('/')
    if not base_url.endswith('/v1/chat/completions'):
        base_url = f"{base_url}/v1/chat/completions"
    
    logger.info(f"Using custom API: {base_url[:50]}...")
    
    return {
        "base_url": base_url,
        "api_key": advanced_config.custom_api_key,
        "model": advanced_config.translation_model,
        "timeout": 60
    }


async def run_translation(
    task_id: str, 
    target_language: str, 
    source_language: str,
    advanced_config: AdvancedConfig
):
    """
    Background task to run translation (async version)
    
    Args:
        task_id: Task ID
        target_language: Target language code
        source_language: Source language code
        advanced_config: Advanced configuration options
    """
    logger.info(f"Starting translation for task: {task_id}")
    logger.info(f"Advanced config: mode={advanced_config.translation_mode}, "
                f"compile={advanced_config.compile_strategy}, "
                f"verify={advanced_config.enable_verification}")
    
    try:
        # Get task info
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return
        
        source_path = Path(task["source_path"])
        if not source_path.exists():
            raise Exception(f"Source path not found: {source_path}")
        
        # Find main .tex file using validator
        main_tex_file = find_main_tex_file(source_path)
        if not main_tex_file:
            # Fallback to first .tex file
            tex_files = list(source_path.rglob("*.tex"))
            if not tex_files:
                raise Exception(f"No .tex files found in {source_path}")
            main_tex_file = tex_files[0]
            logger.warning(f"Using fallback main tex file: {main_tex_file}")
        else:
            logger.info(f"Using detected main tex file: {main_tex_file}")
        
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
        
        # Build LLM config from advanced settings
        llm_config = build_llm_config(advanced_config)
        
        # Build config dict for CoordinatorAgent with all advanced settings
        agent_config = {
            "sys_name": "LaTeXTrans",
            "target_language": target_language,
            "source_language": source_language,
            "mode": TRANSLATION_MODE_MAP.get(advanced_config.translation_mode, 0),
            "latex_engine": advanced_config.compile_strategy,
            "use_verification_agent": advanced_config.enable_verification,
            "generate_terminology": advanced_config.generate_terminology_table,
            "llm_config": llm_config
        }
        
        logger.info(f"Agent config: mode={agent_config['mode']}, "
                    f"engine={agent_config['latex_engine']}, "
                    f"verify={agent_config['use_verification_agent']}")
        
        # Create coordinator agent
        coordinator = CoordinatorAgent(
            config=agent_config,
            project_dir=str(source_path),
            output_dir=str(output_dir),
            on_progress=progress_callback
        )
        
        # Run translation workflow asynchronously
        logger.info(f"Running translation workflow for {main_tex_file}")
        await coordinator.workflow_latextrans_async()
        
        # Check if translation succeeded by looking for output PDF
        # The workflow saves PDF as {target_language}_{project_name}/{target_language}_{project_name}.pdf
        project_name = source_path.name
        # Subdirectory logic matching CoordinatorAgent's transed_project_dir
        transed_subdir = f"{target_language}_{project_name}"
        output_pdf = output_dir / transed_subdir / f"{target_language}_{project_name}.pdf"
        
        # Fallback recursive check: prioritize files starting with target_language_
        if not output_pdf.exists():
            prefix = f"{target_language}_"
            found_pdfs = [p for p in output_dir.rglob("*.pdf") if p.name.startswith(prefix)]
            if found_pdfs:
                output_pdf = found_pdfs[0]
                logger.info(f"Found translated PDF via fallback: {output_pdf}")

        if output_pdf.exists():
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.COMPLETED.value,
                progress=100,
                message="Translation completed successfully",
                output_path=str(output_dir)
            )
            logger.info(f"Translation completed: {task_id}")
        else:
            # Check if there were any errors in the output directory
            # If no PDF was generated, mark as completed with warnings
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.COMPLETED_WITH_WARNINGS.value,
                progress=100,
                message="Translation completed but PDF generation may have issues",
                warnings="No PDF file found in output directory",
                output_path=str(output_dir)
            )
            logger.warning(f"Translation completed with warnings: {task_id}")
    
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
    request: TranslateRequest
):
    """
    Start translation for a task
    
    Args:
        task_id: Task ID from upload or arxiv endpoint
        request: Translation configuration with advanced options
    
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
    
    # Store advanced config in task record
    task_manager.update_task(
        task_id=task_id,
        advanced_config=request.advanced_config.model_dump()
    )
    
    # Start background translation using asyncio
    asyncio.create_task(
        run_translation(
            task_id=task_id,
            target_language=request.target_language,
            source_language=request.source_language,
            advanced_config=request.advanced_config
        )
    )
    
    logger.info(f"Translation started in background for task: {task_id}")
    
    return TranslateResponse(
        task_id=task_id,
        status="started",
        message="Translation started in background"
    )
