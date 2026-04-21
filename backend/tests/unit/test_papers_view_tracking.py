import asyncio
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.db import DatabaseUnavailableError
from backend.app.services import paper_service


def test_record_view_increments_visible_paper(monkeypatch):
    class _FakeCommunityRepository:
        def increment_view_count(self, _paper_id: str):
            return 3

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())

    result = asyncio.run(paper_service.record_community_paper_view(paper_id="paper-view"))

    assert result == {"paper_id": "paper-view", "view_count": 3}


def test_record_view_returns_404_for_missing_or_hidden_paper(monkeypatch):
    class _UnavailableCommunityRepository:
        def increment_view_count(self, _paper_id: str):
            raise DatabaseUnavailableError("local database unavailable")

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _UnavailableCommunityRepository())
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda _paper_id: asyncio.sleep(0, result=None),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(paper_service.record_community_paper_view(paper_id="missing"))

    assert exc_info.value.status_code == 404


def test_record_view_gracefully_degrades_when_local_repository_is_unavailable(monkeypatch):
    class _UnavailableCommunityRepository:
        def increment_view_count(self, _paper_id: str):
            raise DatabaseUnavailableError("local database unavailable")

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _UnavailableCommunityRepository())
    monkeypatch.setattr(
        paper_service,
        "_fetch_paper_by_id",
        lambda paper_id: asyncio.sleep(
            0,
            result={
                "id": paper_id,
                "visibility": "public",
                "status": "published",
                "view_count": 0,
            },
        ),
    )

    result = asyncio.run(paper_service.record_community_paper_view(paper_id="paper-view"))

    assert result == {"paper_id": "paper-view", "view_count": 0}


def test_record_view_passes_user_id_and_anon_id_to_repository(monkeypatch):
    captured = {}

    class _FakeCommunityRepository:
        def record_daily_view(self, *, paper_id: str, user_id: str | None = None, anon_id: str | None = None):
            captured["paper_id"] = paper_id
            captured["user_id"] = user_id
            captured["anon_id"] = anon_id
            return 6

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _FakeCommunityRepository())

    result = asyncio.run(
        paper_service.record_community_paper_view(
            paper_id="paper-view",
            user_id="user-1",
            anon_id="anon-1",
        )
    )

    assert captured == {"paper_id": "paper-view", "user_id": "user-1", "anon_id": "anon-1"}
    assert result == {"paper_id": "paper-view", "view_count": 6}
