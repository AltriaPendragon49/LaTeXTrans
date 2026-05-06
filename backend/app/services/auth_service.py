from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from backend.app.core.config import get_settings
from backend.app.db import DatabaseUnavailableError
from backend.app.repositories import AuthRepository
from backend.app.services.translation_quota_service import TranslationQuotaService
from backend.app.utils.async_blocking import run_blocking


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    normalized = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(normalized.encode("utf-8"))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_unix() -> int:
    return int(_now_utc().timestamp())


@dataclass
class AuthServiceError(Exception):
    status_code: int
    code: str
    message: str


class NiuTransAuthClient:
    def __init__(self) -> None:
        self._settings = get_settings()

    @staticmethod
    def _extract_first(payload: Any, *candidate_paths: tuple[str, ...]) -> Optional[str]:
        for path in candidate_paths:
            current = payload
            for key in path:
                if not isinstance(current, dict):
                    current = None
                    break
                current = current.get(key)
            if current is not None and str(current).strip():
                return str(current).strip()
        return None

    @staticmethod
    def _extract_first_raw(payload: Any, *candidate_paths: tuple[str, ...]) -> Any:
        for path in candidate_paths:
            current = payload
            for key in path:
                if not isinstance(current, dict):
                    current = None
                    break
                current = current.get(key)
            if current is not None and str(current).strip():
                return current
        return None

    @classmethod
    def _extract_int(cls, payload: Any, *candidate_paths: tuple[str, ...]) -> Optional[int]:
        value = cls._extract_first_raw(payload, *candidate_paths)
        if value is None or isinstance(value, bool):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    async def verify_credentials(self, *, identifier: str, password: str) -> dict[str, Any]:
        request_payload = {
            "identifier": identifier,
            "password": password,
            "loginMode": "Password",
            "isSubAccount": "0",
        }
        request_headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://niutrans.com",
            "Referer": self._settings.niutrans_login_url,
            "User-Agent": "LaTexTrans-LocalAuth/1.0",
        }
        timeout = httpx.Timeout(15.0, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self._settings.niutrans_auth_url,
                    data=request_payload,
                    headers=request_headers,
                )
        except httpx.HTTPError as exc:
            raise AuthServiceError(
                status_code=503,
                code="AUTH_UPSTREAM_UNAVAILABLE",
                message="NiuTrans authentication is temporarily unavailable.",
            ) from exc

        if response.status_code in {400, 401, 403}:
            raise AuthServiceError(
                status_code=401,
                code="AUTH_INVALID_CREDENTIALS",
                message="Invalid credentials.",
            )
        if response.status_code >= 500:
            raise AuthServiceError(
                status_code=503,
                code="AUTH_UPSTREAM_UNAVAILABLE",
                message="NiuTrans authentication is temporarily unavailable.",
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AuthServiceError(
                status_code=503,
                code="AUTH_UPSTREAM_UNAVAILABLE",
                message="NiuTrans authentication returned an invalid response.",
            ) from exc

        if isinstance(payload, dict):
            upstream_code = payload.get("code")
            upstream_message = self._extract_first(
                payload,
                ("msg",),
                ("message",),
                ("error", "message"),
            )
            if upstream_code == 1006:
                raise AuthServiceError(
                    status_code=401,
                    code="AUTH_INVALID_CREDENTIALS",
                    message="NiuTrans did not accept these credentials.",
                )
            if isinstance(upstream_code, int) and upstream_code not in {0, 200}:
                raise AuthServiceError(
                    status_code=503,
                    code="AUTH_UPSTREAM_UNAVAILABLE",
                    message=upstream_message or "NiuTrans authentication is temporarily unavailable.",
                )

        external_user_id = self._extract_first(
            payload,
            ("userId",),
            ("data", "userId"),
            ("data", "user", "userId"),
            ("user", "userId"),
        )
        if not external_user_id:
            raise AuthServiceError(
                status_code=503,
                code="AUTH_UPSTREAM_UNAVAILABLE",
                message="NiuTrans authentication did not return a user identifier.",
            )

        return {
            "external_user_id": external_user_id,
            "email": self._extract_first(
                payload,
                ("email",),
                ("data", "email"),
                ("data", "user", "email"),
                ("user", "email"),
            ),
            "display_name": self._extract_first(
                payload,
                ("displayName",),
                ("nickname",),
                ("username",),
                ("data", "displayName"),
                ("data", "nickname"),
                ("data", "user", "displayName"),
                ("data", "user", "nickname"),
            ),
            "upstream_token": self._extract_first(
                payload,
                ("token",),
                ("accessToken",),
                ("data", "token"),
                ("data", "accessToken"),
                ("data", "user", "token"),
            ),
        }

    async def fetch_user_info_balance(self, *, token: str, user_id: str) -> dict[str, Any]:
        request_headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": token,
            "Niutrans-userid": user_id,
            "User-Agent": "LaTexTrans-LocalAuth/1.0",
        }
        timeout = httpx.Timeout(15.0, connect=10.0)
        fetched_at = _now_utc()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    self._settings.niutrans_user_info_url,
                    headers=request_headers,
                )
        except httpx.HTTPError:
            return {
                "unused_num_integral": None,
                "status": "unavailable",
                "fetched_at": fetched_at,
            }

        if response.status_code >= 400:
            return {
                "unused_num_integral": None,
                "status": "unavailable",
                "fetched_at": fetched_at,
            }

        try:
            payload = response.json()
        except ValueError:
            return {
                "unused_num_integral": None,
                "status": "unavailable",
                "fetched_at": fetched_at,
            }

        unused_num_integral = self._extract_int(
            payload,
            ("unusedNumIntegral",),
            ("data", "unusedNumIntegral"),
            ("data", "user", "unusedNumIntegral"),
            ("user", "unusedNumIntegral"),
        )
        if unused_num_integral is None:
            return {
                "unused_num_integral": None,
                "status": "unavailable",
                "fetched_at": fetched_at,
            }
        return {
            "unused_num_integral": unused_num_integral,
            "status": "available",
            "fetched_at": fetched_at,
        }


