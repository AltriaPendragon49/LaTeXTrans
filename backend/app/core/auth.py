from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.config import get_settings
from backend.app.policies import authorize
from backend.app.services.auth_service import AuthServiceError, LocalAuthService

# 允许可选的依赖项缺失 Authorization 头（游客模式）
security = HTTPBearer(auto_error=False)


def extract_bearer_token_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    """从 HTTP 授权凭据中提取 Bearer 令牌"""
    if credentials is None or not credentials.credentials:
        return None
    return credentials.credentials.strip() or None


def extract_bearer_token(request: Any) -> Optional[str]:
    """从请求头中提取 Bearer 令牌"""
    header_value = str(request.headers.get("authorization", ""))
    if not header_value.lower().startswith("bearer "):
        return None
    token = header_value[7:].strip()
    return token or None


def resolve_current_user_id(
    current_user: Any,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    """从当前用户字典中解析用户 ID，支持 id、user_id、sub 等键名"""
    del credentials

    if not isinstance(current_user, dict):
        return None

    for key in ("id", "user_id", "sub"):
        value = current_user.get(key)
        if value:
            return str(value)
    return None


def get_auth_service() -> LocalAuthService:
    """获取本地认证服务实例"""
    return LocalAuthService()


async def optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict[str, Any]]:
    """可选认证：如果提供了有效令牌则返回当前用户，否则返回 None（游客模式）"""
    token = extract_bearer_token_from_credentials(credentials)
    if not token:
        return None

    try:
        return await get_auth_service().get_current_user_from_token(token)
    except AuthServiceError:
        return None


async def require_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict[str, Any]:
    """强制认证：必须提供有效令牌，否则返回 401"""
    token = extract_bearer_token_from_credentials(credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_SESSION_INVALID", "message": "Session is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await get_auth_service().get_current_user_from_token(token)
    except AuthServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_admin_user(
    current_user: dict[str, Any] = Depends(require_current_user),
) -> dict[str, Any]:
    """管理员认证：在 require_current_user 基础上验证用户是否具有 admin 角色"""
    roles = {str(role).strip().lower() for role in (current_user.get("roles") or [])}
    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "Admin access required."},
        )
    return current_user


async def require_admin_request(
    current_user: Any = Depends(require_admin_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict[str, Any]:
    """管理员请求认证：验证管理员用户并检查 admin_cleanup 策略的执行权限"""
    if isinstance(current_user, HTTPAuthorizationCredentials):
        credentials = current_user
        current_user = None

    if isinstance(current_user, dict):
        decision = authorize(current_user, "admin_cleanup", "execute")
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "AUTH_FORBIDDEN", "message": decision.reason},
            )
        return {
            "auth_type": "local_user",
            "user_id": current_user.get("id"),
            "roles": current_user.get("roles", []),
        }

    token = extract_bearer_token_from_credentials(credentials)
    if token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "Admin access required."},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "AUTH_SESSION_INVALID", "message": "Session is invalid or expired."},
        headers={"WWW-Authenticate": "Bearer"},
    )
