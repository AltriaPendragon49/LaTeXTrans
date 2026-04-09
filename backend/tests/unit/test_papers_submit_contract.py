import asyncio
import base64
import json
import os
from io import BytesIO
from types import SimpleNamespace

from fastapi import UploadFile
from backend.app.policies.base import AuthorizationResult

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import papers as papers_route
from backend.app.services import paper_service


def _jwt_for(user_id: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": user_id}).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"header.{payload}.sig"


def _close_task(coro):
    coro.close()
    return None


def test_admin_submit_arxiv_creates_official(monkeypatch):
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
                "existing_paper": None,
                "should_create": True,
            },
        ),
    )
    monkeypatch.setattr(
        paper_service.arxiv_route,
        "download_arxiv",
        lambda **_kwargs: asyncio.sleep(0, result=SimpleNamespace(task_id="task-official")),
    )
    monkeypatch.setattr(
        paper_service,
        "_insert_paper",
        lambda payload: asyncio.sleep(
            0,
            result={
                "id": "paper-1",
                "created_at": "2026-03-18T00:00:00+00:00",
                **payload,
            },
        ),
    )
    monkeypatch.setattr(paper_service.asyncio, "create_task", _close_task)

    result = asyncio.run(
        paper_service.submit_arxiv_paper(
            arxiv_id="2501.00001",
            credentials=SimpleNamespace(credentials=_jwt_for("admin-1")),
        )
    )

    assert result["paper"]["community_status"] == "official"
    assert result["task"]["task_id"] == "task-official"
    assert result["admission_result"] == "created"


def test_normal_user_submit_arxiv_without_existing_creates_fallback(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "user-1", "roles": [], "is_admin": False}),
    )
    monkeypatch.setattr(
        paper_service,
        "resolve_community_admission",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "community_status": "user_fallback",
                "admission_result": "created",
                "existing_paper": None,
                "should_create": True,
            },
        ),
    )
    monkeypatch.setattr(
        paper_service.arxiv_route,
        "download_arxiv",
        lambda **_kwargs: asyncio.sleep(0, result=SimpleNamespace(task_id="task-fallback")),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_arxiv_metadata",
        lambda _arxiv_id: asyncio.sleep(
            0,
            result={
                "title": "Recovered arXiv title",
                "authors": ["Alice", "Bob"],
                "categories": ["cs.CV", "cs.LG"],
                "abstract_raw": "Recovered abstract",
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_insert_paper",
        lambda payload: asyncio.sleep(
            0,
            result={
                "id": "paper-2",
                "created_at": "2026-03-18T00:00:00+00:00",
                **payload,
            },
        ),
    )
    monkeypatch.setattr(paper_service.asyncio, "create_task", _close_task)

    result = asyncio.run(
        paper_service.submit_arxiv_paper(
            arxiv_id="2501.00002",
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
        )
    )

    assert result["paper"]["community_status"] == "user_fallback"
    assert result["admission_result"] == "created"
    assert result["paper"]["title"] == "Recovered arXiv title"
    assert result["paper"]["authors"] == ["Alice", "Bob"]
    assert result["paper"]["categories"] == ["cs.CV", "cs.LG"]
    assert result["paper"]["abstract_raw"] == "Recovered abstract"


def test_normal_user_submit_arxiv_reuses_existing_official(monkeypatch):
    existing = {
        "id": "paper-3",
        "source": "arxiv",
        "arxiv_id": "2501.00003",
        "title": "Official paper",
        "authors": [],
        "categories": [],
        "community_status": "official",
        "trans_status": "completed",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": "2026-03-18T01:00:00+00:00",
        "community_selected_task_id": "task-existing",
        "community_selected_asset_id": "asset-existing",
        "visibility": "public",
        "status": "published",
        "like_count": 0,
        "favorite_count": 0,
        "comment_count": 0,
        "view_count": 0,
        "download_count": 0,
    }
    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "user-1", "roles": [], "is_admin": False}),
    )
    monkeypatch.setattr(
        paper_service,
        "resolve_community_admission",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "community_status": "official",
                "admission_result": "reused_existing_official",
                "existing_paper": existing,
                "should_create": False,
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_latest_assets",
        lambda paper_ids: asyncio.sleep(
            0,
            result={paper_ids[0]: {"id": "asset-existing", "task_id": "task-existing", "asset_type": "translated_pdf", "file_path": "/tmp/p.pdf", "file_name": "p.pdf", "mime_type": "application/pdf", "created_at": "2026-03-18T01:00:00+00:00"}},
        ),
    )

    result = asyncio.run(
        paper_service.submit_arxiv_paper(
            arxiv_id="2501.00003",
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
        )
    )

    assert result["paper"]["id"] == "paper-3"
    assert result["task"]["task_id"] is None
    assert result["admission_result"] == "reused_existing_official"


