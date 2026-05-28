"""用户设置 API 路由，基于本地用户设置持久化。"""

from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.core.auth import require_current_user
from backend.app.core.config import get_default_translation_model
from backend.app.core.encryption import encrypt_api_key
from backend.app.policies import authorize
from backend.app.repositories import USER_SETTINGS_DEFAULTS, UserSettingsRepository
from backend.app.utils.async_blocking import run_db_blocking

router = APIRouter()


class UserSettingsResponse(BaseModel):
    """用户设置响应模型"""

    default_source_language: str = "en"
    default_target_language: str = "zh"
    translation_mode: str = "full"
    compile_strategy: str = "auto"
    translation_model: Optional[str] = get_default_translation_model()
    generate_glossary: bool = True
    use_author_api: bool = True
    custom_base_url: Optional[str] = None
    has_custom_api_key: bool = False
    default_formatting: Optional[Dict[str, Any]] = None


class UserSettingsUpdate(BaseModel):
    """用户设置更新请求模型"""

    default_source_language: Optional[str] = None
    default_target_language: Optional[str] = None
    translation_mode: Optional[str] = None
    compile_strategy: Optional[str] = None
    translation_model: Optional[str] = None
    generate_glossary: Optional[bool] = None
    use_author_api: Optional[bool] = None
    custom_base_url: Optional[str] = None
    custom_api_key: Optional[str] = None
    default_formatting: Optional[Dict[str, Any]] = None


SYSTEM_DEFAULTS = dict(USER_SETTINGS_DEFAULTS)


def get_user_settings_repository() -> UserSettingsRepository:
    """获取用户设置仓库实例"""
    return UserSettingsRepository()


def _resolve_user_settings_repository() -> UserSettingsRepository:
    """解析用户设置仓库（用于 FastAPI 依赖注入）"""
    return get_user_settings_repository()


def _build_response(settings: dict[str, Any]) -> UserSettingsResponse:
    """将数据库设置字典转换为 API 响应模型"""
    return UserSettingsResponse(
        default_source_language=settings.get("default_source_language", "en"),
        default_target_language=settings.get("default_target_language", "zh"),
        translation_mode=settings.get("translation_mode", "full"),
        compile_strategy=settings.get("compile_strategy", "auto"),
        translation_model=settings.get("translation_model"),
        generate_glossary=settings.get("generate_glossary", True),
        use_author_api=settings.get("use_author_api", True),
        custom_base_url=settings.get("custom_base_url"),
        has_custom_api_key=bool(settings.get("custom_api_key_encrypted")),
        default_formatting=settings.get("default_formatting"),
    )


def _ensure_settings_authorized(current_user: Dict[str, Any], action: str) -> None:
    """校验用户对设置的操作权限，未授权时抛出 403"""
    decision = authorize(current_user, "settings", action)
    if decision.allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=decision.reason,
    )


@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: Dict[str, Any] = Depends(require_current_user),
    repository: UserSettingsRepository = Depends(_resolve_user_settings_repository),
):
    """获取当前用户的已保存设置或项目默认值"""
    _ensure_settings_authorized(current_user, "read")

    try:
        settings = await run_db_blocking(
            lambda: repository.get_user_settings(current_user["id"])
        )
        return _build_response(settings or SYSTEM_DEFAULTS)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get settings: {str(e)}",
        ) from e


@router.put("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    update: UserSettingsUpdate,
    current_user: Dict[str, Any] = Depends(require_current_user),
    repository: UserSettingsRepository = Depends(_resolve_user_settings_repository),
):
    """更新当前用户的已保存设置"""
    _ensure_settings_authorized(current_user, "update")

    try:
        update_data: dict[str, Any] = {}
        provided_fields = getattr(update, "model_fields_set", set())

        if update.default_source_language is not None:
            update_data["default_source_language"] = update.default_source_language
        if update.default_target_language is not None:
            update_data["default_target_language"] = update.default_target_language
        if update.translation_mode is not None:
            if update.translation_mode not in ("full", "quick_scan"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="translation_mode must be 'full' or 'quick_scan'",
                )
            update_data["translation_mode"] = update.translation_mode
        if update.compile_strategy is not None:
            if update.compile_strategy not in ("auto", "pdflatex", "xelatex", "lualatex"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="compile_strategy must be 'auto', 'pdflatex', 'xelatex', or 'lualatex'",
                )
            update_data["compile_strategy"] = update.compile_strategy
        if update.translation_model is not None or "translation_model" in provided_fields:
            update_data["translation_model"] = update.translation_model
        if update.generate_glossary is not None:
            update_data["generate_glossary"] = update.generate_glossary
        if update.use_author_api is not None:
            update_data["use_author_api"] = update.use_author_api
        if update.custom_base_url is not None or "custom_base_url" in provided_fields:
            update_data["custom_base_url"] = update.custom_base_url
        if update.custom_api_key is not None or "custom_api_key" in provided_fields:
            update_data["custom_api_key_encrypted"] = encrypt_api_key(update.custom_api_key)
        if update.default_formatting is not None:
            update_data["default_formatting"] = update.default_formatting
        elif "default_formatting" in provided_fields:
            update_data["default_formatting"] = None

        if not update_data:
            return await get_user_settings(current_user, repository)

        saved_settings = await run_db_blocking(
            lambda: repository.upsert_user_settings(current_user["id"], update_data)
        )
        return _build_response(saved_settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}",
        ) from e
