import asyncio
from types import SimpleNamespace

import httpx
from fastapi import Request, Response
from starlette.responses import StreamingResponse

from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    )


def _request_with_headers(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/preview/task-cos-preview/pdf",
            "headers": raw_headers,
            "query_string": b"",
            "scheme": "https",
            "server": ("testserver", 443),
            "client": ("127.0.0.1", 12345),
        }
    )


def test_proxy_remote_pdf_asset_forwards_range_and_overrides_disposition(monkeypatch):
    from backend.app.api.routes import download as download_route

    captured = {}

    class _FakeUpstream:
        status_code = 206
        headers = {
            "content-type": "application/pdf",
            "content-length": "12",
            "accept-ranges": "bytes",
            "content-range": "bytes 0-11/200",
            "content-disposition": "attachment; filename=cos.pdf",
        }

        async def aiter_bytes(self):
            yield b"%PDF-proxy"

        async def aclose(self):
            captured["upstream_closed"] = True

    class _FakeClient:
        def __init__(self, *, follow_redirects: bool, timeout: float):
            captured["follow_redirects"] = follow_redirects
            captured["timeout"] = timeout

        def build_request(self, method: str, url: str, headers: dict[str, str]):
            captured["request"] = {"method": method, "url": url, "headers": headers}
            return captured["request"]

        async def send(self, request, *, stream: bool):
            captured["stream"] = stream
            return _FakeUpstream()

        async def aclose(self):
            captured["client_closed"] = True

    monkeypatch.setattr(download_route.httpx, "AsyncClient", _FakeClient)

    async def _call():
        response = await download_route._proxy_remote_pdf_asset(
            "https://cos.example.com/paper.pdf?sign=abc",
            filename="paper.pdf",
            request=_request_with_headers({"range": "bytes=0-11"}),
            content_disposition="inline",
        )
        body = b"".join([chunk async for chunk in response.body_iterator])
        await response.background()
        return response, body

    response, body = asyncio.run(_call())

    assert isinstance(response, StreamingResponse)
    assert response.status_code == 206
    assert body == b"%PDF-proxy"
    assert captured["request"]["headers"]["Range"] == "bytes=0-11"
    assert captured["stream"] is True
    assert captured["upstream_closed"] is True
    assert captured["client_closed"] is True
    assert response.headers["content-disposition"] == 'inline; filename="paper.pdf"'
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == "bytes 0-11/200"


def test_preview_pdf_proxies_object_storage_asset_like_may_8(monkeypatch):
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

    async def _fake_proxy(
        url: str,
        *,
        filename: str,
        request: Request | None = None,
        content_disposition: str = "inline",
        media_type: str = "application/pdf",
    ):
        assert url == "https://cos.example.com/preview.pdf?sign=abc"
        assert filename == "preview_task-cos-preview.pdf"
        assert request is None
        assert content_disposition == "inline"
        assert media_type == "application/pdf"
        return Response(
            content=b"%PDF-preview",
            status_code=200,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="preview_task-cos-preview.pdf"',
            },
        )

    monkeypatch.setattr(download_route, "_proxy_remote_pdf_asset", _fake_proxy)

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/preview/task-cos-preview/pdf")

    response = asyncio.run(_call())

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'inline; filename="preview_task-cos-preview.pdf"'
