from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.app.core.auth import extract_bearer_token
from backend.app.services.auth_service import AuthServiceError, LocalAuthService

router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LocalUserPayload(BaseModel):
    id: str
    external_provider: str
    external_user_id: str
    login_identifier: str | None = None
    roles: list[str]
    display_name: str | None = None
    email: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: LocalUserPayload


class MeResponse(BaseModel):
    user: LocalUserPayload


def get_auth_service() -> LocalAuthService:
    return LocalAuthService()


def _error_response(exc: AuthServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, payload: LoginRequest):
    auth_service = get_auth_service()
    try:
        result = await auth_service.login(
            identifier=payload.identifier,
            password=payload.password,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthServiceError as exc:
        return _error_response(exc)
    return result


@router.get("/me", response_model=MeResponse)
async def current_user(request: Request):
    auth_service = get_auth_service()
    token = extract_bearer_token(request)
    if not token:
        return JSONResponse(
            status_code=401,
            content={"code": "AUTH_SESSION_INVALID", "message": "Session is invalid or expired."},
        )

    try:
        user = await auth_service.get_current_user_from_token(token)
    except AuthServiceError as exc:
        return _error_response(exc)
    return {"user": user}


@router.post("/logout")
async def logout(request: Request):
    auth_service = get_auth_service()
    token = extract_bearer_token(request)
    if not token:
        return JSONResponse(
            status_code=401,
            content={"code": "AUTH_SESSION_INVALID", "message": "Session is invalid or expired."},
        )

    try:
        await auth_service.logout_current_session(token)
    except AuthServiceError as exc:
        return _error_response(exc)
    return {"ok": True}
