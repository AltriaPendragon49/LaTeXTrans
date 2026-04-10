import asyncio
from io import BytesIO

import httpx

from backend.app.api.routes import papers as papers_route
from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def test_admin_can_start_upload_curation_batch(monkeypatch) -> None:
    async def fake_submit_admin_upload_curation_batch(  # type: ignore[no-untyped-def]
        *,
        files,
        current_user,
        source_language,
        target_language,
    ):
        assert len(files) == 2
        assert current_user["id"] == "admin-1"
        assert source_language == "en"
        assert target_language == "zh"
        return {
            "batch_id": "batch-upload-1",
            "status": "queued",
            "items": [
                {
                    "job_id": "job-upload-1",
                    "paper_id": "paper-upload-1",
                    "source_type": "upload",
                    "original_filename": "paper-a.zip",
                    "status": "queued",
                },
                {
                    "job_id": "job-upload-2",
                    "paper_id": "paper-upload-2",
                    "source_type": "upload",
                    "original_filename": "paper-b.zip",
                    "status": "queued",
                },
            ],
        }

    monkeypatch.setattr(
        "backend.app.services.paper_service.submit_admin_upload_curation_batch",
        fake_submit_admin_upload_curation_batch,
        raising=False,
    )
    app.dependency_overrides[papers_route.require_current_user] = lambda: {
        "id": "admin-1",
        "roles": ["admin"],
    }

    files = [
        ("file_a", ("paper-a.zip", BytesIO(b"zip-a"), "application/zip")),
        ("file_b", ("paper-b.zip", BytesIO(b"zip-b"), "application/zip")),
    ]

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/papers/admin/curation/uploads",
                data={"source_language": "en", "target_language": "zh"},
                files=files,
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["batch_id"] == "batch-upload-1"
    assert response.json()["items"][0]["original_filename"] == "paper-a.zip"
