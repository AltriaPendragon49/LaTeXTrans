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

from backend.app.services.task_manager import (
    clear_cached_runtime_artifacts,
    get_task_manager,
    get_task_queue,
)
from backend.app.services import task_artifact_storage
from backend.app.services import task_manager as task_manager_module
from backend.app.services.agents.coordinator_agent import CoordinatorAgent
from backend.app.services.latex_validator import find_main_tex_file
from backend.app.services.config_capture import capture_task_config
from backend.app.core.auth import (
    optional_current_user,
    require_current_user,
    resolve_current_user_id,
)
from backend.app.core.config import get_settings, TaskStatus
from backend.app.repositories import TranslationTaskRepository, UserSettingsRepository
from backend.app.models.config_models import (
    AdvancedConfig,
    ORIGIN_CLI_PARITY_MODE,
    TRANSLATION_MODE_MAP,
    normalize_origin_cli_parity_agent_config,
)
from backend.app.core.encryption import decrypt_api_key
from backend.app.services.agents.llm_runtime import resolve_task_llm_max_concurrent_requests
from backend.app.services.agents.llm_token_pool import (
    compute_pool_routing_key,
    LlmMemberScheduler,
)
from backend.app.services.translation_quota_service import (
    DailyQuotaExceededError,
    TranslationQuotaService,
)
from backend.app.services.latex.utils import batch_download_arxiv_tex, extract_arxiv_ids, get_arxiv_category
from backend.app.utils.async_blocking import run_db_blocking

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()
task_manager = get_task_manager()
CLI_PARITY_TASK_LLM_MAX_CONCURRENT_REQUESTS = 10
CLI_PARITY_MODEL_CONTEXT_TOKENS = 32000
CLI_PARITY_PROMPT_RESERVE_TOKENS = 4096


def resolve_llm_task_capacity(llm_config: Dict[str, Any]) -> int:
    members = list(llm_config.get("pool_members") or [])
    if not members:
        return 1
    scheduler = LlmMemberScheduler(
        members=members,
        reserve_count=int(llm_config.get("reserve_count") or 0),
        default_member_concurrency=int(llm_config.get("default_member_concurrency") or 1),
        pool_concurrency=llm_config.get("shared_pool_concurrency") or llm_config.get("pool_concurrency"),
    )
    return max(int(scheduler.community_task_capacity() or 1), 1)

# Allow missing Authorization header (guest mode)
security = HTTPBearer(auto_error=False)


if hasattr(task_manager_module, "is_runtime_shutting_down"):
    is_runtime_shutting_down = task_manager_module.is_runtime_shutting_down
else:
    def is_runtime_shutting_down() -> bool:
        return False


def _schedule_community_publish_watch(task_id: str, user_id: Optional[str]) -> None:
    if not user_id:
        return

    async def _watch() -> None:
        from backend.app.services import paper_service

        await paper_service.watch_task_and_publish_community_library(task_id=task_id)

    asyncio.create_task(_watch())


def get_translation_task_repository() -> TranslationTaskRepository:
    return TranslationTaskRepository()


def get_translation_quota_service() -> TranslationQuotaService:
    return TranslationQuotaService()


def _quota_exceeded_detail(exc: DailyQuotaExceededError) -> dict[str, Any]:
    snapshot = exc.snapshot
    return {
        "code": "DAILY_LATEX_QUOTA_EXCEEDED",
        "message": "Daily LaTeX translation quota exceeded.",
        "requested_count": exc.requested_count,
        "limit": snapshot.limit,
        "used": snapshot.used,
        "remaining": snapshot.remaining,
        "quota_date": snapshot.quota_date,
        "reset_timezone": snapshot.reset_timezone,
    }


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


