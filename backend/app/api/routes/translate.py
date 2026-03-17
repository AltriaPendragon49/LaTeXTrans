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
import hashlib
import json
import shutil
from pathlib import Path

from backend.app.services.task_manager import get_task_manager
from backend.app.services.agents.coordinator_agent import CoordinatorAgent
from backend.app.services.latex_validator import find_main_tex_file
from backend.app.services.config_capture import capture_task_config
from backend.app.core.config import get_settings, TaskStatus
from backend.app.models.config_models import AdvancedConfig, TRANSLATION_MODE_MAP
from backend.app.core.encryption import decrypt_api_key
from backend.app.services.agents.llm_runtime import resolve_task_llm_max_concurrent_requests
from backend.app.core.supabase_client import get_supabase_admin_client, create_supabase_admin_client
from backend.app.services.latex.utils import batch_download_arxiv_tex, extract_arxiv_ids, get_arxiv_category
from backend.app.utils.async_blocking import run_db_blocking

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()
CLI_PARITY_TASK_LLM_MAX_CONCURRENT_REQUESTS = 10
CLI_PARITY_MODEL_CONTEXT_TOKENS = 32000
CLI_PARITY_PROMPT_RESERVE_TOKENS = 4096

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


class BatchTranslateRequest(BaseModel):
    """Batch translation request (authenticated users only)"""
    arxiv_ids: list = Field(..., description="List of arXiv IDs (max 9)")
    target_language: str = Field(default="ch")
    source_language: str = Field(default="en")
    advanced_config: AdvancedConfig = Field(default_factory=AdvancedConfig)


class BatchTranslateResponse(BaseModel):
    """Batch translation response"""
    batch_id: str
    task_ids: list
    message: str
    queued_count: int


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


async def get_user_api_config_async(user_id: str) -> dict:
    """
    Async-safe wrapper for fetching user API config from Supabase.
    """
    try:
        client = get_supabase_admin_client()
        if not client:
            logger.warning("Supabase admin client not available")
            return {}

        def _shared_call():
            return client.table("user_settings").select(
                "custom_base_url, custom_api_key_encrypted"
            ).eq("user_id", user_id).execute()

        def _per_call_client():
            c = create_supabase_admin_client()
            if not c:
                return None
            return c.table("user_settings").select(
                "custom_base_url, custom_api_key_encrypted"
            ).eq("user_id", user_id).execute()

        result = await run_db_blocking(_shared_call, per_call_client_call=_per_call_client)
        if result is None or not result.data or len(result.data) == 0:
            logger.info(f"No user settings found for user {user_id}")
            return {}

        settings_row = result.data[0]
        encrypted_key = settings_row.get("custom_api_key_encrypted")
        if not encrypted_key:
            logger.info(f"No custom API key stored for user {user_id}")
            return {}

        api_key = decrypt_api_key(encrypted_key)
        if not api_key:
            logger.warning(f"Failed to decrypt API key for user {user_id}")
            return {}

        logger.info(f"Successfully retrieved user's custom API config for user {user_id}")
        return {
            "base_url": settings_row.get("custom_base_url"),
            "api_key": api_key
        }
    except Exception as e:
        logger.error(f"Error getting user API config async: {e}")
        return {}


def build_llm_config(advanced_config: AdvancedConfig, user_id: str = None) -> Dict[str, Any]:
    """
    Build LLM configuration from advanced config.
    
    优先级顺序：
    1. 使用作者 API（如果 use_author_api=True）
    2. 使用前端高级配置中传入的 API（访客模式或临时覆盖）
    3. 使用系统设置中保存的 API（已登录用户，从数据库解密）
    4. 回退到作者 API
    
    Args:
        advanced_config: Advanced configuration from request
        user_id: Optional user ID for fetching stored API key
    
    Returns:
        LLM configuration dictionary for agent
    """
    # Priority 0: Default: use author's API if explicitly requested
    if advanced_config.use_author_api:
        logger.info("Using author's API configuration (use_author_api=True)")
        return settings.get_llm_config()
    
    logger.info(f"Custom API mode: user_id={user_id}, has_custom_api_key_in_request={bool(advanced_config.custom_api_key)}")
    
    # Priority 1: Check if custom config is provided in request (guest mode or override)
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
            "timeout": settings.llm_timeout
        }

    # Priority 2: Try to get user's stored API config from system settings
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
                "timeout": settings.llm_timeout
            }
        else:
            logger.warning(f"No API key found in system settings for user {user_id}")
    
    # Final fallback to author's API
    logger.warning("No custom API configuration available, falling back to author's API")
    return settings.get_llm_config()


