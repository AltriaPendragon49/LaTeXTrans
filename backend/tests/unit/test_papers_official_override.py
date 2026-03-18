import asyncio
import base64
import json
import os
from types import SimpleNamespace

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_service


def _jwt_for(user_id: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": user_id}).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"header.{payload}.sig"


def _close_task(coro):
    coro.close()
    return None


def test_admin_submit_promotes_existing_fallback_to_official(monkeypatch):
    existing = {
        "id": "paper-fallback",
        "source": "arxiv",
        "arxiv_id": "2501.01010",
        "title": "Fallback title",
        "authors": [],
        "categories": [],
        "community_status": "user_fallback",
        "trans_status": "queued",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": None,
        "community_selected_task_id": "task-old",
        "community_selected_asset_id": "asset-old",
        "visibility": "public",
        "status": "published",
        "like_count": 0,
        "favorite_count": 0,
        "comment_count": 0,
        "view_count": 0,
        "download_count": 0,
    }
    captured = {}

    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "admin-1", "roles": ["admin"], "is_admin": True}),
    )
    monkeypatch.setattr(
        paper_service,
        "resolve_community_admission",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "community_status": "official",
                "admission_result": "created",
                "existing_paper": existing,
                "should_create": False,
            },
        ),
    )
    monkeypatch.setattr(
        paper_service.arxiv_route,
        "download_arxiv",
        lambda **_kwargs: asyncio.sleep(0, result=SimpleNamespace(task_id="task-new-official")),
    )

    async def _fake_update_paper(paper_id, payload):
        captured["paper_id"] = paper_id
        captured["payload"] = payload
        return {**existing, **payload}

    monkeypatch.setattr(paper_service, "_update_paper", _fake_update_paper)
    monkeypatch.setattr(paper_service.asyncio, "create_task", _close_task)

    result = asyncio.run(
        paper_service.submit_arxiv_paper(
            arxiv_id="2501.01010",
            credentials=SimpleNamespace(credentials=_jwt_for("admin-1")),
        )
    )

    assert captured["paper_id"] == "paper-fallback"
    assert captured["payload"]["community_status"] == "official"
    assert captured["payload"]["community_selected_task_id"] == "task-new-official"
    assert captured["payload"]["official_published_at"] is not None
    assert result["paper"]["community_status"] == "official"
    assert result["task"]["task_id"] == "task-new-official"