def normalize_origin_cli_parity_advanced_config(advanced_config: AdvancedConfig) -> AdvancedConfig:
    """Return the user config shape that matches the effective origin CLI parity kernel."""
    if hasattr(advanced_config, "model_copy"):
        normalized = advanced_config.model_copy(deep=True)
    else:
        normalized = AdvancedConfig(**advanced_config.model_dump())
    normalized.translation_core_mode = ORIGIN_CLI_PARITY_MODE
    normalized.translation_mode = "full"
    normalized.compile_strategy = "auto"
    # Preserve the user's choice: only default to False if not already set.
    if getattr(normalized, "generate_terminology_table", None) is None:
        normalized.generate_terminology_table = False
    return normalized


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
        settings_row = UserSettingsRepository().get_user_settings(user_id)
        if not settings_row:
            logger.info(f"No user settings found for user {user_id}")
            return {}

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
        logger.error(f"Error getting user API config: {e}")
        return {}


async def get_user_api_config_async(user_id: str) -> dict:
    """
    Async-safe wrapper for fetching user API config from local persistence.
    """
    try:
        settings_row = await run_db_blocking(
            lambda: UserSettingsRepository().get_user_settings(user_id)
        )
        if not settings_row:
            logger.info(f"No user settings found for user {user_id}")
            return {}

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


def _build_system_managed_llm_config(advanced_config: AdvancedConfig) -> Dict[str, Any]:
    members = settings.get_llm_system_pool_members()
    if not members:
        return {}

    config: Dict[str, Any] = {
        "api_key": members[0]["api_key"],
        "base_url": members[0]["base_url"],
        "model": advanced_config.translation_model,
        "timeout": settings.llm_timeout,
        "reserve_count": settings.llm_pool_reserve_count,
        "default_member_concurrency": settings.llm_member_default_concurrency,
        "pool_mode": "system_managed",
        "pool_members": members,
        "pool_routing_key": compute_pool_routing_key(members),
    }
    if settings.llm_shared_pool_concurrency:
        config["shared_pool_concurrency"] = settings.llm_shared_pool_concurrency
    return config


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
    def _system_pool_config() -> Dict[str, Any]:
        return _build_system_managed_llm_config(advanced_config)

    # Priority 0: Default: use author's API if explicitly requested
    if advanced_config.use_author_api:
        logger.info("Using author's API configuration (use_author_api=True)")
        return _system_pool_config() or settings.get_llm_config()
    
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
            "timeout": settings.llm_timeout,
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
                "timeout": settings.llm_timeout,
            }
        else:
            logger.warning(f"No API key found in system settings for user {user_id}")

    # Final fallback to author's API
    logger.warning("No custom API configuration available, falling back to author's API")
    return _system_pool_config() or settings.get_llm_config()


async def build_llm_config_async(advanced_config: AdvancedConfig, user_id: str = None) -> Dict[str, Any]:
    """
    Async-safe variant of build_llm_config for async request paths.
    """
    def _system_pool_config() -> Dict[str, Any]:
        return _build_system_managed_llm_config(advanced_config)

    if advanced_config.use_author_api:
        logger.info("Using author's API configuration (use_author_api=True)")
        return _system_pool_config() or settings.get_llm_config()

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
    return _system_pool_config() or settings.get_llm_config()

