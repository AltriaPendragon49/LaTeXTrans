import asyncio
import sqlite3
from pathlib import Path

import httpx
import pytest

from backend.app.core.config import get_settings
from backend.app.services.auth_service import AuthServiceError, LocalAuthService, NiuTransAuthClient


def _create_sqlite_schema(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            create table users (
              id text primary key,
              external_provider text not null,
              external_user_id text not null,
              email text null,
              display_name text null,
              token_version integer not null default 1,
              status text not null default 'active',
              created_at text not null,
              updated_at text not null
            );
            create unique index uq_users_provider_external on users (external_provider, external_user_id);

            create table user_roles (
              user_id text not null,
              role text not null,
              created_at text not null,
              primary key (user_id, role)
            );

            create table auth_sessions (
              id text primary key,
              user_id text not null,
              status text not null default 'active',
              issued_at text not null,
              expires_at text not null,
              revoked_at text null,
              last_seen_at text null,
              client_ip text null,
              user_agent text null
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_local_auth_service_roundtrip_with_sqlite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database_path = tmp_path / "local-auth.db"
    _create_sqlite_schema(database_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    monkeypatch.setattr(settings, "auth_jwt_keys", "v1:test-secret")
    monkeypatch.setattr(settings, "auth_jwt_issuer", "test-issuer")
    monkeypatch.setattr(settings, "auth_jwt_audience", "test-audience")
    monkeypatch.setattr(settings, "auth_access_token_ttl_seconds", 3600)
    monkeypatch.setattr(settings, "local_admin_external_user_ids", ["179017"])

    service = LocalAuthService()

    async def fake_verify_credentials(*, identifier: str, password: str):
        assert identifier == "alice@example.com"
        assert password == "secret"
        return {
            "external_user_id": "179017",
            "email": "alice@example.com",
            "display_name": "Alice",
        }

    monkeypatch.setattr(service._upstream_client, "verify_credentials", fake_verify_credentials)

    login_result = asyncio.run(
        service.login(
            identifier="alice@example.com",
            password="secret",
            client_ip="127.0.0.1",
            user_agent="pytest",
        )
    )

    assert login_result["user"]["external_user_id"] == "179017"
    assert "admin" in login_result["user"]["roles"]

    current_user = asyncio.run(
        service.get_current_user_from_token(login_result["access_token"])
    )
    assert current_user["id"] == login_result["user"]["id"]

    asyncio.run(service.logout_current_session(login_result["access_token"]))

    with pytest.raises(Exception):
        asyncio.run(service.get_current_user_from_token(login_result["access_token"]))


def test_niutrans_auth_client_maps_upstream_login_exception_to_invalid_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict[str, object]:
            return {"code": 1006, "msg": "登录异常", "data": None}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    client = NiuTransAuthClient()

    with pytest.raises(AuthServiceError) as exc_info:
        asyncio.run(
            client.verify_credentials(
                identifier="alice@example.com",
                password="secret",
            )
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "AUTH_INVALID_CREDENTIALS"