class LocalAuthService:
    def __init__(
        self,
        *,
        repository: Optional[AuthRepository] = None,
        upstream_client: Optional[NiuTransAuthClient] = None,
        quota_service: Optional[TranslationQuotaService] = None,
    ) -> None:
        self._settings = get_settings()
        self._repository = repository or AuthRepository()
        self._upstream_client = upstream_client or NiuTransAuthClient()
        self._quota_service = quota_service or TranslationQuotaService()

    def _parse_jwt_keys(self) -> list[tuple[str, str]]:
        raw_value = str(self._settings.auth_jwt_keys or "").strip()
        items = [item.strip() for item in raw_value.split(",") if item.strip()]
        parsed: list[tuple[str, str]] = []
        for item in items:
            version, _, secret = item.partition(":")
            if version and secret:
                parsed.append((version.strip(), secret.strip()))
        if not parsed:
            raise AuthServiceError(
                status_code=503,
                code="AUTH_SESSION_INVALID",
                message="Local auth signing keys are not configured.",
            )
        return parsed

    def _build_local_user_payload(self, user: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": user["id"],
            "external_provider": user["external_provider"],
            "external_user_id": user["external_user_id"],
            "login_identifier": user.get("login_identifier"),
            "roles": list(user.get("roles") or ["user"]),
            "display_name": user.get("display_name"),
            "email": user.get("email"),
        }

    async def _store_pdf_balance_snapshot_from_upstream(
        self,
        *,
        user_id: str,
        upstream_user: dict[str, Any],
    ) -> None:
        upstream_token = str(upstream_user.get("upstream_token") or "").strip()
        external_user_id = str(upstream_user.get("external_user_id") or "").strip()
        if not upstream_token or not external_user_id:
            await run_blocking(
                lambda: self._quota_service.store_pdf_direct_snapshot(
                    user_id=user_id,
                    unused_num_integral=None,
                    status="unavailable",
                    fetched_at=_now_utc(),
                )
            )
            return

        balance = await self._upstream_client.fetch_user_info_balance(
            token=upstream_token,
            user_id=external_user_id,
        )
        await run_blocking(
            lambda: self._quota_service.store_pdf_direct_snapshot(
                user_id=user_id,
                unused_num_integral=balance.get("unused_num_integral"),
                status=str(balance.get("status") or "unavailable"),
                fetched_at=balance.get("fetched_at"),
            )
        )

    async def get_quota_snapshot_for_user(self, user_id: str) -> dict[str, Any]:
        try:
            return await run_blocking(lambda: self._quota_service.get_quota_snapshot(user_id))
        except DatabaseUnavailableError as exc:
            raise AuthServiceError(
                503,
                "AUTH_SESSION_INVALID",
                "Local auth persistence is not configured.",
            ) from exc

    def _encode_jwt(self, payload: dict[str, Any]) -> str:
        version, secret = self._parse_jwt_keys()[0]
        header = {"alg": "HS256", "typ": "JWT", "kid": version}
        signing_input = ".".join(
            [
                _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")),
                _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")),
            ]
        )
        signature = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
        return f"{signing_input}.{_b64url_encode(signature)}"

    def _decode_and_verify_jwt(self, token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")

        signing_input = f"{parts[0]}.{parts[1]}"
        try:
            header = json.loads(_b64url_decode(parts[0]).decode("utf-8"))
            payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
            signature = _b64url_decode(parts[2])
        except (ValueError, json.JSONDecodeError) as exc:
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.") from exc

        verified = False
        for version, secret in self._parse_jwt_keys():
            if header.get("kid") not in {None, version}:
                continue
            expected = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
            if hmac.compare_digest(expected, signature):
                verified = True
                break
        if not verified:
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")

        if payload.get("iss") != self._settings.auth_jwt_issuer:
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")
        if payload.get("aud") != self._settings.auth_jwt_audience:
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")
        if int(payload.get("exp") or 0) <= _now_unix():
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")
        return payload

    async def login(
        self,
        *,
        identifier: str,
        password: str,
        client_ip: Optional[str],
        user_agent: Optional[str],
    ) -> dict[str, Any]:
        normalized_identifier = identifier.strip()
        if not normalized_identifier or not password:
            raise AuthServiceError(400, "AUTH_INVALID_REQUEST", "Identifier and password are required.")

        upstream_user = await self._upstream_client.verify_credentials(
            identifier=normalized_identifier,
            password=password,
        )
        try:
            user = await run_blocking(
                lambda: self._repository.get_or_create_user(
                    external_provider="niutrans",
                    external_user_id=upstream_user["external_user_id"],
                    login_identifier=normalized_identifier,
                    email=upstream_user.get("email"),
                    display_name=upstream_user.get("display_name"),
                )
            )
            expires_at = _now_utc() + timedelta(seconds=self._settings.auth_access_token_ttl_seconds)
            session_id = await run_blocking(
                lambda: self._repository.create_session(
                    user_id=user["id"],
                    expires_at=expires_at,
                    client_ip=client_ip,
                    user_agent=user_agent,
                )
            )
        except DatabaseUnavailableError as exc:
            raise AuthServiceError(
                503,
                "AUTH_SESSION_INVALID",
                "Local auth persistence is not configured.",
            ) from exc

        try:
            await self._store_pdf_balance_snapshot_from_upstream(
                user_id=user["id"],
                upstream_user=upstream_user,
            )
        except Exception:
            await run_blocking(
                lambda: self._quota_service.store_pdf_direct_snapshot(
                    user_id=user["id"],
                    unused_num_integral=None,
                    status="unavailable",
                    fetched_at=_now_utc(),
                )
            )

        quota_snapshot = await self.get_quota_snapshot_for_user(user["id"])

        payload = {
            "iss": self._settings.auth_jwt_issuer,
            "aud": self._settings.auth_jwt_audience,
            "sub": user["id"],
            "sid": session_id,
            "ver": int(user.get("token_version") or 1),
            "provider": "niutrans",
            "external_user_id": user["external_user_id"],
            "roles": list(user.get("roles") or ["user"]),
            "iat": _now_unix(),
            "exp": int(expires_at.timestamp()),
        }
        token = self._encode_jwt(payload)
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self._settings.auth_access_token_ttl_seconds,
            "user": self._build_local_user_payload(user),
            "quota_snapshot": quota_snapshot,
        }

    async def get_current_user_from_token(self, token: str) -> dict[str, Any]:
        payload = self._decode_and_verify_jwt(token)
        session_id = str(payload.get("sid") or "").strip()
        user_id = str(payload.get("sub") or "").strip()
        if not session_id or not user_id:
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")

        try:
            session = await run_blocking(lambda: self._repository.get_active_session(session_id))
            user = await run_blocking(lambda: self._repository.get_user_by_id(user_id))
        except DatabaseUnavailableError as exc:
            raise AuthServiceError(
                503,
                "AUTH_SESSION_INVALID",
                "Local auth persistence is not configured.",
            ) from exc

        if session is None or user is None:
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")
        if session.get("user_id") != user["id"]:
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")
        if int(payload.get("ver") or 0) != int(user.get("token_version") or 0):
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")

        expires_at = session.get("expires_at")
        if isinstance(expires_at, str):
            expires_dt = datetime.fromisoformat(expires_at)
        else:
            expires_dt = expires_at
        if expires_dt is not None and expires_dt.replace(tzinfo=timezone.utc) <= _now_utc():
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")

        await run_blocking(lambda: self._repository.mark_session_seen(session_id))
        return self._build_local_user_payload(user)

    async def logout_current_session(self, token: str) -> None:
        payload = self._decode_and_verify_jwt(token)
        session_id = str(payload.get("sid") or "").strip()
        if not session_id:
            raise AuthServiceError(401, "AUTH_SESSION_INVALID", "Session is invalid or expired.")
        try:
            await run_blocking(lambda: self._repository.revoke_session(session_id))
        except DatabaseUnavailableError as exc:
            raise AuthServiceError(
                503,
                "AUTH_SESSION_INVALID",
                "Local auth persistence is not configured.",
            ) from exc