def compute_config_hash(
    arxiv_id: Optional[str],
    source_language: str,
    target_language: str,
    translation_mode: str,
    compile_strategy: str,
    source_path: Optional[str] = None,
    formatting: Optional[Any] = None,
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
        "translation_core_mode": ORIGIN_CLI_PARITY_MODE,
        "content_key": content_key,
        "source_language": source_language,
        "target_language": target_language,
        "translation_mode": translation_mode,
        "compile_strategy": compile_strategy,
        "formatting": _normalize_formatting_for_hash(formatting),
    }
    return hashlib.md5(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()


def _normalize_formatting_for_hash(formatting: Optional[Any]) -> Optional[Dict[str, Any]]:
    if formatting is None:
        return None

    if isinstance(formatting, BaseModel):
        formatting_payload = formatting.model_dump(exclude_none=True)
    elif isinstance(formatting, dict):
        formatting_payload = {
            key: value for key, value in formatting.items()
            if value is not None
        }
    else:
        formatting_payload = {
            key: value for key, value in vars(formatting).items()
            if value is not None
        }

    return formatting_payload or None


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
        repository = get_translation_task_repository()
        record = await run_db_blocking(
            lambda: repository.find_reusable_completed_task(
                config_hash,
                exclude_task_id=task_id,
            )
        )
        if not record:
            return None

        reusable_task_id = str(record.get("task_id") or "").strip()
        output_path_value = str(record.get("output_path") or "").strip()

        if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos" and output_path_value:
            logger.info(f"Found reusable object-storage output: {output_path_value}")
            return output_path_value

        candidate_paths = []
        if output_path_value:
            candidate_paths.append(Path(output_path_value))
        if reusable_task_id:
            candidate_paths.append(settings.outputs_dir / reusable_task_id)

        checked_paths = []
        for candidate_path in candidate_paths:
            normalized_candidate = str(candidate_path)
            if normalized_candidate in checked_paths:
                continue
            checked_paths.append(normalized_candidate)
            if candidate_path.exists():
                logger.info(f"Found reusable output: {candidate_path}")
                return str(candidate_path)

        if checked_paths:
            logger.warning(
                "Reusable output referenced in local DB but no local candidate exists: %s",
                checked_paths,
            )

        return None
    except Exception as e:
        logger.warning(f"Error searching for reusable output: {e}")
        return None


async def persist_task_config_hash(task_id: str, config_hash: str) -> bool:
    """Persist config_hash for an already-created authenticated task row."""
    try:
        repository = get_translation_task_repository()
        updated = await run_db_blocking(
            lambda: repository.update_task(task_id, {"config_hash": config_hash})
        )
        if updated:
            logger.info(f"Stored config_hash in local database for task {task_id}")
        return bool(updated)
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
    if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
        dest = Path(settings.outputs_dir) / task_id
        task_artifact_storage.materialize_task_directory(
            source_output,
            destination=dest,
            force=True,
        )
        return task_artifact_storage.persist_task_output_directory(
            task_id=task_id,
            local_output_dir=dest,
            delete_local=True,
        )

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
    advanced_config = normalize_origin_cli_parity_advanced_config(advanced_config)
    logger.info(f"Advanced config: mode={advanced_config.translation_mode}, "
                f"compile={advanced_config.compile_strategy}, "
                f"user_id={user_id}")
    attempt_id: Optional[int] = None

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

        if hasattr(task_manager, "begin_task_attempt"):
            attempt_id = task_manager.begin_task_attempt(task_id)
        else:
            attempt_id = int((task or {}).get("attempt_id") or 1)
        
        raw_source_path = task.get("source_path")
        arxiv_id = task.get("arxiv_id")

        # Helper: re-download arXiv source if path is missing or path doesn't exist
        async def _ensure_source_path() -> Path:
            nonlocal raw_source_path
            if raw_source_path:
                p = Path(raw_source_path)
                if p.exists():
                    return p
                if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
                    hydrated_path = task_artifact_storage.resolve_local_task_path(raw_source_path)
                    try:
                        return task_artifact_storage.materialize_task_directory(
                            raw_source_path,
                            destination=hydrated_path,
                            force=True,
                        )
                    except FileNotFoundError:
                        logger.warning(f"Stored source path not found in object storage: {raw_source_path}")
                logger.warning(f"Source path on disk not found: {p}")
            else:
                logger.warning(f"Task {task_id} has no source_path recorded")

            if arxiv_id and task.get("source_type") == "arxiv":
                logger.info(f"Re-downloading arXiv source for {arxiv_id}...")
                task_manager.update_task(
                    task_id=task_id,
                    message=f"源文件缺失，正在重新下载 arXiv {arxiv_id}...",
                    user_id=user_id,
                    expected_attempt_id=attempt_id
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
                stored_source_path = str(new_path)
                if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
                    stored_source_path = task_artifact_storage.persist_task_directory(
                        new_path,
                        stored_path=task_artifact_storage.normalize_stored_task_path(new_path),
                        delete_local=False,
                    )
                task_manager.update_task(
                    task_id=task_id,
                    source_path=stored_source_path,
                    source_available=True,
                    user_id=user_id,
                    expected_attempt_id=attempt_id
                )
                logger.info(f"Re-download succeeded, source_path updated to: {stored_source_path}")
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
        durable_output_path = str(output_dir)
        
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PROCESSING.value,
            progress=0,
            message="Checking for reusable output...",
            detail_code="task_waiting",
            output_path=str(output_dir),  # eagerly written for lazy reconciliation
            user_id=user_id,
            expected_attempt_id=attempt_id
        )
        
        # 计算配置签名
        config_hash = compute_config_hash(
            arxiv_id=task.get("arxiv_id"),
            source_language=source_language,
            target_language=target_language,
            translation_mode=advanced_config.translation_mode,
            compile_strategy=advanced_config.compile_strategy,
            source_path=str(source_path),
            formatting=advanced_config.formatting,
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
                user_id=user_id,
                expected_attempt_id=attempt_id
            )
            logger.info(f"Task {task_id} completed via output reuse")
            if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
                clear_cached_runtime_artifacts(task_id, [source_path])
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
            user_id=user_id,
            expected_attempt_id=attempt_id
        )
        
        # Create progress callback
        if hasattr(task_manager, "create_progress_callback"):
            try:
                progress_callback = task_manager.create_progress_callback(
                    task_id,
                    attempt_id=attempt_id,
                )
            except TypeError:
                progress_callback = task_manager.create_progress_callback(task_id)
        else:
            progress_callback = None
        
        # Build LLM config from advanced settings (with user's stored API key if available)
        llm_config = await build_llm_config_async(advanced_config, user_id)
        
        # Build config dict for CoordinatorAgent with all advanced settings
        task_llm_cap = CLI_PARITY_TASK_LLM_MAX_CONCURRENT_REQUESTS
        community_production_translation = bool(getattr(advanced_config, "community_production_translation", False))
        if community_production_translation:
            task_llm_cap = max(1, int(settings.community_translation_llm_max_concurrent_requests or 10))

        task_llm_max_concurrent_requests = resolve_task_llm_max_concurrent_requests(
            default=settings.llm_max_concurrent_requests,
            cap=task_llm_cap,
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
            "sys_name": "PaperX",
            "target_language": target_language,
            "source_language": source_language,
            "translation_core_mode": getattr(advanced_config, "translation_core_mode", None),
            "mode": TRANSLATION_MODE_MAP.get(advanced_config.translation_mode, 0),
            "translation_mode": advanced_config.translation_mode,
            "latex_engine": advanced_config.compile_strategy,
            "use_verification_agent": False,
            "generate_terminology": advanced_config.generate_terminology_table,
            "generate_terminology_table": advanced_config.generate_terminology_table,
            "enable_rag_terminology": getattr(advanced_config, "enable_rag_terminology", False),
            "rag_terminology_domain": getattr(advanced_config, "rag_terminology_domain", None),
            "update_term": False,
            "user_term": "",
            "category": category_map,
            "formatting": formatting,
            "enable_parser_env_llm_judgment": False if community_production_translation else True,
            "enable_legacy_translation_core": True if community_production_translation else False,
            "model_context_tokens": settings.model_context_tokens or CLI_PARITY_MODEL_CONTEXT_TOKENS,
            "prompt_reserve_tokens": settings.prompt_reserve_tokens or CLI_PARITY_PROMPT_RESERVE_TOKENS,
            "llm_max_concurrent_requests": task_llm_max_concurrent_requests,
            "task_id": task_id,
            "output_dir": str(output_dir),
            "tex_sources_dir": str(settings.uploads_dir),
            "llm_config": llm_config
        }
        agent_config = normalize_origin_cli_parity_agent_config(agent_config)

        logger.info(f"Agent config: mode={agent_config['mode']}, "
                    f"engine={agent_config['latex_engine']}, "
                    f"verify={agent_config['use_verification_agent']}, "
                    f"llm_max_concurrent_requests={agent_config['llm_max_concurrent_requests']}, "
                    f"translation_core_mode={agent_config['translation_core_mode']}")

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

        if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos" and output_dir.exists():
            durable_output_path = task_artifact_storage.persist_task_output_directory(
                task_id=task_id,
                local_output_dir=output_dir,
                delete_local=True,
            )

        if workflow_status == "structure_invalid":
            error_text = error_summary or "LaTeX structure guard rejected bundle before compilation"
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.STRUCTURE_INVALID.value,
                progress=100,
                message=error_text,
                error=error_text,
                warnings=warning_summary,
                output_path=durable_output_path,
                failure_reason_code=failure_reason_code,
                failure_class=failure_class or "structural",
                guard_phase=guard_phase,
                replay_bundle_ref=replay_bundle_ref,
                user_id=user_id,
                expected_attempt_id=attempt_id,
            )
            try:
                from backend.app.services import paper_service

                await paper_service.mark_paper_translation_failed_by_task(task_id)
            except Exception:
                logger.warning(
                    "Failed to sync paper status to failed for structure-invalid task %s",
                    task_id,
                    exc_info=True,
                )
            if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
                clear_cached_runtime_artifacts(task_id, [source_path])
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
                output_path=durable_output_path,
                failure_reason_code=failure_reason_code,
                failure_class=failure_class,
                guard_phase=guard_phase,
                replay_bundle_ref=replay_bundle_ref,
                user_id=user_id,
                expected_attempt_id=attempt_id
            )
            try:
                from backend.app.services import paper_service

                await paper_service.mark_paper_translation_failed_by_task(task_id)
            except Exception:
                logger.warning(
                    "Failed to sync paper status to failed for compilation-failed task %s",
                    task_id,
                    exc_info=True,
                )
            if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
                clear_cached_runtime_artifacts(task_id, [source_path])
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
                output_path=durable_output_path,
                user_id=user_id,
                expected_attempt_id=attempt_id
            )
            logger.info(f"Translation completed with compilation warnings: {task_id}")
        else:
            task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.COMPLETED.value,
                progress=100,
                message="Translation completed successfully",
                detail_code="compile_complete",
                output_path=durable_output_path,
                user_id=user_id,
                expected_attempt_id=attempt_id
            )
            logger.info(f"Translation completed: {task_id}")
        if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
            clear_cached_runtime_artifacts(task_id, [source_path])
    
    except asyncio.CancelledError:
        is_user_cancelled = task_manager.is_cancelled(task_id)
        if is_user_cancelled:
            logger.info("Translation task %s cancelled by user request", task_id)
            raise

        if not is_runtime_shutting_down():
            logger.warning(
                "Translation task %s cancelled unexpectedly during runtime; will rely on queue retry.",
                task_id,
            )
            raise

        logger.warning(
            "Translation task %s cancelled by runtime/shutdown; marking failed state",
            task_id,
        )
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            message="Task interrupted by backend restart",
            error="Task interrupted by backend restart",
            detail_code="task_interrupted_restart",
            progress=100,
            user_id=user_id,
            expected_attempt_id=attempt_id,
        )
        try:
            from backend.app.services import paper_service

            await paper_service.mark_paper_translation_failed_by_task(task_id)
        except Exception:
            logger.warning("Failed to sync paper status to failed for interrupted task %s", task_id, exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Translation error for task {task_id}: {e}", exc_info=True)
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error=str(e),
            message=f"Translation error: {str(e)}",
            user_id=user_id,
            expected_attempt_id=attempt_id
        )
        try:
            from backend.app.services import paper_service

            await paper_service.mark_paper_translation_failed_by_task(task_id)
        except Exception:
            logger.warning("Failed to sync paper status to failed for errored task %s", task_id, exc_info=True)


