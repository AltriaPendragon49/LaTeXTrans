import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.core import auth
from backend.app.policies.base import AuthorizationResult
from backend.app.main import app
import backend.app.main as main_module


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def test_admin_cleanup_route_requires_authentication() -> None:
    async def _call():
        async with _make_client() as client:
            return await client.post("/api/admin/cleanup")

    response = asyncio.run(_call())

    assert response.status_code == 401


def test_admin_cleanup_route_runs_when_admin_dependency_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_cleanup():
        return {"ok": True, "reset_papers": 2, "deleted_folders": 1, "errors": []}

    monkeypatch.setattr(main_module, "reset_stale_community_tasks", fake_cleanup)
    app.dependency_overrides[main_module.require_admin_request] = lambda: {"auth_type": "test-admin"}

    async def _call():
        async with _make_client() as client:
            return await client.post("/api/admin/cleanup")

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["reset_papers"] == 2


def test_require_admin_request_rejects_non_admin_user(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAuthClient:
        def get_user(self, token):
            return SimpleNamespace(
                user=SimpleNamespace(
                    id="user-1",
                    email="user@example.com",
                    app_metadata={"role": "authenticated"},
                    user_metadata={},
                )
            )

    monkeypatch.setattr(
        auth,
        "create_supabase_client_with_token",
        lambda token: SimpleNamespace(auth=FakeAuthClient()),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            auth.require_admin_request(
                HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials="header.payload.signature",
                )
            )
        )

    assert exc_info.value.status_code == 403


def test_require_admin_request_accepts_service_role_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(
            supabase_service_role_key="service-role-secret",
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
        ),
    )

    result = asyncio.run(
        auth.require_admin_request(
            HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="service-role-secret",
            )
        )
    )

    assert result["auth_type"] == "service_role"


def test_require_admin_request_uses_central_authorization_for_local_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth,
        "authorize",
        lambda *_args, **_kwargs: AuthorizationResult(
            allowed=False,
            reason="central policy denied admin cleanup",
            resource="admin_cleanup",
            action="execute",
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            auth.require_admin_request(
                current_user={"id": "usr-1", "roles": ["admin"]},
                credentials=None,
            )
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["message"] == "central policy denied admin cleanup"