def test_normal_user_submit_arxiv_reuses_existing_fallback(monkeypatch):
    existing = {
        "id": "paper-4",
        "source": "arxiv",
        "arxiv_id": "2501.00004",
        "title": "Fallback paper",
        "authors": [],
        "categories": [],
        "community_status": "user_fallback",
        "trans_status": "queued",
        "created_at": "2026-03-18T00:00:00+00:00",
        "official_published_at": None,
        "community_selected_task_id": "task-existing",
        "community_selected_asset_id": None,
        "visibility": "public",
        "status": "published",
        "like_count": 0,
        "favorite_count": 0,
        "comment_count": 0,
        "view_count": 0,
        "download_count": 0,
    }
    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "user-1", "roles": [], "is_admin": False}),
    )
    monkeypatch.setattr(
        paper_service,
        "resolve_community_admission",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "community_status": "user_fallback",
                "admission_result": "reused_existing_fallback",
                "existing_paper": existing,
                "should_create": False,
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_latest_assets",
        lambda paper_ids: asyncio.sleep(0, result={paper_ids[0]: None}),
    )

    result = asyncio.run(
        paper_service.submit_arxiv_paper(
            arxiv_id="2501.00004",
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
        )
    )

    assert result["paper"]["community_status"] == "user_fallback"
    assert result["task"]["task_id"] is None
    assert result["admission_result"] == "reused_existing_fallback"


def test_normal_user_upload_creates_fallback(monkeypatch):
    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context",
        lambda _credentials: asyncio.sleep(0, result={"user_id": "user-1", "roles": [], "is_admin": False}),
    )
    monkeypatch.setattr(
        paper_service.upload_route,
        "upload_file",
        lambda **_kwargs: asyncio.sleep(
            0,
            result=SimpleNamespace(
                task_id="task-upload",
                status="pending",
                source_path="D:/tmp/paper.zip",
            ),
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_insert_paper",
        lambda payload: asyncio.sleep(
            0,
            result={
                "id": "paper-upload",
                "created_at": "2026-03-18T00:00:00+00:00",
                **payload,
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_create_source_asset",
        lambda **_kwargs: asyncio.sleep(
            0,
            result={
                "id": "asset-upload",
                "task_id": "task-upload",
                "asset_type": "source_archive",
                "file_path": "D:/tmp/paper.zip",
                "file_name": "paper.zip",
                "mime_type": "application/zip",
                "created_at": "2026-03-18T00:00:00+00:00",
            },
        ),
    )
    monkeypatch.setattr(
        paper_service,
        "_update_paper",
        lambda paper_id, payload: asyncio.sleep(
            0,
            result={
                "id": paper_id,
                "source": "upload",
                "arxiv_id": None,
                "title": "paper",
                "authors": [],
                "categories": [],
                "community_status": "user_fallback",
                "trans_status": payload.get("trans_status", "not_started"),
                "created_at": "2026-03-18T00:00:00+00:00",
                "official_published_at": None,
                "community_selected_task_id": "task-upload",
                "community_selected_asset_id": payload["community_selected_asset_id"],
                "visibility": "public",
                "status": "published",
                "like_count": 0,
                "favorite_count": 0,
                "comment_count": 0,
                "view_count": 0,
                "download_count": 0,
            },
        ),
    )

    upload = UploadFile(filename="paper.zip", file=BytesIO(b"zip-bytes"))
    result = asyncio.run(
        paper_service.submit_uploaded_paper(
            file=upload,
            credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
        )
    )

    assert result["paper"]["community_status"] == "user_fallback"
    assert result["paper"]["trans_status"] == "not_started"
    assert result["task"]["task_id"] == "task-upload"
    assert result["admission_result"] == "created"


def test_submit_requires_authentication():
    try:
        asyncio.run(
            papers_route.submit_paper(
                request=SimpleNamespace(headers={}),
                credentials=None,
                current_user=None,
            )
        )
        raise AssertionError("expected authentication failure")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 401


def test_submit_returns_forbidden_when_paper_policy_denies(monkeypatch):
    monkeypatch.setattr(
        papers_route,
        "authorize",
        lambda *_args, **_kwargs: AuthorizationResult(
            allowed=False,
            reason="paper submit blocked by policy",
            resource="paper",
            action="submit",
        ),
    )

    class _JsonRequest:
        headers = {"content-type": "application/json"}

        async def json(self):
            return {"arxiv_id": "2501.12345"}

    try:
        asyncio.run(
            papers_route.submit_paper(
                request=_JsonRequest(),
                credentials=SimpleNamespace(credentials=_jwt_for("user-1")),
                current_user={"id": "user-1", "roles": ["user"]},
            )
        )
        raise AssertionError("expected policy failure")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403