async def _start_translation_for_task(
    task_id: str,
    request: TranslateRequest,
    credentials: Optional[HTTPAuthorizationCredentials],
    current_user: Optional[dict[str, Any]],
    *,
    reserve_daily_quota: bool = True,
) -> TranslateResponse:
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
    effective_advanced_config = normalize_origin_cli_parity_advanced_config(request.advanced_config)

    user_id = resolve_current_user_id(current_user, credentials)
    if user_id:
        logger.info(f"Authenticated user: {user_id}")

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
    tq = get_task_queue()
    if user_id and tq:
        user_active = tq.get_user_active_count(user_id)
        if user_active >= settings.max_user_active_tasks:
            raise HTTPException(
                status_code=429,
                detail=f"Too many active tasks. You have {user_active}/{settings.max_user_active_tasks} active tasks. Please wait for existing tasks to complete."
            )

    quota_service: Optional[TranslationQuotaService] = None
    quota_reserved = False
    user_roles = current_user.get("roles") if current_user else None
    if user_id and reserve_daily_quota:
        quota_service = get_translation_quota_service()
        try:
            quota_service.reserve_latex_translation(user_id=user_id, requested_count=1, roles=user_roles)
            quota_reserved = True
        except DailyQuotaExceededError as exc:
            raise HTTPException(status_code=429, detail=_quota_exceeded_detail(exc)) from exc

    config_hash = compute_config_hash(
        arxiv_id=task.get("arxiv_id"),
        source_language=request.source_language,
        target_language=request.target_language,
        translation_mode=effective_advanced_config.translation_mode,
        compile_strategy=effective_advanced_config.compile_strategy,
        source_path=task.get("source_path"),
        formatting=effective_advanced_config.formatting,
    )
    logger.info(f"Computed config_hash for task {task_id}: {config_hash}")

    # Keep the final config snapshot in memory before delayed persistence so
    # both the initial insert and any retry can include the same metadata.
    task_manager.update_task(
        task_id=task_id,
        source_language=request.source_language,
        target_language=request.target_language,
        advanced_config=effective_advanced_config.model_dump(),
        config_hash=config_hash,
    )

    # ✅ Persist to database (delayed creation)
    persisted = task_manager.persist_task_if_needed(task_id)
    if not persisted:
        logger.warning(f"Failed to persist task {task_id}, but continuing with translation")
    elif user_id:
        try:
            await persist_task_config_hash(task_id, config_hash)
        except Exception:
            if quota_reserved and quota_service is not None:
                try:
                    quota_service.release_latex_translation(user_id=user_id, count=1, roles=user_roles)
                except Exception:
                    logger.warning("Failed to release daily quota after config persistence failure", exc_info=True)
            raise

    try:
        # Enqueue translation via TaskQueue
        if tq:
            # Compute token_hash for per-bucket routing isolation
            _llm_cfg = await build_llm_config_async(effective_advanced_config, user_id)
            pool_routing_key = str(_llm_cfg.get("pool_routing_key") or "").strip()
            if pool_routing_key:
                token_hash = hashlib.md5(pool_routing_key.encode()).hexdigest()
            else:
                _api_key = (_llm_cfg.get("api_key") or "").encode()
                token_hash = hashlib.md5(_api_key).hexdigest()

            async def translation_factory():
                await run_translation(
                    task_id=task_id,
                    target_language=request.target_language,
                    source_language=request.source_language,
                    advanced_config=effective_advanced_config,
                    user_id=user_id
                )

            llm_capacity = resolve_llm_task_capacity(_llm_cfg)
            await tq.enqueue(
                task_id,
                translation_factory,
                user_id,
                token_hash,
                llm_capacity=llm_capacity,
            )
            logger.info(
                f"Task {task_id} enqueued via TaskQueue "
                f"(token_hash={token_hash[:8]}..., llm_capacity={llm_capacity})"
            )
        else:
            # Fallback: direct asyncio.create_task (TaskQueue not initialized)
            logger.warning("TaskQueue not initialized, falling back to direct asyncio.create_task")
            asyncio.create_task(
                run_translation(
                    task_id=task_id,
                    target_language=request.target_language,
                    source_language=request.source_language,
                    advanced_config=effective_advanced_config,
                    user_id=user_id
                )
            )
    except Exception:
        if quota_reserved and quota_service is not None and user_id:
            try:
                quota_service.release_latex_translation(user_id=user_id, count=1, roles=user_roles)
            except Exception:
                logger.warning("Failed to release daily quota for pre-acceptance failure", exc_info=True)
        raise

    return TranslateResponse(
        task_id=task_id,
        status="queued",
        message="Translation queued successfully"
    )


