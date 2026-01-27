"""
Translation API Routes

Provides endpoints for starting translation tasks.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
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
    Background task to run translation (async version)
    
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
        
        # Load LLM config and build agent config
        llm_config = settings.get_llm_config()
        
        # Build config dict for CoordinatorAgent
        # Keep llm_config as nested structure as expected by agents
        agent_config = {
            "sys_name": "LaTeXTrans",
            "target_language": target_language,
            "source_language": source_language,
            "mode": 0,  # Translation mode: 0 = full translation
            "llm_config": llm_config  # Keep as nested dict
        }
        
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
        # The workflow saves PDF as {target_language}_{project_name}.pdf
        project_name = source_path.name
        output_pdf = output_dir / f"{target_language}_{project_name}.pdf"
        
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
        request: Translation configuration
    
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
    
    # Start background translation using asyncio
    import asyncio
    asyncio.create_task(
        run_translation(
            task_id=task_id,
            target_language=request.target_language,
            source_language=request.source_language
        )
    )
    
    logger.info(f"Translation started in background for task: {task_id}")
    
    return TranslateResponse(
        task_id=task_id,
        status="started",
        message="Translation started in background"
    )
