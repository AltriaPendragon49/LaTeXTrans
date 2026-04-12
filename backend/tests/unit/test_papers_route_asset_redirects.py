import asyncio
import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import papers as papers_route


def test_preview_translated_pdf_redirects_to_signed_url(monkeypatch):
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

    monkeypatch.setattr(
        papers_route.paper_service,
        "resolve_paper_translated_pdf_preview",
        _fake_preview,
    )

    response = asyncio.run(papers_route.preview_translated_paper_pdf("paper-1"))

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://cos.example.com/")


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
