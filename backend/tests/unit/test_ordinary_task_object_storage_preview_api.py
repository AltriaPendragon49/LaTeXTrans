import asyncio
from types import SimpleNamespace

import httpx
from fastapi import Request, Response
from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    )


def test_preview_pdf_proxies_signed_url_in_object_storage_mode(monkeypatch):
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

    async def _fake_proxy(url: str, *, filename: str, media_type: str, request: Request | None = None):
        assert url == "https://cos.example.com/preview.pdf?sign=abc"
        assert filename == "preview_task-cos-preview.pdf"
        assert media_type == "application/pdf"
        assert request is not None
        assert request.headers.get("range") == "bytes=0-1023"
        return Response(
            content=b"%PDF-preview",
            status_code=206,
            media_type="application/pdf",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Range": "bytes 0-1023/2048",
                "Content-Disposition": 'inline; filename="preview_task-cos-preview.pdf"',
            },
        )

    monkeypatch.setattr(download_route, "_proxy_remote_asset", _fake_proxy)

    async def _call():
        async with _make_client() as client:
            return await client.get(
                "/api/preview/task-cos-preview/pdf",
                headers={"Range": "bytes=0-1023"},
            )

    response = asyncio.run(_call())

    assert response.status_code == 206
    assert response.headers["content-disposition"] == 'inline; filename="preview_task-cos-preview.pdf"'
    assert response.headers["accept-ranges"] == "bytes"
