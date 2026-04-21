import asyncio
import os
from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import papers as papers_route
from backend.app.main import app
from backend.app.services import paper_service


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def test_list_favorite_folders_route_requires_authentication() -> None:
    async def _call():
        async with _make_client() as client:
            return await client.get("/api/papers/favorite-folders")

    response = asyncio.run(_call())

    assert response.status_code == 401


def test_list_favorite_folders_route_returns_service_payload(monkeypatch) -> None:
    async def fake_list_favorite_folders(*, user_id: str):  # type: ignore[no-untyped-def]
        assert user_id == "user-1"
        return {
            "items": [
                {
                    "id": "folder-1",
                    "name": "Reading list",
                    "paper_count": 2,
                    "created_at": "2026-04-21T00:00:00",
                    "updated_at": "2026-04-21T00:00:00",
                }
            ]
        }

    monkeypatch.setattr(paper_service, "list_favorite_folders", fake_list_favorite_folders, raising=False)
    app.dependency_overrides[papers_route.require_current_user] = lambda: {"id": "user-1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/papers/favorite-folders")

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["name"] == "Reading list"


def test_create_favorite_folder_route_serializes_datetime_fields(monkeypatch) -> None:
    async def fake_create_favorite_folder(*, user_id: str, name: str):  # type: ignore[no-untyped-def]
        assert user_id == "user-1"
        assert name == "Reading list"
        return {
            "folder": {
                "id": "folder-1",
                "name": "Reading list",
                "paper_count": 0,
                "created_at": datetime(2026, 4, 21, 17, 33, 41),
                "updated_at": datetime(2026, 4, 21, 17, 33, 41),
            }
        }

    monkeypatch.setattr(paper_service, "create_favorite_folder", fake_create_favorite_folder, raising=False)
    app.dependency_overrides[papers_route.require_current_user] = lambda: {"id": "user-1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            return await client.post("/api/papers/favorite-folders", json={"name": "Reading list"})

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "folder": {
            "id": "folder-1",
            "name": "Reading list",
            "paper_count": 0,
            "created_at": "2026-04-21T17:33:41",
            "updated_at": "2026-04-21T17:33:41",
        }
    }


