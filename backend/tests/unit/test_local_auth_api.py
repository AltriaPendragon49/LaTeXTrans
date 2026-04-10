import asyncio

import httpx
import pytest

from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


class _FakeAuthService:
    def __init__(self) -> None:
        self.logged_out_tokens: list[str] = []

    async def login(self, *, identifier: str, password: str, client_ip: str | None, user_agent: str | None):
        assert identifier == "alice@example.com"
        assert password == "secret"
        assert client_ip is None or isinstance(client_ip, str)
        assert user_agent is None or isinstance(user_agent, str)
        return {
            "access_token": "local-token-123",
            "token_type": "Bearer",
            "expires_in": 28800,
            "user": {
                "id": "usr_123",
                "external_provider": "niutrans",
                "external_user_id": "179017",
                "roles": ["user"],
                "display_name": "Alice",
                "email": None,
            },
        }

    async def get_current_user_from_token(self, token: str):
        if token != "local-token-123":
            raise ValueError("AUTH_SESSION_INVALID")
        return {
            "id": "usr_123",
            "external_provider": "niutrans",
            "external_user_id": "179017",
            "roles": ["user"],
            "display_name": "Alice",
            "email": None,
        }

    async def logout_current_session(self, token: str) -> None:
        self.logged_out_tokens.append(token)


def test_auth_login_returns_local_session_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.api.routes import auth as auth_route

    fake_service = _FakeAuthService()
    monkeypatch.setattr(auth_route, "get_auth_service", lambda: fake_service)

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/auth/login",
                json={"identifier": "alice@example.com", "password": "secret"},
            )

    response = asyncio.run(_call())

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "local-token-123",
        "token_type": "Bearer",
        "expires_in": 28800,
        "user": {
            "id": "usr_123",
            "external_provider": "niutrans",
            "external_user_id": "179017",
            "roles": ["user"],
            "display_name": "Alice",
            "email": None,
        },
    }


def test_auth_me_returns_401_without_token() -> None:
    async def _call():
        async with _make_client() as client:
            return await client.get("/api/auth/me")

    response = asyncio.run(_call())

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_SESSION_INVALID"


def test_auth_me_returns_bootstrap_user_for_valid_local_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.api.routes import auth as auth_route

    fake_service = _FakeAuthService()
    monkeypatch.setattr(auth_route, "get_auth_service", lambda: fake_service)

    async def _call():
        async with _make_client() as client:
            return await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer local-token-123"},
            )

    response = asyncio.run(_call())

    assert response.status_code == 200
    assert response.json() == {
        "user": {
            "id": "usr_123",
            "external_provider": "niutrans",
            "external_user_id": "179017",
            "roles": ["user"],
            "display_name": "Alice",
            "email": None,
        }
    }


def test_auth_logout_revokes_current_session(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.api.routes import auth as auth_route

    fake_service = _FakeAuthService()
    monkeypatch.setattr(auth_route, "get_auth_service", lambda: fake_service)

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/auth/logout",
                headers={"Authorization": "Bearer local-token-123"},
            )

    response = asyncio.run(_call())

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fake_service.logged_out_tokens == ["local-token-123"]
