import asyncio
import os
from pathlib import Path

from fastapi import Request
from fastapi.responses import Response
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import papers as papers_route


def _request_with_headers(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/papers/paper-1/translated-pdf",
            "headers": raw_headers,
            "query_string": b"",
            "scheme": "https",
            "server": ("testserver", 443),
            "client": ("127.0.0.1", 12345),
        }
    )


def test_preview_translated_pdf_streams_object_storage_pdf_inline(monkeypatch):
    async def _fake_preview(*, paper_id: str):
        assert paper_id == "paper-1"
        return {
            "paper_id": paper_id,
            "asset": {
                "id": "asset-pdf",
                "file_name": "translated.pdf",
                "mime_type": "application/pdf",
            },
            "signed_url": "https://cos.example.com/paper.pdf?sign=abc",
        }

    async def _fake_proxy(*, url: str, filename: str, request: Request):
        assert url == "https://cos.example.com/paper.pdf?sign=abc"
        assert filename == "translated.pdf"
        assert request.headers.get("range") == "bytes=0-1023"
        return Response(
            content=b"%PDF-1.4\n%mock\n",
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="translated.pdf"',
                "Accept-Ranges": "bytes",
            },
        )

    monkeypatch.setattr(
        papers_route.paper_service,
        "resolve_paper_translated_pdf_preview",
        _fake_preview,
    )
    monkeypatch.setattr(papers_route, "_proxy_remote_pdf_preview", _fake_proxy)

    response = asyncio.run(
        papers_route.preview_translated_paper_pdf(
            "paper-1",
            _request_with_headers({"range": "bytes=0-1023"}),
        )
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'inline; filename="translated.pdf"'
    assert response.headers["accept-ranges"] == "bytes"


def test_proxy_remote_pdf_preview_streams_range_response(monkeypatch):
    class _FakeUpstreamResponse:
        status_code = 206
        headers = {
            "content-type": "application/pdf",
            "accept-ranges": "bytes",
            "content-range": "bytes 0-8/9",
            "content-length": "9",
            "etag": '"etag-1"',
        }

        async def aiter_bytes(self):
            yield b"%PDF"
            yield b"-mock"

        async def aclose(self):
            return None

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            self.request_headers = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def build_request(self, method: str, url: str, headers: dict[str, str]):
            self.request_headers = headers
            return {"method": method, "url": url}

        async def send(self, request, stream: bool = False):
            assert request["method"] == "GET"
            assert request["url"] == "https://cos.example.com/paper.pdf?sign=abc"
            assert stream is True
            assert self.request_headers == {
                "Range": "bytes=0-8",
                "User-Agent": "LaTeXTrans-Preview/1.0",
            }
            return _FakeUpstreamResponse()

        async def aclose(self):
            return None

    monkeypatch.setattr(papers_route.httpx, "AsyncClient", _FakeClient)

    response = asyncio.run(
        papers_route._proxy_remote_pdf_preview(
            url="https://cos.example.com/paper.pdf?sign=abc",
            filename="translated.pdf",
            request=_request_with_headers({"range": "bytes=0-8"}),
        )
    )

    assert isinstance(response, StreamingResponse)
    assert isinstance(response.background, BackgroundTask)
    assert response.status_code == 206
    assert response.headers["content-disposition"] == 'inline; filename="translated.pdf"'
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == "bytes 0-8/9"


def test_download_paper_redirects_to_signed_url(monkeypatch):
    async def _fake_download(*, paper_id: str, token: str):
        assert paper_id == "paper-1"
        assert token == "download-token"
        return {
            "paper_id": paper_id,
            "asset": {
                "id": "asset-pdf",
                "file_name": "translated.pdf",
                "mime_type": "application/pdf",
            },
            "signed_url": "https://cos.example.com/paper.pdf?sign=abc",
        }

    monkeypatch.setattr(
        papers_route.paper_service,
        "resolve_paper_download",
        _fake_download,
    )

    response = asyncio.run(papers_route.download_paper("paper-1", token="download-token"))

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://cos.example.com/")


def test_preview_source_pdf_serves_local_range_requests(monkeypatch, tmp_path: Path):
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nmock-source-payload")

    async def _fake_preview(*, paper_id: str):
        assert paper_id == "paper-1"
        return {
            "paper_id": paper_id,
            "file_path": str(pdf_path),
            "filename": "source.pdf",
        }

    monkeypatch.setattr(
        papers_route.paper_service,
        "resolve_paper_source_pdf_preview",
        _fake_preview,
    )

    response = asyncio.run(
        papers_route.preview_source_paper_pdf(
            "paper-1",
            _request_with_headers({"range": "bytes=0-8"}),
        )
    )

    assert isinstance(response, StreamingResponse)
    assert response.status_code == 206
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == f"bytes 0-8/{pdf_path.stat().st_size}"
    assert response.headers["content-disposition"] == 'inline; filename="source.pdf"'


def test_preview_translated_pdf_serves_local_range_requests(monkeypatch, tmp_path: Path):
    pdf_path = tmp_path / "translated.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nmock-translated-payload")

    async def _fake_preview(*, paper_id: str):
        assert paper_id == "paper-1"
        return {
            "paper_id": paper_id,
            "asset": {
                "id": "asset-pdf",
                "file_name": "translated.pdf",
                "mime_type": "application/pdf",
            },
            "file_path": str(pdf_path),
        }

    monkeypatch.setattr(
        papers_route.paper_service,
        "resolve_paper_translated_pdf_preview",
        _fake_preview,
    )

    response = asyncio.run(
        papers_route.preview_translated_paper_pdf(
            "paper-1",
            _request_with_headers({"range": "bytes=0-7"}),
        )
    )

    assert isinstance(response, StreamingResponse)
    assert response.status_code == 206
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == f"bytes 0-7/{pdf_path.stat().st_size}"
    assert response.headers["content-disposition"] == 'inline; filename="translated.pdf"'
