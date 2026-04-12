import asyncio
import os

from fastapi import Request
from fastapi.responses import Response

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
