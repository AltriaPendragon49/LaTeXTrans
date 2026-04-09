import asyncio

import httpx
import pytest

from backend.app.main import app
from backend.app.policies.base import AuthorizationResult


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


class _FakeSettingsRepository:
    def __init__(self) -> None:
        self.records: dict[str, dict] = {}

    def get_user_settings(self, user_id: str):
        return self.records.get(user_id)

    def upsert_user_settings(self, user_id: str, updates: dict):
        current = self.records.get(user_id, {}).copy()
        current.update(updates)
        self.records[user_id] = current
        return current


def test_settings_routes_use_local_current_user_and_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.api.routes import settings as settings_route

    fake_repo = _FakeSettingsRepository()
    monkeypatch.setattr(settings_route, "get_user_settings_repository", lambda: fake_repo)
    app.dependency_overrides[settings_route.require_current_user] = lambda: {"id": "usr_local_1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            get_response = await client.get("/api/settings")
            put_response = await client.put(
                "/api/settings",
                json={
                    "default_source_language": "en",
                    "default_target_language": "zh",
                    "translation_mode": "full",
                    "custom_api_key": "secret-key",
                    "custom_base_url": "https://example.invalid/v1/chat/completions",
                },
            )
            get_after_put = await client.get("/api/settings")
            return get_response, put_response, get_after_put

    get_response, put_response, get_after_put = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert get_response.status_code == 200
    assert get_response.json()["default_source_language"] == "en"
    assert put_response.status_code == 200
    assert put_response.json()["has_custom_api_key"] is True
    assert get_after_put.status_code == 200
    assert get_after_put.json()["custom_base_url"] == "https://example.invalid/v1/chat/completions"


def test_settings_routes_use_central_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.api.routes import settings as settings_route

    fake_repo = _FakeSettingsRepository()
    authorize_calls: list[tuple[str, str]] = []

    def _fake_authorize(user, resource, action, context=None):
        authorize_calls.append((resource, action))
        return AuthorizationResult(
            allowed=True,
            reason="ok",
            resource=resource,
            action=action,
        )

    monkeypatch.setattr(settings_route, "get_user_settings_repository", lambda: fake_repo)
    monkeypatch.setattr(settings_route, "authorize", _fake_authorize)
    app.dependency_overrides[settings_route.require_current_user] = lambda: {"id": "usr_local_1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            get_response = await client.get("/api/settings")
            put_response = await client.put("/api/settings", json={"default_source_language": "en"})
            return get_response, put_response

    get_response, put_response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert get_response.status_code == 200
    assert put_response.status_code == 200
    assert authorize_calls == [("settings", "read"), ("settings", "update")]