@router.post("/translate/{task_id}", response_model=TranslateResponse)
async def start_translation(
    task_id: str,
    request: TranslateRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    current_user: Optional[dict[str, Any]] = Depends(optional_current_user),
):
    return await _start_translation_for_task(
        task_id=task_id,
        request=request,
        credentials=credentials,
        current_user=current_user,
        reserve_daily_quota=True,
    )


@router.get("/queue/status")
async def get_queue_status(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    current_user: Optional[dict[str, Any]] = Depends(optional_current_user),
):
    """
    Get current task queue status.

    Returns:
        Queue status including active count, queue size, and max concurrent
    """
    tq = get_task_queue()

    if not tq:
        return {
            "active_count": 0,
            "queue_size": 0,
            "max_concurrent": settings.max_concurrent_translations,
            "total_pending": 0,
            "interactive_active": 0,
            "interactive_waiting": 0,
            "backfill_active": 0,
            "backfill_waiting": 0,
            "borrowed_slots": 0,
            "user_quota_used": 0
        }

    status = tq.get_status()

    user_id = resolve_current_user_id(current_user, credentials)
    status["user_quota_used"] = tq.get_user_active_count(user_id) if user_id else 0
    status["user_quota_max"] = settings.max_user_active_tasks
    return status


@router.post("/batch-translate", response_model=BatchTranslateResponse)
async def batch_translate(
    request: BatchTranslateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
    current_user: dict[str, Any] = Depends(require_current_user),
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
    user_id = resolve_current_user_id(current_user, credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required for batch translation")
    user_roles = current_user.get("roles") if isinstance(current_user, dict) else None
    effective_advanced_config = normalize_origin_cli_parity_advanced_config(request.advanced_config)

    # Validate arxiv_ids count
    arxiv_ids = request.arxiv_ids
    if not arxiv_ids:
        raise HTTPException(status_code=400, detail="No arXiv IDs provided")
    if len(arxiv_ids) > 9:
        raise HTTPException(
            status_code=400,
            detail=f"Batch limit exceeded: maximum 9 arXiv IDs per request, got {len(arxiv_ids)}"
        )

    normalized_arxiv_ids: list[str] = []
    invalid_arxiv_ids: list[str] = []
    for raw_id in arxiv_ids:
        normalized = extract_arxiv_ids([raw_id])
        if not normalized:
            invalid_arxiv_ids.append(str(raw_id))
            continue
        normalized_arxiv_ids.append(normalized[0])
    if invalid_arxiv_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid arXiv ID format: {', '.join(invalid_arxiv_ids)}",
        )

    # Check user quota
    tq = get_task_queue()
    if tq:
        user_active = tq.get_user_active_count(user_id)
        remaining = settings.max_user_active_tasks - user_active
        if remaining <= 0:
            raise HTTPException(
                status_code=429,
                detail=f"Quota exceeded: you have {user_active}/{settings.max_user_active_tasks} active tasks. Please wait for existing tasks to complete."
            )
        if len(normalized_arxiv_ids) > remaining:
            raise HTTPException(
                status_code=429,
                detail=f"Quota exceeded: you can submit at most {remaining} more tasks (currently {user_active}/{settings.max_user_active_tasks} active)."
            )

    quota_service = get_translation_quota_service()
    reserved_count = len(normalized_arxiv_ids)
    try:
        quota_service.reserve_latex_translation(
            user_id=user_id,
            requested_count=reserved_count,
            roles=user_roles,
        )
    except DailyQuotaExceededError as exc:
        raise HTTPException(status_code=429, detail=_quota_exceeded_detail(exc)) from exc

    import uuid
    batch_id = str(uuid.uuid4())
    task_ids = []
    errors = []
    accepted_count = 0

    for arxiv_id in normalized_arxiv_ids:
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
                translation_mode=effective_advanced_config.translation_mode,
                compile_strategy=effective_advanced_config.compile_strategy,
                formatting=effective_advanced_config.formatting,
            )
            task_manager.update_task(
                task_id=task_id,
                source_language=request.source_language,
                target_language=request.target_language,
                advanced_config=effective_advanced_config.model_dump(),
                config_hash=config_hash,
            )

            # ✅ Persist to DB immediately (synchronous fast attempt).
            # If the local database is unreachable, silently retry in background (2x, 5s apart).
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
            _batch_llm_cfg = await build_llm_config_async(effective_advanced_config, user_id)
            _pool_routing_key = str(_batch_llm_cfg.get("pool_routing_key") or "").strip()
            if _pool_routing_key:
                _batch_token_hash = hashlib.md5(_pool_routing_key.encode()).hexdigest()
            else:
                _batch_token_hash = hashlib.md5(
                    (_batch_llm_cfg.get("api_key") or "").encode()
                ).hexdigest()
            _batch_llm_capacity = resolve_llm_task_capacity(_batch_llm_cfg)
            asyncio.create_task(
                _download_and_enqueue(
                    task_id=task_id,
                    arxiv_id=arxiv_id,
                    user_id=user_id,
                    source_language=request.source_language,
                    target_language=request.target_language,
                    advanced_config=effective_advanced_config,
                    tq=tq,
                    token_hash=_batch_token_hash,
                    llm_capacity=_batch_llm_capacity,
                )
            )
            accepted_count += 1
            logger.info(f"[BatchTranslate] Created task {task_id} for arxiv_id={arxiv_id}, download started in background")

        except Exception as e:
            logger.error(f"[BatchTranslate] Failed to process arxiv_id={arxiv_id}: {e}")
            errors.append(f"{arxiv_id}: {str(e)}")

    if not task_ids:
        quota_service.release_latex_translation(user_id=user_id, count=reserved_count, roles=user_roles)
        raise HTTPException(
            status_code=500,
            detail=f"All batch tasks failed: {'; '.join(errors)}"
        )

    unaccepted_count = max(reserved_count - accepted_count, 0)
    if unaccepted_count:
        quota_service.release_latex_translation(user_id=user_id, count=unaccepted_count, roles=user_roles)

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
    llm_capacity: int = 1,
    lane: str = "interactive",
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
    advanced_config = normalize_origin_cli_parity_advanced_config(advanced_config)
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
        stored_source_path = source_path
        if str(getattr(settings, "storage_backend_mode", "")).strip().lower() == "cos":
            stored_source_path = task_artifact_storage.persist_task_directory(
                Path(source_path),
                stored_path=task_artifact_storage.normalize_stored_task_path(source_path),
                delete_local=True,
            )

        # Step 3: Mark source as available
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PENDING.value,
            progress=100,
            message=f"arXiv 论文 {arxiv_id} 下载完成，等待翻译",
            detail_code="download_source_complete",
            source_path=stored_source_path,
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
            await tq.enqueue(task_id, factory, user_id, token_hash, lane=lane, llm_capacity=llm_capacity)
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
