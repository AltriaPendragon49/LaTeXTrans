"""
Authentication Module - 纯 RLS 模式

核心原则：
- 后端不验证 token
- 后端不解析 user
- 所有权限完全交给 RLS
- 这是 Supabase 官方最终推荐形态

前端发送 access_token → 后端透传给 Supabase client → RLS 自动控制权限
"""

import logging
import secrets
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client

from backend.app.core.config import get_settings

# Allow missing Authorization header (guest mode)
security = HTTPBearer(auto_error=False)


def create_supabase_client_with_token(access_token: Optional[str] = None) -> Optional[Client]:
    """
    创建 Supabase 客户端。
    
    如果提供 access_token，则创建用户上下文客户端（受 RLS 约束）。
    如果不提供，返回 None（访客模式）。
    
    后端不验证 token - Supabase 和 RLS 会处理无效 token。
    
    Args:
        access_token: 用户的 Supabase access_token（可选）
        
    Returns:
        配置了用户认证的 Supabase Client，或 None
    """
    settings = get_settings()
    
    if not settings.supabase_url or not settings.supabase_anon_key:
        logging.warning("[Auth] Supabase not configured")
        return None
    
    if access_token is None:
        return None
    
    # 使用 anon key 创建客户端
    client = create_client(
        settings.supabase_url,
        settings.supabase_anon_key
    )
    try:
        setattr(client, "_access_token", access_token)
    except Exception:
        pass
    
    # 设置用户的 access_token
    # RLS 将使用 auth.uid() 识别用户
    # 后端不验证 token - 如果无效，RLS 会拒绝访问
    try:
        client.auth.set_session(access_token, "")
    except Exception as e:
        logging.debug(f"[Auth] set_session failed: {e}")
        # 继续使用客户端，让 RLS 处理
    
    return client


def clone_supabase_client_with_same_auth(client: Optional[Client]) -> Optional[Client]:
    """Create a short-lived authenticated clone from an existing user-scoped client."""
    if client is None:
        return None

    access_token = getattr(client, "_access_token", None)
    if not access_token:
        return None

    return create_supabase_client_with_token(access_token)


async def get_supabase_client_from_request(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Client]:
    """
    从请求中获取配置了用户认证的 Supabase 客户端。
    
    后端不验证 token，不解析 user，不调用 auth.get_user()。
    直接将 token 透传给 Supabase client，RLS 控制一切。
    
    Returns:
        Supabase Client（认证用户）或 None（访客）
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    
    # 快速检查 JWT 格式
    if token.count(".") != 2:
        logging.debug("[Auth] Non-JWT token, treating as guest")
        return None
    
    return create_supabase_client_with_token(token)


def _extract_admin_roles(metadata: Any) -> set[str]:
    if not isinstance(metadata, dict):
        return set()

    candidates: list[str] = []
    role = metadata.get("role")
    if isinstance(role, str):
        candidates.append(role)

    roles = metadata.get("roles")
    if isinstance(roles, (list, tuple, set)):
        candidates.extend(str(item) for item in roles if item is not None)
    elif isinstance(roles, str):
        candidates.extend(part.strip() for part in roles.split(","))

    return {candidate.strip().lower() for candidate in candidates if candidate and candidate.strip()}


async def require_admin_request(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict[str, Any]:
    """
    Guard administrative endpoints.

    Allows either:
    - the exact backend service-role key as a bearer token; or
    - a verified Supabase user token carrying an admin role in app/user metadata.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    settings = get_settings()

    if settings.supabase_service_role_key and secrets.compare_digest(
        token,
        settings.supabase_service_role_key,
    ):
        return {"auth_type": "service_role"}

    if token.count(".") != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    client = create_supabase_client_with_token(token)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        response = client.auth.get_user(token)
    except Exception as exc:
        logging.debug("[Auth] Admin user lookup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = getattr(response, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin_roles = (
        _extract_admin_roles(getattr(user, "app_metadata", None))
        | _extract_admin_roles(getattr(user, "user_metadata", None))
    )
    if admin_roles.isdisjoint({"admin", "service_role", "supabase_admin"}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return {
        "auth_type": "supabase_user",
        "user_id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
        "roles": sorted(admin_roles),
    }