async def build_llm_config_async(advanced_config: AdvancedConfig, user_id: str = None) -> Dict[str, Any]:
    """
    Async-safe variant of build_llm_config for async request paths.
    """
    if advanced_config.use_author_api:
        logger.info("Using author's API configuration (use_author_api=True)")
        return settings.get_llm_config()

    logger.info(f"Custom API mode: user_id={user_id}, has_custom_api_key_in_request={bool(advanced_config.custom_api_key)}")

    if advanced_config.custom_api_key:
        logger.info("Using API key from request (frontend advanced config)")
        base_url = (advanced_config.custom_base_url or "").rstrip('/')
        if base_url and not base_url.endswith('/v1/chat/completions'):
            base_url = f"{base_url}/v1/chat/completions"
        return {
            "base_url": base_url if base_url else None,
            "api_key": advanced_config.custom_api_key,
            "model": advanced_config.translation_model,
            "timeout": settings.llm_timeout
        }

    if user_id:
        logger.info(f"Attempting to get API config from system settings for user {user_id}")
        user_api_config = await get_user_api_config_async(user_id)
        if user_api_config.get("api_key"):
            base_url = (user_api_config.get("base_url") or "").rstrip('/')
            if base_url and not base_url.endswith('/v1/chat/completions'):
                base_url = f"{base_url}/v1/chat/completions"
            return {
                "base_url": base_url if base_url else None,
                "api_key": user_api_config["api_key"],
                "model": advanced_config.translation_model,
                "timeout": settings.llm_timeout
            }
        logger.warning(f"No API key found in system settings for user {user_id}")

    logger.warning("No custom API configuration available, falling back to author's API")
    return settings.get_llm_config()

def compute_config_hash(
    arxiv_id: Optional[str],
    source_language: str,
    target_language: str,
    translation_mode: str,
    compile_strategy: str,
    source_path: Optional[str] = None
) -> str:
    """
    生成翻译配置签名,用于快速匹配已有结果
    
    Args:
        arxiv_id: arXiv 论文 ID (or None for uploaded files)
        source_language: 源语言
        target_language: 目标语言
        translation_mode: 翻译模式
        compile_strategy: 编译策略
        source_path: 源文件路径 (用于区分不同上传内容)
    
    Returns:
        MD5 hash 字符串
    """
    # For arxiv tasks, arxiv_id uniquely identifies the paper.
    # For uploaded files, arxiv_id is None so we MUST include
    # source_path to prevent different papers from sharing a hash.
    content_key = arxiv_id or source_path or ""
    config = {
        "content_key": content_key,
        "source_language": source_language,
        "target_language": target_language,
        "translation_mode": translation_mode,
        "compile_strategy": compile_strategy
    }
    return hashlib.md5(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()


async def find_reusable_output(config_hash: str, task_id: str) -> Optional[str]:
    """
    查询是否有配置完全一致的已完成任务可复用
    
    使用 admin client 绕过 RLS (跨用户查询)
    排除当前任务自身
    
    Args:
        config_hash: 配置签名
        task_id: 当前任务 ID (排除自身)
    
    Returns:
        已完成任务的 output_path,若无则返回 None
    """
    try:
        client = get_supabase_admin_client()
        if not client:
            logger.warning("Supabase admin client not available for output reuse")
            return None
        
        def _shared_call():
            return client.table("translation_tasks").select(
                "output_path"
            ).eq(
                "config_hash", config_hash
            ).eq(
                "status", "completed"
            ).neq(
                "task_id", task_id
            ).limit(1).execute()

        def _per_call_client():
            c = create_supabase_admin_client()
            if not c:
                return None
            return c.table("translation_tasks").select(
                "output_path"
            ).eq(
                "config_hash", config_hash
            ).eq(
                "status", "completed"
            ).neq(
                "task_id", task_id
            ).limit(1).execute()

        result = await run_db_blocking(_shared_call, per_call_client_call=_per_call_client)
        if result is None:
            return None
        
        if result.data and result.data[0].get("output_path"):
            output_path = Path(result.data[0]["output_path"])
            if output_path.exists():
                logger.info(f"Found reusable output: {output_path}")
                return str(output_path)
            else:
                logger.warning(f"Reusable output path exists in DB but not on filesystem: {output_path}")
        
        return None
        
    except Exception as e:
        logger.warning(f"Error searching for reusable output: {e}")
        return None


async def persist_task_config_hash(task_id: str, config_hash: str) -> bool:
    """Persist config_hash for an already-created authenticated task row."""
    try:
        client = get_supabase_admin_client()
        if not client:
            logger.warning("Supabase admin client not available for config_hash persistence")
            return False

        def _shared_call():
            return client.table("translation_tasks").update({
                "config_hash": config_hash
            }).eq("task_id", task_id).execute()

        def _per_call_client():
            c = create_supabase_admin_client()
            if not c:
                return None
            return c.table("translation_tasks").update({
                "config_hash": config_hash
            }).eq("task_id", task_id).execute()

        await run_db_blocking(_shared_call, per_call_client_call=_per_call_client)
        logger.info(f"Stored config_hash in database for task {task_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to store config_hash for task {task_id}: {e}")
        return False


async def copy_output(source_output: str, task_id: str) -> str:
    """
    深拷贝已有 output 到新任务目录
    
    Args:
        source_output: 源 output 目录路径
        task_id: 新任务 ID
    
    Returns:
        新的 output 目录路径
    """
    dest = settings.outputs_dir / task_id
    if dest.exists():
        shutil.rmtree(dest)
    
    logger.info(f"Copying output from {source_output} to {dest}")
    shutil.copytree(source_output, dest)
    logger.info(f"Output copy completed: {dest}")
    
    return str(dest)


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
                f"user_id={user_id}")
    
    try:
        # Check if task was cancelled before starting
        if task_manager.is_cancelled(task_id):
            logger.info(f"Task {task_id} was cancelled before translation started, aborting")
            return
        
        # Get task info
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return
        
        raw_source_path = task.get("source_path")
        arxiv_id = task.get("arxiv_id")

        # Helper: re-download arXiv source if path is missing or path doesn't exist
        async def _ensure_source_path() -> Path:
            nonlocal raw_source_path
            if raw_source_path:
                p = Path(raw_source_path)
                if p.exists():
                    return p
                logger.warning(f"Source path on disk not found: {p}")
            else:
                logger.warning(f"Task {task_id} has no source_path recorded")

            if arxiv_id and task.get("source_type") == "arxiv":
                logger.info(f"Re-downloading arXiv source for {arxiv_id}...")
                task_manager.update_task(
                    task_id=task_id,
                    message=f"源文件缺失，正在重新下载 arXiv {arxiv_id}...",
                    user_id=user_id
                )
                save_dir = str(settings.uploads_dir / f"arxiv_{arxiv_id}")
                source_dirs = await asyncio.to_thread(
                    batch_download_arxiv_tex,
                    [arxiv_id],
                    save_dir,
                    task_manager,
                    task_id,
                )
                if not source_dirs:
                    raise Exception(f"Re-download failed for arXiv {arxiv_id}: no source returned")
                new_path = Path(source_dirs[0])
                task_manager.update_task(
                    task_id=task_id,
                    source_path=str(new_path),
                    source_available=True,
                    user_id=user_id
                )
                logger.info(f"Re-download succeeded, source_path updated to: {new_path}")
                return new_path

            raise Exception(f"Source path not found: {raw_source_path}")

        source_path = await _ensure_source_path()
        
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
        
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PROCESSING.value,
            progress=0,
            message="Checking for reusable output...",
            detail_code="task_waiting",
            output_path=str(output_dir),  # eagerly written for lazy reconciliation
            user_id=user_id
        )
        
        # 计算配置签名
        config_hash = compute_config_hash(
            arxiv_id=task.get("arxiv_id"),
            source_language=source_language,
            target_language=target_language,
            translation_mode=advanced_config.translation_mode,
            compile_strategy=advanced_config.compile_strategy,
            source_path=str(source_path)
        )
        logger.info(f"Config hash for task {task_id}: {config_hash}")
        
        # 尝试找到可复用的 output
        reusable_output = await find_reusable_output(config_hash, task_id)
        if reusable_output:
            logger.info(f"🎉 Found reusable output for task {task_id}, skipping translation")
            
            # 深拷贝 output
            new_output_path = await copy_output(reusable_output, task_id)
            
            # 更新任务状态为完成
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.COMPLETED.value,
                progress=100,
                message="Translation completed (reused existing output)",
                detail_code="compile_complete",
                output_path=new_output_path,
                user_id=user_id
            )
            logger.info(f"Task {task_id} completed via output reuse")
            return
        
        # 没有找到可复用的,继续正常翻译
        logger.info("No reusable output found, proceeding with translation")
        
        # Update task status
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PROCESSING.value,
            progress=0,
            message="Initializing translation...",
            detail_code="translation_starting",
            user_id=user_id
        )
        
        # Create progress callback
        progress_callback = task_manager.create_progress_callback(task_id)
        
        # Build LLM config from advanced settings (with user's stored API key if available)
        llm_config = await build_llm_config_async(advanced_config, user_id)
        
        # Build config dict for CoordinatorAgent with all advanced settings
        task_llm_max_concurrent_requests = resolve_task_llm_max_concurrent_requests(
            default=settings.llm_max_concurrent_requests,
            cap=CLI_PARITY_TASK_LLM_MAX_CONCURRENT_REQUESTS,
        )
        category_map: dict[str, list[str]] = {}
        if arxiv_id:
            try:
                category_map = await asyncio.to_thread(get_arxiv_category, [arxiv_id])
            except Exception as exc:
                logger.warning("Failed to fetch arXiv category for %s: %s", arxiv_id, exc)

        formatting = (
            advanced_config.formatting.model_dump(exclude_none=True)
            if advanced_config.formatting is not None
            else None
        )
        agent_config = {
            "sys_name": "LaTeXTrans",
            "target_language": target_language,
            "source_language": source_language,
            "mode": TRANSLATION_MODE_MAP.get(advanced_config.translation_mode, 0),
            "translation_mode": advanced_config.translation_mode,
            "latex_engine": advanced_config.compile_strategy,
            "use_verification_agent": False,
            "generate_terminology": advanced_config.generate_terminology_table,
            "generate_terminology_table": advanced_config.generate_terminology_table,
            "update_term": False,
            "user_term": "",
            "category": category_map,
            "formatting": formatting,
            "use_compilation_diagnostics": True,
            "enable_compile_first_structural_fallback": settings.enable_compile_first_structural_fallback,
            "enable_post_compile_target_language_fallback": settings.enable_post_compile_target_language_fallback,
            "structural_fallback_ratio_cap": settings.structural_fallback_ratio_cap,
            "structural_fallback_cap_mode": settings.structural_fallback_cap_mode,
            "model_context_tokens": settings.model_context_tokens or CLI_PARITY_MODEL_CONTEXT_TOKENS,
            "prompt_reserve_tokens": settings.prompt_reserve_tokens or CLI_PARITY_PROMPT_RESERVE_TOKENS,
            "llm_max_concurrent_requests": task_llm_max_concurrent_requests,
            "task_id": task_id,
            "output_dir": str(output_dir),
            "tex_sources_dir": str(settings.uploads_dir),
            "llm_config": llm_config
        }

        logger.info(f"Agent config: mode={agent_config['mode']}, "
                    f"engine={agent_config['latex_engine']}, "
                    f"verify={agent_config['use_verification_agent']}, "
                    f"llm_max_concurrent_requests={agent_config['llm_max_concurrent_requests']}")

        captured_config_file = capture_task_config(
            task_id=task_id,
            advanced_config=advanced_config.model_dump(),
            agent_config=agent_config,
            llm_config=llm_config,
            additional_info={
                "arxiv_id": arxiv_id,
                "is_logged_in": bool(user_id),
                "user_id": user_id,
                "task_id": task_id,
                "target_language": target_language,
                "source_language": source_language,
                "source_path": str(source_path),
                "output_dir": str(output_dir),
            },
        )
        if captured_config_file:
            logger.info(f"Task config snapshot saved: {captured_config_file}")





      
        
        # Create coordinator agent
        coordinator = CoordinatorAgent(
            config=agent_config,
            project_dir=str(source_path),
            output_dir=str(output_dir),
            on_progress=progress_callback
        )
        
        # Run translation workflow asynchronously
        logger.info(f"Running translation workflow for {main_tex_file}")
        workflow_result = await coordinator.workflow_latextrans_async()
        workflow_status = (workflow_result or {}).get("status")
        error_summary = (workflow_result or {}).get("error_summary")
        warning_summary = (workflow_result or {}).get("warnings")
        pdf_path = (workflow_result or {}).get("pdf_path")
        failure_reason_code = (workflow_result or {}).get("failure_reason_code")
        failure_class = (workflow_result or {}).get("failure_class")
        guard_phase = (workflow_result or {}).get("guard_phase")
        replay_bundle_ref = (workflow_result or {}).get("replay_bundle_ref")

        if pdf_path and not Path(pdf_path).exists():
            logger.error(
                f"Workflow returned missing compiled PDF path for task {task_id}: {pdf_path}"
            )
            workflow_status = "failed_compilation"
            error_summary = error_summary or f"Compilation returned a missing PDF path: {pdf_path}"
            pdf_path = None

        if workflow_status == "structure_invalid":
            error_text = error_summary or "LaTeX structure guard rejected bundle before compilation"
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.STRUCTURE_INVALID.value,
                progress=100,
                message=error_text,
                error=error_text,
                warnings=warning_summary,
                output_path=str(output_dir),
                failure_reason_code=failure_reason_code,
                failure_class=failure_class or "structural",
                guard_phase=guard_phase,
                replay_bundle_ref=replay_bundle_ref,
                user_id=user_id,
            )
            logger.warning(f"Translation aborted by structure guard: {task_id}")
            return

        if workflow_status == "failed_compilation" or not pdf_path:
            error_text = error_summary or "Compilation failed without detailed error output"
            failure_msg = f"PDF compilation failed: {error_text}"
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.FAILED_COMPILATION.value,
                progress=100,
                message=failure_msg,
                error=error_text,
                warnings=warning_summary,
                output_path=str(output_dir),
                failure_reason_code=failure_reason_code,
                failure_class=failure_class,
                guard_phase=guard_phase,
                replay_bundle_ref=replay_bundle_ref,
                user_id=user_id
            )
            logger.warning(f"Translation finished with compilation failure: {task_id}")
            return

        if workflow_status == "completed_with_warnings":
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.COMPLETED_WITH_WARNINGS.value,
                progress=100,
                message="Translation completed with compilation warnings",
                detail_code="compile_complete",
                warnings=warning_summary or "Compilation completed with warnings",
                output_path=str(output_dir),
                user_id=user_id
            )
            logger.info(f"Translation completed with compilation warnings: {task_id}")
        else:
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.COMPLETED.value,
                progress=100,
                message="Translation completed successfully",
                detail_code="compile_complete",
                output_path=str(output_dir),
                user_id=user_id
            )
            logger.info(f"Translation completed: {task_id}")
    
    except Exception as e:
        logger.error(f"Translation error for task {task_id}: {e}", exc_info=True)
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"Translation error: {str(e)}",
            user_id=user_id
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
            import base64
            import json
            token = credentials.credentials
            payload_b64 = token.split('.')[1]
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

    if task["status"] in [TaskStatus.PROCESSING.value, TaskStatus.QUEUED.value]:
        raise HTTPException(
            status_code=400,
            detail="Task is already being processed or queued"
        )

    # Check user quota (authenticated users only)
    from backend.app.services.task_manager import get_task_queue
    tq = get_task_queue()
    if user_id and tq:
        user_active = tq.get_user_active_count(user_id)
        if user_active >= settings.max_user_active_tasks:
            raise HTTPException(
                status_code=429,
                detail=f"Too many active tasks. You have {user_active}/{settings.max_user_active_tasks} active tasks. Please wait for existing tasks to complete."
            )

    config_hash = compute_config_hash(
        arxiv_id=task.get("arxiv_id"),
        source_language=request.source_language,
        target_language=request.target_language,
        translation_mode=request.advanced_config.translation_mode,
        compile_strategy=request.advanced_config.compile_strategy,
        source_path=task.get("source_path")
    )
    logger.info(f"Computed config_hash for task {task_id}: {config_hash}")

    # Keep the final config snapshot in memory before delayed persistence so
    # both the initial insert and any retry can include the same metadata.
    task_manager.update_task(
        task_id=task_id,
        source_language=request.source_language,
        target_language=request.target_language,
        advanced_config=request.advanced_config.model_dump(),
        config_hash=config_hash,
    )

    # ✅ Persist to database (delayed creation)
    persisted = task_manager.persist_task_if_needed(task_id)
    if not persisted:
        logger.warning(f"Failed to persist task {task_id}, but continuing with translation")
    elif user_id:
        await persist_task_config_hash(task_id, config_hash)

    # Enqueue translation via TaskQueue
    if tq:
        # Compute token_hash for per-bucket routing isolation
        _llm_cfg = await build_llm_config_async(request.advanced_config, user_id)
        _api_key = (_llm_cfg.get("api_key") or "").encode()
        token_hash = hashlib.md5(_api_key).hexdigest()

        async def translation_factory():
            await run_translation(
                task_id=task_id,
                target_language=request.target_language,
                source_language=request.source_language,
                advanced_config=request.advanced_config,
                user_id=user_id
            )

        await tq.enqueue(task_id, translation_factory, user_id, token_hash)
        logger.info(f"Task {task_id} enqueued via TaskQueue (token_hash={token_hash[:8]}...)")
    else:
        # Fallback: direct asyncio.create_task (TaskQueue not initialized)
        logger.warning("TaskQueue not initialized, falling back to direct asyncio.create_task")
        asyncio.create_task(
            run_translation(
                task_id=task_id,
                target_language=request.target_language,
                source_language=request.source_language,
                advanced_config=request.advanced_config,
                user_id=user_id
            )
        )

    return TranslateResponse(
        task_id=task_id,
        status="queued",
        message="Translation queued successfully"
    )


