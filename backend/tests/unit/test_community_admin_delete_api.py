import asyncio

import httpx

from backend.app.api.routes import papers as papers_route
from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def test_admin_delete_paper_route_returns_delete_job(monkeypatch) -> None:
    async def fake_delete_community_paper_admin(*, paper_id: str, current_user):  # type: ignore[no-untyped-def]
        assert paper_id == "paper-1"
        assert current_user["id"] == "admin-1"
        return {
            "job_id": "delete-job-1",
            "paper_id": "paper-1",
            "status": "queued",
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.delete_community_paper_admin",
        fake_delete_community_paper_admin,
        raising=False,
    )
    app.dependency_overrides[papers_route.require_current_user] = lambda: {
        "id": "admin-1",
        "roles": ["admin"],
    }

    async def _call():
        async with _make_client() as client:
            return await client.delete("/api/papers/admin/paper-1")

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "delete-job-1",
        "paper_id": "paper-1",
        "status": "queued",
    }
