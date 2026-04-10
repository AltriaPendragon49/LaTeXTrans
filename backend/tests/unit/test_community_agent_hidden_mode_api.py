import asyncio

import httpx

from backend.app.api.routes import community_agent as community_agent_route
from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def test_hidden_community_agent_mode_rejects_direct_product_access(monkeypatch) -> None:
    monkeypatch.setattr(community_agent_route.settings, "community_agent_product_enabled", False)
    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-1"}

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/community-agent/runs",
                json={"input": "Explain this paper"},
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert "hidden" in response.json()["detail"].lower()
