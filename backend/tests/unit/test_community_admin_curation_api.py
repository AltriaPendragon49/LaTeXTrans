import asyncio
from typing import Any, Dict

import httpx

from backend.app.api.routes import papers as papers_route
from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def test_non_admin_user_cannot_start_admin_arxiv_curation_batch() -> None:
    app.dependency_overrides[papers_route.require_current_user] = lambda: {
        "id": "usr-1",
        "roles": ["user"],
    }

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/papers/admin/curation/arxiv",
                json={
                    "arxiv_ids": ["2503.01010"],
                    "source_language": "en",
                    "target_language": "zh",
                },
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_can_start_admin_arxiv_curation_batch_and_receive_item_tracking(
    monkeypatch,
) -> None:
    async def fake_submit_admin_arxiv_curation_batch(  # type: ignore[no-untyped-def]
        *,
        arxiv_ids,
        current_user,
        source_language,
        target_language,
    ):
        assert arxiv_ids == ["2503.01010", "2503.01011"]
        assert current_user["id"] == "admin-1"
        assert source_language == "en"
        assert target_language == "zh"
        return {
            "batch_id": "batch-1",
            "status": "queued",
            "items": [
                {
                    "job_id": "job-1",
                    "paper_id": "paper-1",
                    "source_type": "arxiv",
                    "arxiv_id": "2503.01010",
                    "status": "queued",
                },
                {
                    "job_id": "job-2",
                    "paper_id": "paper-2",
                    "source_type": "arxiv",
                    "arxiv_id": "2503.01011",
                    "status": "queued",
                },
            ],
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.submit_admin_arxiv_curation_batch",
        fake_submit_admin_arxiv_curation_batch,
        raising=False,
    )
    app.dependency_overrides[papers_route.require_current_user] = lambda: {
        "id": "admin-1",
        "roles": ["admin"],
    }

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/papers/admin/curation/arxiv",
                json={
                    "arxiv_ids": ["2503.01010", "2503.01011"],
                    "source_language": "en",
                    "target_language": "zh",
                },
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {
        "batch_id": "batch-1",
        "status": "queued",
        "items": [
            {
                "job_id": "job-1",
                "paper_id": "paper-1",
                "source_type": "arxiv",
                "arxiv_id": "2503.01010",
                "status": "queued",
            },
            {
                "job_id": "job-2",
                "paper_id": "paper-2",
                "source_type": "arxiv",
                "arxiv_id": "2503.01011",
                "status": "queued",
            },
        ],
    }


def test_admin_can_fetch_curation_batch_status(monkeypatch) -> None:
    async def fake_get_admin_curation_batch(*, batch_id: str) -> Dict[str, Any]:
        assert batch_id == "batch-1"
        return {
            "batch_id": "batch-1",
            "status": "processing",
            "items": [
                {
                    "job_id": "job-1",
                    "paper_id": "paper-1",
                    "source_type": "arxiv",
                    "arxiv_id": "2503.01010",
                    "status": "metadata_preparing",
                },
                {
                    "job_id": "job-2",
                    "paper_id": "paper-2",
                    "source_type": "upload",
                    "original_filename": "paper.zip",
                    "status": "queued",
                },
            ],
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.get_admin_curation_batch",
        fake_get_admin_curation_batch,
        raising=False,
    )
    app.dependency_overrides[papers_route.require_current_user] = lambda: {
        "id": "admin-1",
        "roles": ["admin"],
    }

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/papers/admin/curation/batches/batch-1")

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["batch_id"] == "batch-1"
    assert response.json()["items"][0]["status"] == "metadata_preparing"