def test_put_paper_favorite_folders_route_returns_updated_state(monkeypatch) -> None:
    async def fake_update_paper_favorite_folders(*, paper_id: str, user_id: str, folder_ids: list[str]):  # type: ignore[no-untyped-def]
        assert paper_id == "paper-1"
        assert user_id == "user-1"
        assert folder_ids == ["folder-1", "folder-2"]
        return {
            "paper_id": "paper-1",
            "favorited": True,
            "favorite_folder_count": 2,
            "favorite_count": 1,
            "selected_folder_ids": ["folder-1", "folder-2"],
        }

    monkeypatch.setattr(
        paper_service,
        "update_paper_favorite_folders",
        fake_update_paper_favorite_folders,
        raising=False,
    )
    app.dependency_overrides[papers_route.require_current_user] = lambda: {"id": "user-1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            return await client.put(
                "/api/papers/paper-1/favorite-folders",
                json={"folder_ids": ["folder-1", "folder-2"]},
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["favorite_folder_count"] == 2
    assert response.json()["favorited"] is True


def test_like_toggle_routes_return_persistent_like_state(monkeypatch) -> None:
    async def fake_like(*, paper_id: str, user_id: str):  # type: ignore[no-untyped-def]
        assert paper_id == "paper-1"
        assert user_id == "user-1"
        return {"paper_id": paper_id, "liked": True, "like_count": 8}

    async def fake_unlike(*, paper_id: str, user_id: str):  # type: ignore[no-untyped-def]
        assert paper_id == "paper-1"
        assert user_id == "user-1"
        return {"paper_id": paper_id, "liked": False, "like_count": 7}

    monkeypatch.setattr(paper_service, "like_paper", fake_like, raising=False)
    monkeypatch.setattr(paper_service, "unlike_paper", fake_unlike, raising=False)
    app.dependency_overrides[papers_route.require_current_user] = lambda: {"id": "user-1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            like_response = await client.post("/api/papers/paper-1/like")
            unlike_response = await client.delete("/api/papers/paper-1/like")
            return like_response, unlike_response

    like_response, unlike_response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert like_response.status_code == 200
    assert like_response.json() == {"paper_id": "paper-1", "liked": True, "like_count": 8}
    assert unlike_response.status_code == 200
    assert unlike_response.json() == {"paper_id": "paper-1", "liked": False, "like_count": 7}


def test_list_papers_route_uses_private_cache_for_authenticated_viewers(monkeypatch) -> None:
    async def fake_list_community_papers(**_: object):  # type: ignore[no-untyped-def]
        return {
            "items": [],
            "total": 0,
            "offset": 0,
            "limit": 12,
            "has_more": False,
            "next_offset": None,
            "source_mode": "database",
        }

    monkeypatch.setattr(paper_service, "list_community_papers", fake_list_community_papers, raising=False)

    async def _call() -> tuple[httpx.Response, httpx.Response]:
        async with _make_client() as client:
            app.dependency_overrides[papers_route.optional_current_user] = lambda: {"id": "user-1", "roles": ["user"]}
            authenticated = await client.get("/api/papers")
            app.dependency_overrides[papers_route.optional_current_user] = lambda: None
            anonymous = await client.get("/api/papers")
            return authenticated, anonymous

    authenticated, anonymous = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert authenticated.status_code == 200
    assert authenticated.headers["cache-control"] == "private, no-store"
    assert authenticated.headers["vary"] == "Authorization, Cookie"
    assert anonymous.status_code == 200
    assert anonymous.headers["cache-control"] == "public, max-age=60, stale-while-revalidate=300"
    assert anonymous.headers["vary"] == "Authorization, Cookie"


def test_paper_detail_route_uses_private_cache_for_authenticated_viewers(monkeypatch) -> None:
    async def fake_get_community_paper_detail(**_: object):  # type: ignore[no-untyped-def]
        return {
            "paper": {
                "id": "paper-1",
                "source": "arxiv",
                "title": "Example paper",
                "authors": [],
                "categories": [],
                "community_status": "official",
                "trans_status": "completed",
                "created_at": "2026-04-21T00:00:00",
                "official_published_at": "2026-04-21T00:00:00",
            },
            "reader_state": "ready",
        }

    monkeypatch.setattr(
        paper_service,
        "get_community_paper_detail",
        fake_get_community_paper_detail,
        raising=False,
    )

    async def _call() -> tuple[httpx.Response, httpx.Response]:
        async with _make_client() as client:
            app.dependency_overrides[papers_route.optional_current_user] = lambda: {"id": "user-1", "roles": ["user"]}
            authenticated = await client.get("/api/papers/paper-1")
            app.dependency_overrides[papers_route.optional_current_user] = lambda: None
            anonymous = await client.get("/api/papers/paper-1")
            return authenticated, anonymous

    authenticated, anonymous = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert authenticated.status_code == 200
    assert authenticated.headers["cache-control"] == "private, no-store"
    assert authenticated.headers["vary"] == "Authorization, Cookie"
    assert anonymous.status_code == 200
    assert anonymous.headers["cache-control"] == "public, max-age=30, stale-while-revalidate=120"
    assert anonymous.headers["vary"] == "Authorization, Cookie"


def test_record_view_route_accepts_authenticated_and_anonymous_principals(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    async def fake_record_view(*, paper_id: str, user_id: str | None = None, anon_id: str | None = None):  # type: ignore[no-untyped-def]
        captured["paper_id"] = paper_id
        captured["user_id"] = user_id
        captured["anon_id"] = anon_id
        return {"paper_id": paper_id, "view_count": 4}

    monkeypatch.setattr(paper_service, "record_community_paper_view", fake_record_view)

    async def _call():
        async with _make_client() as client:
            app.dependency_overrides[papers_route.optional_current_user] = lambda: None
            anon_response = await client.post(
                "/api/papers/paper-1/view",
                headers={"X-Community-Anonymous-Id": "anon-abc"},
            )
            app.dependency_overrides[papers_route.optional_current_user] = lambda: {"id": "user-1", "roles": ["user"]}
            auth_response = await client.post("/api/papers/paper-1/view")
            return anon_response, auth_response

    anon_response, auth_response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert anon_response.status_code == 200
    assert auth_response.status_code == 200
    assert captured["paper_id"] == "paper-1"
    assert captured["user_id"] == "user-1"
    assert captured["anon_id"] == "anon-abc"