@router.get("/queue/status")
async def get_queue_status(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Get current task queue status.

    Returns:
        Queue status including active count, queue size, and max concurrent
    """
    from backend.app.services.task_manager import get_task_queue
    tq = get_task_queue()

    if not tq:
        return {
            "active_count": 0,
            "queue_size": 0,
            "max_concurrent": settings.max_concurrent_translations,
            "total_pending": 0,
            "user_quota_used": 0
        }

    status = tq.get_status()

    # Add user quota info if authenticated
    user_id = None
    if credentials:
        try:
            import base64
            import json
            token = credentials.credentials
            payload_b64 = token.split('.')[1]
            payload_b64 += '=' * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            user_id = payload.get('sub')
        except Exception:
            pass

    status["user_quota_used"] = tq.get_user_active_count(user_id) if user_id else 0
    status["user_quota_max"] = settings.max_user_active_tasks
    return status


@router.post("/batch-translate", response_model=BatchTranslateResponse)
async def batch_translate(
    request: BatchTranslateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True))
):
    """
    Batch translation for authenticated users only.
    Accepts up to 9 arXiv IDs and creates independent translation tasks.

    The endpoint returns immediately after creating tasks in memory and persisting
    them to the database. The actual arXiv download and translation enqueue happen
    in background coroutines (asyncio.create_task), so the HTTP request is not
    blocked by potentially slow network downloads.

    Args:
        request: Batch translation request with arXiv IDs and config
        credentials: Required bearer token (401 if missing)

    Returns:
        Batch ID and list of task IDs
    """
    # Parse user_id from JWT
    user_id = None
    try:
        import base64
        import json
        token = credentials.credentials
        payload_b64 = token.split('.')[1]
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        user_id = payload.get('sub')
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required for batch translation")

    # Validate arxiv_ids count
    arxiv_ids = request.arxiv_ids
    if not arxiv_ids:
        raise HTTPException(status_code=400, detail="No arXiv IDs provided")
    if len(arxiv_ids) > 9:
        raise HTTPException(
            status_code=400,
            detail=f"Batch limit exceeded: maximum 9 arXiv IDs per request, got {len(arxiv_ids)}"
        )

    # Check user quota
    from backend.app.services.task_manager import get_task_queue
    tq = get_task_queue()
    if tq:
        user_active = tq.get_user_active_count(user_id)
        remaining = settings.max_user_active_tasks - user_active
        if remaining <= 0:
            raise HTTPException(
                status_code=429,
                detail=f"Quota exceeded: you have {user_active}/{settings.max_user_active_tasks} active tasks. Please wait for existing tasks to complete."
            )
        if len(arxiv_ids) > remaining:
            raise HTTPException(
                status_code=429,
                detail=f"Quota exceeded: you can submit at most {remaining} more tasks (currently {user_active}/{settings.max_user_active_tasks} active)."
            )

    import uuid
    batch_id = str(uuid.uuid4())
    task_ids = []
    errors = []

    for raw_id in arxiv_ids:
        # Normalize arXiv ID (strip URL prefix etc.)
        normalized = extract_arxiv_ids([raw_id])
        if not normalized:
            errors.append(f"{raw_id}: invalid arXiv ID format")
            continue
        arxiv_id = normalized[0]

        try:
            # Create task in memory only (no DB yet)
            task_id = task_manager.create_task(
                source_type="arxiv",
                arxiv_id=arxiv_id,
                user_id=user_id,
                persist_to_db=False
            )

            # ✅ Update source/target language and config in memory BEFORE persisting,
            # so the DB record captures actual translation config instead of defaults.
            config_hash = compute_config_hash(
                arxiv_id=arxiv_id,
                source_language=request.source_language,
                target_language=request.target_language,
                translation_mode=request.advanced_config.translation_mode,
                compile_strategy=request.advanced_config.compile_strategy,
            )
            task_manager.update_task(
                task_id=task_id,
                source_language=request.source_language,
                target_language=request.target_language,
                advanced_config=request.advanced_config.model_dump(),
                config_hash=config_hash,
            )

            # ✅ Persist to DB immediately (synchronous fast attempt).
            # If Supabase is unreachable, silently retry in background (2x, 5s apart).
            # On total failure: task is registered for auto-cleanup and persist_failed=True
            # is set in memory so the frontend can warn the user.
            persisted = task_manager.persist_task_if_needed(task_id)
            if not persisted:
                logger.warning(
                    f"[BatchTranslate] Initial persist failed for {task_id}, "
                    f"scheduling background retry"
                )
                asyncio.create_task(
                    task_manager.persist_task_with_retry(task_id, retries=2, delay=5.0)
                )
            else:
                await persist_task_config_hash(task_id, config_hash)

            task_ids.append(task_id)

            # ✅ Launch download + enqueue in background (non-blocking).
            # This prevents the HTTP request from blocking for minutes while
            # downloading arXiv source packages over the network.
            # Compute token_hash for bucket routing (same key as for single-task enqueue)
            _batch_llm_cfg = await build_llm_config_async(request.advanced_config, user_id)
            _batch_token_hash = hashlib.md5(
                (_batch_llm_cfg.get("api_key") or "").encode()
            ).hexdigest()
            asyncio.create_task(
                _download_and_enqueue(
                    task_id=task_id,
                    arxiv_id=arxiv_id,
                    user_id=user_id,
                    source_language=request.source_language,
                    target_language=request.target_language,
                    advanced_config=request.advanced_config,
                    tq=tq,
                    token_hash=_batch_token_hash,
                )
            )
            logger.info(f"[BatchTranslate] Created task {task_id} for arxiv_id={arxiv_id}, download started in background")

        except Exception as e:
            logger.error(f"[BatchTranslate] Failed to process arxiv_id={arxiv_id}: {e}")
            errors.append(f"{arxiv_id}: {str(e)}")

    if not task_ids:
        raise HTTPException(
            status_code=500,
            detail=f"All batch tasks failed: {'; '.join(errors)}"
        )

    return BatchTranslateResponse(
        batch_id=batch_id,
        task_ids=task_ids,
        message=f"Batch translation started: {len(task_ids)} tasks queued" + (
            f" ({len(errors)} failed)" if errors else ""
        ),
        queued_count=len(task_ids)
    )


async def _download_and_enqueue(
    task_id: str,
    arxiv_id: str,
    user_id: str,
    source_language: str,
    target_language: str,
    advanced_config,
    tq,
    token_hash: str = "default",
):
    """
    Background coroutine: download arXiv source and enqueue translation.

    Runs outside the HTTP request lifecycle so it does NOT block batch_translate.
    Progress is visible via GET /api/tasks/{task_id}.

    Flow:
        1. Update task status → processing (downloading)
        2. Download arXiv source in thread pool (blocking I/O)
        3. Update task status → pending (source available)
        4. Enqueue translation via TaskQueue
    """
    logger.info(f"[BatchDownload] Starting background download for task {task_id}, arxiv_id={arxiv_id}")
    try:
        # Step 1: Mark as downloading
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PROCESSING.value,
            progress=0,
            stage="downloading",
            message=f"正在下载 arXiv 论文 {arxiv_id}...",
            detail_code="download_source_starting",
            user_id=user_id,
        )

        # Step 2: Download arXiv source in thread pool (blocking network I/O)
        source_dirs = await asyncio.to_thread(
            batch_download_arxiv_tex,
            [arxiv_id],
            str(settings.uploads_dir / f"arxiv_{arxiv_id}"),
            task_manager,
            task_id,
        )

        if not source_dirs:
            raise ValueError(f"arXiv 论文 {arxiv_id} 没有可用的 TeX 源码")

        source_path = source_dirs[0]

        # Step 3: Mark source as available
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PENDING.value,
            progress=100,
            message=f"arXiv 论文 {arxiv_id} 下载完成，等待翻译",
            detail_code="download_source_complete",
            source_path=source_path,
            source_available=True,
            user_id=user_id,
        )

        # Step 4: Enqueue translation
        if tq:
            async def make_factory(tid, uid, src, tgt, cfg):
                async def factory():
                    await run_translation(
                        task_id=tid,
                        target_language=tgt,
                        source_language=src,
                        advanced_config=cfg,
                        user_id=uid,
                    )
                return factory

            factory = await make_factory(task_id, user_id, source_language, target_language, advanced_config)
            await tq.enqueue(task_id, factory, user_id, token_hash)
        else:
            asyncio.create_task(
                run_translation(
                    task_id=task_id,
                    target_language=target_language,
                    source_language=source_language,
                    advanced_config=advanced_config,
                    user_id=user_id,
                )
            )

        logger.info(f"[BatchDownload] Task {task_id} enqueued for arxiv_id={arxiv_id}")

    except Exception as e:
        logger.error(f"[BatchDownload] Failed for task {task_id} (arxiv_id={arxiv_id}): {e}", exc_info=True)
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"下载失败: {str(e)}",
            user_id=user_id,
        )
