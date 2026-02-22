"""
Settings API Routes - 纯 RLS 模式

核心原则：
- 后端不验证 token，不解析 user
- token 透传给 Supabase client
- RLS 使用 auth.uid() 自动控制权限
- 这是 Supabase 官方最终推荐形态
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from backend.app.core.auth import get_supabase_client_from_request
from backend.app.core.encryption import encrypt_api_key

router = APIRouter()


class UserSettingsResponse(BaseModel):
    """Response model for user settings"""
    default_source_language: str = "en"
    default_target_language: str = "zh"
    translation_mode: str = "full"
    compile_strategy: str = "auto"
    translation_model: Optional[str] = None
    enable_verification: bool = True
    generate_glossary: bool = True
    use_author_api: bool = True
    custom_base_url: Optional[str] = None
    has_custom_api_key: bool = False
    default_formatting: Optional[Dict[str, Any]] = None  # FormattingConfig as dict


class UserSettingsUpdate(BaseModel):
    """Update model for user settings"""
    default_source_language: Optional[str] = None
    default_target_language: Optional[str] = None
    translation_mode: Optional[str] = None
    compile_strategy: Optional[str] = None
    translation_model: Optional[str] = None
    enable_verification: Optional[bool] = None
    generate_glossary: Optional[bool] = None
    use_author_api: Optional[bool] = None
    custom_base_url: Optional[str] = None
    custom_api_key: Optional[str] = None  # Write-only, not returned in response
    default_formatting: Optional[Dict[str, Any]] = None  # FormattingConfig as dict


# System default settings
SYSTEM_DEFAULTS = {
    "default_source_language": "en",
    "default_target_language": "zh",
    "translation_mode": "full",
    "compile_strategy": "auto",
    "translation_model": None,
    "enable_verification": True,
    "generate_glossary": True,
    "use_author_api": True,
    "custom_base_url": None,
    "custom_api_key_encrypted": None,
    "default_formatting": None,
}


def _build_response(settings: dict) -> UserSettingsResponse:
    """Helper to build response from settings dict."""
    return UserSettingsResponse(
        default_source_language=settings.get("default_source_language", "en"),
        default_target_language=settings.get("default_target_language", "zh"),
        translation_mode=settings.get("translation_mode", "full"),
        compile_strategy=settings.get("compile_strategy", "auto"),
        translation_model=settings.get("translation_model"),
        enable_verification=settings.get("enable_verification", True),
        generate_glossary=settings.get("generate_glossary", True),
        use_author_api=settings.get("use_author_api", True),
        custom_base_url=settings.get("custom_base_url"),
        has_custom_api_key=bool(settings.get("custom_api_key_encrypted")),
        default_formatting=settings.get("default_formatting"),
    )


@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    supabase: Optional[Client] = Depends(get_supabase_client_from_request)
):
    """
    Get current user's settings.
    
    纯 RLS 模式：
    - 后端不需要 user_id
    - RLS policy: "auth.uid() = user_id" 自动过滤
    - 如果 token 无效，RLS 返回空结果
    """
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # RLS 自动过滤：只返回当前用户的 settings
        result = supabase.table("user_settings").select("*").execute()
        
        if result.data and len(result.data) > 0:
            return _build_response(result.data[0])
        
        # 用户没有 settings 记录 - 返回默认值
        # 注意：INSERT 需要 user_id，但我们无法获取（纯 RLS 模式）
        # 所以首次访问返回默认值，首次更新时创建记录
        return UserSettingsResponse()
        
    except Exception as e:
        # RLS 拒绝访问时可能抛出异常
        if "JWT" in str(e) or "token" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get settings: {str(e)}"
        )


@router.put("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    update: UserSettingsUpdate,
    supabase: Optional[Client] = Depends(get_supabase_client_from_request)
):
    """
    Update current user's settings.
    
    纯 RLS 模式：
    - 后端不需要 user_id
    - RLS policy 自动确保只能更新自己的记录
    """
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Build update dict
        update_data = {}
        
        if update.default_source_language is not None:
            update_data["default_source_language"] = update.default_source_language
        if update.default_target_language is not None:
            update_data["default_target_language"] = update.default_target_language
        if update.translation_mode is not None:
            if update.translation_mode not in ("full", "quick_scan"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="translation_mode must be 'full' or 'quick_scan'"
                )
            update_data["translation_mode"] = update.translation_mode
        if update.compile_strategy is not None:
            if update.compile_strategy not in ("auto", "pdflatex", "xelatex", "lualatex"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="compile_strategy must be 'auto', 'pdflatex', 'xelatex', or 'lualatex'"
                )
            update_data["compile_strategy"] = update.compile_strategy
        if update.translation_model is not None:
            update_data["translation_model"] = update.translation_model
        if update.enable_verification is not None:
            update_data["enable_verification"] = update.enable_verification
        if update.generate_glossary is not None:
            update_data["generate_glossary"] = update.generate_glossary
        if update.use_author_api is not None:
            update_data["use_author_api"] = update.use_author_api
        if update.custom_base_url is not None:
            update_data["custom_base_url"] = update.custom_base_url
        if update.custom_api_key is not None:
            update_data["custom_api_key_encrypted"] = encrypt_api_key(update.custom_api_key)
        if update.default_formatting is not None:
            update_data["default_formatting"] = update.default_formatting
        elif "default_formatting" in (update.model_fields_set if hasattr(update, 'model_fields_set') else {}):
            # Explicit None means clear the formatting
            update_data["default_formatting"] = None
        
        if not update_data:
            return await get_user_settings(supabase)
        
        # 尝试更新（RLS 自动过滤到当前用户）
        result = supabase.table("user_settings").select("id").execute()
        
        if result.data and len(result.data) > 0:
            # 更新现有记录
            supabase.table("user_settings").update(update_data).eq("id", result.data[0]["id"]).execute()
        else:
            # 创建新记录 - 使用 RLS 自动填充 user_id
            # 注意：需要数据库触发器或 default 值设置 user_id = auth.uid()
            insert_data = {**SYSTEM_DEFAULTS, **update_data}
            supabase.table("user_settings").insert(insert_data).execute()
        
        return await get_user_settings(supabase)
        
    except HTTPException:
        raise
    except Exception as e:
        if "JWT" in str(e) or "token" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )
