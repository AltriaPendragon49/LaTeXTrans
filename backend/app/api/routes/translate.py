"""
Translation API Routes

Provides endpoints for starting translation tasks.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
from backend.app.core.encryption import decrypt_api_key
from backend.app.core.supabase_client import get_supabase_admin_client

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()

# Allow missing Authorization header (guest mode)
security = HTTPBearer(auto_error=False)


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


def get_user_api_config(user_id: str) -> dict:
    """
    从用户设置中获取解密后的 API 配置。
    
    注意：此函数只负责获取配置，不判断是否应该使用。
    调用方应根据 advanced_config.use_author_api 决定是否调用此函数。
    
    Args:
        user_id: 用户 ID
        
    Returns:
        包含 base_url 和 api_key 的字典，或空字典
    """
    try:
        client = get_supabase_admin_client()
        if not client:
            logger.warning("Supabase admin client not available")
            return {}
        
        result = client.table("user_settings").select(
            "custom_base_url, custom_api_key_encrypted"
        ).eq("user_id", user_id).execute()
        
        if not result.data or len(result.data) == 0:
            logger.info(f"No user settings found for user {user_id}")
            return {}
        
        settings = result.data[0]
        
        encrypted_key = settings.get("custom_api_key_encrypted")
        if not encrypted_key:
            logger.info(f"No custom API key stored for user {user_id}")
            return {}
        
        api_key = decrypt_api_key(encrypted_key)
        if not api_key:
            logger.warning(f"Failed to decrypt API key for user {user_id}")
            return {}
        
        logger.info(f"Successfully retrieved user's custom API config for user {user_id}")
        return {
            "base_url": settings.get("custom_base_url"),
            "api_key": api_key
        }
    except Exception as e:
        logger.error(f"Error getting user API config: {e}")
        return {}


def build_llm_config(advanced_config: AdvancedConfig, user_id: str = None) -> Dict[str, Any]:
    """
    Build LLM configuration from advanced config.
    
    优先级顺序：
    1. 使用作者 API（如果 use_author_api=True）
    2. 使用系统设置中保存的 API（已登录用户，从数据库解密）
    3. 使用前端高级配置中传入的 API（访客模式或临时覆盖）
    4. 回退到作者 API
    
    Args:
        advanced_config: Advanced configuration from request
        user_id: Optional user ID for fetching stored API key
    
    Returns:
        LLM configuration dictionary for agent
    """
    # Default: use author's API
    if advanced_config.use_author_api:
        logger.info("Using author's API configuration (use_author_api=True)")
        return settings.get_llm_config()
    
    logger.info(f"Custom API mode: user_id={user_id}, has_custom_api_key_in_request={bool(advanced_config.custom_api_key)}")
    
    # Priority 1: Try to get user's stored API config from system settings
    if user_id:
        logger.info(f"Attempting to get API config from system settings for user {user_id}")
        user_api_config = get_user_api_config(user_id)
        
        if user_api_config.get("api_key"):
            # 系统设置中有 API key，优先使用
            base_url = (user_api_config.get("base_url") or "").rstrip('/')
            if base_url and not base_url.endswith('/v1/chat/completions'):
                base_url = f"{base_url}/v1/chat/completions"
            
            logger.info(f"✅ Using user's stored API config from system settings")
            logger.info(f"   Base URL: {base_url[:50] if base_url else 'default'}...")
            logger.info(f"   API Key: {user_api_config['api_key'][:8]}...***")
            
            return {
                "base_url": base_url if base_url else None,
                "api_key": user_api_config["api_key"],
                "model": advanced_config.translation_model,
                "timeout": 60
            }
        else:
            logger.warning(f"No API key found in system settings for user {user_id}")
    
    # Priority 2: Check if custom config is provided in request (guest mode or override)
    if advanced_config.custom_api_key:
        logger.info("Using API key from request (frontend advanced config)")
        
        base_url = (advanced_config.custom_base_url or "").rstrip('/')
        if base_url and not base_url.endswith('/v1/chat/completions'):
            base_url = f"{base_url}/v1/chat/completions"
        
        logger.info(f"   Base URL: {base_url[:50] if base_url else 'default'}...")
        logger.info(f"   API Key: {advanced_config.custom_api_key[:8]}...***")
        
        return {
            "base_url": base_url if base_url else None,
            "api_key": advanced_config.custom_api_key,
            "model": advanced_config.translation_model,
            "timeout": 60
        }
    
    # Final fallback to author's API
    logger.warning("No custom API configuration available, falling back to author's API")
    return settings.get_llm_config()


async def run_translation(
    task_id: str, 
    target_language: str, 
    source_language: str,
    advanced_config: AdvancedConfig,
    user_id: str = None
):
    """
    Background task to run translation (async version)
    
    Args:
        task_id: Task ID
        target_language: Target language code
        source_language: Source language code
        advanced_config: Advanced configuration options
        user_id: Optional user ID for authenticated users
    """
    logger.info(f"Starting translation for task: {task_id}")
    logger.info(f"Advanced config: mode={advanced_config.translation_mode}, "
                f"compile={advanced_config.compile_strategy}, "
                f"verify={advanced_config.enable_verification}, "
                f"user_id={user_id}")
    
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
        
        # Build LLM config from advanced settings (with user's stored API key if available)
        llm_config = build_llm_config(advanced_config, user_id)
        
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

        # ========== 配置拦截代码 - 开始 ==========
        from backend.tests.test_config_interceptor import ConfigInterceptor
        
        interceptor = ConfigInterceptor()
        config_file = interceptor.capture_config(
            task_id=task_id,
            advanced_config=advanced_config.model_dump(),
            agent_config=agent_config,
            llm_config=llm_config,
            additional_info={
                "target_language": target_language,
                "source_language": source_language,
                "source_path": str(source_path),
                "output_dir": str(output_dir)
            }
        )
        logger.info(f"🔍 配置已拦截并保存到: {config_file}")
        # ========== 配置拦截代码 - 结束 ==========
        
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
    request: TranslateRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Start translation for a task
    
    Args:
        task_id: Task ID from upload or arxiv endpoint
        request: Translation configuration with advanced options
        credentials: Optional bearer token for authenticated users
    
    Returns:
        Translation start confirmation
    
    Raises:
        HTTPException: If task not found or not ready for translation
    """
    logger.info(f"Translation request for task: {task_id}")
    
    # Get user_id from token if authenticated
    user_id = None
    if credentials:
        try:
            # Parse JWT to get user_id (sub claim)
            import base64
            import json
            token = credentials.credentials
            # Decode JWT payload (no verification, just reading claims)
            payload_b64 = token.split('.')[1]
            # Add padding if needed
            payload_b64 += '=' * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            user_id = payload.get('sub')
            logger.info(f"Authenticated user: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to parse user_id from token: {e}")
    
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
            advanced_config=request.advanced_config,
            user_id=user_id
        )
    )
    
    logger.info(f"Translation started in background for task: {task_id}")
    
    return TranslateResponse(
        task_id=task_id,
        status="started",
        message="Translation started in background"
    )
