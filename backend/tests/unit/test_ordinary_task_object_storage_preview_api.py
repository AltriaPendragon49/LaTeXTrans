import asyncio
from types import SimpleNamespace

import httpx
from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    )


def test_preview_pdf_redirects_to_signed_url_in_object_storage_mode(monkeypatch):
    from backend.app.api.routes import download as download_route

    class _FakeTaskManager:
        def get_task(self, task_id: str):
            assert task_id == "task-cos-preview"
            return {
                "task_id": task_id,
                "status": "completed",
                "output_path": "data/outputs/task-cos-preview",
            }

    monkeypatch.setattr(download_route, "task_manager", _FakeTaskManager())
    monkeypatch.setattr(download_route, "settings", SimpleNamespace(storage_backend_mode="cos"))
    monkeypatch.setattr(
        download_route.task_artifact_storage,
        "build_task_output_download_url",
        lambda output_path, asset_name, **kwargs: "https://cos.example.com/preview.pdf?sign=abc"
        if (output_path, asset_name) == ("data/outputs/task-cos-preview", "translated_pdf")
        else None,
    )

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/preview/task-cos-preview/pdf")

    response = asyncio.run(_call())

    assert response.status_code == 307
    assert response.headers["location"] == "https://cos.example.com/preview.pdf?sign=abc"
