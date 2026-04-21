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


def test_admin_can_list_curation_jobs(monkeypatch) -> None:
    async def fake_list_admin_curation_jobs(*, status_filter: str | None, search: str | None) -> Dict[str, Any]:
        assert status_filter == "failed"
        assert search == "2312.00752"
        return {
            "items": [
                {
                    "job_id": "job-1",
                    "batch_id": "batch-1",
                    "paper_id": None,
                    "published_paper_id": None,
                    "task_id": "task-1",
                    "source_type": "arxiv",
                    "arxiv_id": "2312.00752",
                    "status": "failed",
                    "terminal_task_status": "failed_compilation",
                    "terminal_reason": "task_execution_timeout",
                    "timeout_reason": "execution_timeout",
                    "error": "compile failed",
                    "failed_artifact_path": "failed_tasks/task-1",
                    "created_at": "2026-04-19T00:00:00Z",
                    "updated_at": "2026-04-19T00:05:00Z",
                }
            ],
            "total": 1,
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.list_admin_curation_jobs",
        fake_list_admin_curation_jobs,
        raising=False,
    )
    app.dependency_overrides[papers_route.require_current_user] = lambda: {
        "id": "admin-1",
        "roles": ["admin"],
    }

    async def _call():
        async with _make_client() as client:
            return await client.get(
                "/api/papers/admin/curation/jobs",
                params={"status": "failed", "q": "2312.00752"},
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["job_id"] == "job-1"
    assert payload["items"][0]["terminal_task_status"] == "failed_compilation"
    assert payload["items"][0]["terminal_reason"] == "task_execution_timeout"
    assert payload["items"][0]["timeout_reason"] == "execution_timeout"


def test_admin_list_curation_jobs_treats_all_status_as_unfiltered(monkeypatch) -> None:
    async def fake_list_admin_curation_jobs(*, status_filter: str | None, search: str | None) -> Dict[str, Any]:
        assert status_filter is None
        assert search is None
        return {
            "items": [],
            "total": 0,
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.list_admin_curation_jobs",
        fake_list_admin_curation_jobs,
        raising=False,
    )
    app.dependency_overrides[papers_route.require_current_user] = lambda: {
        "id": "admin-1",
        "roles": ["admin"],
    }

    async def _call():
        async with _make_client() as client:
            return await client.get(
                "/api/papers/admin/curation/jobs",
                params={"status": "all", "q": ""},
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_admin_list_curation_jobs_preserves_processing_filter(monkeypatch) -> None:
    async def fake_list_admin_curation_jobs(*, status_filter: str | None, search: str | None) -> Dict[str, Any]:
        assert status_filter == "processing"
        assert search is None
        return {
            "items": [],
            "total": 0,
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.list_admin_curation_jobs",
        fake_list_admin_curation_jobs,
        raising=False,
    )
    app.dependency_overrides[papers_route.require_current_user] = lambda: {
        "id": "admin-1",
        "roles": ["admin"],
    }

    async def _call():
        async with _make_client() as client:
            return await client.get(
                "/api/papers/admin/curation/jobs",
                params={"status": "processing", "q": ""},
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_admin_can_delete_retained_failed_curation_job(monkeypatch) -> None:
    async def fake_delete_admin_curation_job(*, job_id: str, current_user) -> Dict[str, Any]:
        assert job_id == "job-1"
        assert current_user["id"] == "admin-1"
        return {
            "job_id": "job-1",
            "paper_id": None,
            "status": "completed",
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.delete_admin_curation_job",
        fake_delete_admin_curation_job,
        raising=False,
    )
    app.dependency_overrides[papers_route.require_current_user] = lambda: {
        "id": "admin-1",
        "roles": ["admin"],
    }

    async def _call():
        async with _make_client() as client:
            return await client.delete("/api/papers/admin/curation/jobs/job-1")

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-1",
        "paper_id": None,
        "status": "completed",
    }


def test_admin_can_batch_delete_curation_jobs(monkeypatch) -> None:
    async def fake_batch_delete_admin_curation_jobs(*, job_ids, current_user) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        assert job_ids == ["job-1", "job-2"]
        assert current_user["id"] == "admin-1"
        return {
            "deleted": [
                {"job_id": "job-1", "paper_id": None, "status": "failed"},
                {"job_id": "job-2", "paper_id": "paper-2", "status": "completed"},
            ],
            "failed": [],
            "deleted_count": 2,
            "failed_count": 0,
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.batch_delete_admin_curation_jobs",
        fake_batch_delete_admin_curation_jobs,
        raising=False,
    )
    app.dependency_overrides[papers_route.require_current_user] = lambda: {
        "id": "admin-1",
        "roles": ["admin"],
    }

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/papers/admin/curation/jobs/batch-delete",
                json={"job_ids": ["job-1", "job-2"]},
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2
    assert response.json()["failed_count"] == 0
    assert response.json()["deleted"][1]["paper_id"] == "paper-2"
