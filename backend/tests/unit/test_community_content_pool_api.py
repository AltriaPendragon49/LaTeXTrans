import asyncio
from typing import Any, Dict

import httpx

from backend.app.main import app
from backend.app.api.routes import papers as papers_route


def _make_client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": "Bearer header.payload.signature"}


def test_content_pool_readiness_route_requires_authentication() -> None:
    async def _call():
        async with _make_client() as client:
            return await client.get("/api/papers/content-pool/readiness")

    response = asyncio.run(_call())

    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_content_pool_readiness_route_returns_operator_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.community_content_pool_service.get_content_pool_readiness_snapshot",
        lambda: {
            "candidate_total": 3,
            "warmed_total": 2,
            "translated_ready_total": 2,
            "failure_total": 1,
            "running_total": 0,
            "freshness": "2026-03-26T13:00:00+00:00",
            "stage_totals": {
                "discover": 3,
                "admit": 3,
                "source": 3,
                "translate": 2,
                "preview": 2,
                "promote": 2,
            },
            "updated_at": "2026-03-26T13:00:00+00:00",
        },
    )

    app.dependency_overrides[papers_route.require_current_user] = lambda: {"id": "admin-1", "roles": ["admin"]}

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/papers/content-pool/readiness", headers=_auth_headers())

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_total"] == 3
    assert payload["translated_ready_total"] == 2
    assert payload["failure_total"] == 1
    assert payload["stage_totals"]["promote"] == 2


def test_content_pool_job_log_route_requires_authentication() -> None:
    async def _call():
        async with _make_client() as client:
            return await client.get("/api/papers/content-pool/jobs")

    response = asyncio.run(_call())

    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_content_pool_job_log_route_forwards_filters(monkeypatch) -> None:
    observed: Dict[str, Any] = {}

    def fake_get_content_pool_job_log(*, arxiv_id=None, limit=200):
        observed["arxiv_id"] = arxiv_id
        observed["limit"] = limit
        return [
            {
                "timestamp": "2026-03-26T13:00:00+00:00",
                "arxiv_id": "2503.01010",
                "stage": "promote",
                "status": "completed",
                "attempt": 1,
                "payload": {"translated_ready": True},
                "error": None,
            }
        ]

    monkeypatch.setattr(
        "backend.app.services.community_content_pool_service.get_content_pool_job_log",
        fake_get_content_pool_job_log,
    )

    app.dependency_overrides[papers_route.require_current_user] = lambda: {"id": "admin-1", "roles": ["admin"]}

    async def _call():
        async with _make_client() as client:
            return await client.get(
                "/api/papers/content-pool/jobs",
                params={"arxiv_id": "2503.01010", "limit": 50},
                headers=_auth_headers(),
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert observed == {"arxiv_id": "2503.01010", "limit": 50}
    assert payload[0]["stage"] == "promote"
    assert payload[0]["status"] == "completed"


def test_content_pool_readiness_route_rejects_non_admin_user(monkeypatch) -> None:
    app.dependency_overrides[papers_route.require_current_user] = lambda: {"id": "user-1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/papers/content-pool/readiness", headers=_auth_headers())

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 403
