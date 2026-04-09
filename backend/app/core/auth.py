from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.config import get_settings
from backend.app.policies import authorize
from backend.app.services.auth_service import AuthServiceError, LocalAuthService

# Allow missing Authorization header (guest mode) on optional dependencies.
security = HTTPBearer(auto_error=False)


def extract_bearer_token_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if credentials is None or not credentials.credentials:
        return None
    return credentials.credentials.strip() or None


def extract_bearer_token(request: Any) -> Optional[str]:
    header_value = str(request.headers.get("authorization", ""))
    if not header_value.lower().startswith("bearer "):
        return None
    token = header_value[7:].strip()
    return token or None


def resolve_current_user_id(
    current_user: Any,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    del credentials

    if not isinstance(current_user, dict):
        return None

    for key in ("id", "user_id", "sub"):
        value = current_user.get(key)
        if value:
            return str(value)
    return None


def get_auth_service() -> LocalAuthService:
    return LocalAuthService()


async def optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict[str, Any]]:
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
    roles = {str(role).strip().lower() for role in (current_user.get("roles") or [])}
    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH_FORBIDDEN", "message": "Admin access required."},
        )
    return current_user


def create_supabase_client_with_token(access_token: Optional[str] = None) -> None:
    # Legacy compatibility shim retained for older tests and monkeypatch paths.
    del access_token
    return None


def clone_supabase_client_with_same_auth(client: Any) -> None:
    del client
    return None


async def get_supabase_client_from_request(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> None:
    del credentials
    return None


async def require_admin_request(
    current_user: Any = Depends(require_admin_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict[str, Any]:
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
