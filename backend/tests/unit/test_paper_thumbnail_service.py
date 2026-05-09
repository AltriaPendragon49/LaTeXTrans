from pathlib import Path

import asyncio

from backend.app.services import paper_thumbnail_service


def test_ensure_pdf_thumbnail_bytes_reuses_cached_file(monkeypatch, tmp_path: Path):
    cache_dir = tmp_path / "paper_pdf_thumbnails"
    render_calls = {"count": 0}
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(
        paper_thumbnail_service,
        "_thumbnail_cache_dir",
        lambda: cache_dir,
    )
    monkeypatch.setattr(
        paper_thumbnail_service,
        "_render_pdf_thumbnail_bytes_from_path",
        lambda _path: render_calls.__setitem__("count", render_calls["count"] + 1) or b"png-bytes",
    )

    first = asyncio.run(
        paper_thumbnail_service.ensure_pdf_thumbnail(
            cache_seed="translated:paper-1:asset-1",
            file_path=str(pdf_path),
        )
    )
    second = asyncio.run(
        paper_thumbnail_service.ensure_pdf_thumbnail(
            cache_seed="translated:paper-1:asset-1",
            file_path=str(pdf_path),
        )
    )

    assert first == second
    assert first is not None
    assert first.exists()
    assert first.read_bytes() == b"png-bytes"
    assert render_calls["count"] == 1


def test_ensure_pdf_thumbnail_delivery_uploads_and_returns_signed_url(monkeypatch, tmp_path: Path):
    cache_dir = tmp_path / "paper_pdf_thumbnails"
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    uploads = []

    class _FakeBackend:
        def object_exists(self, *, object_key: str) -> bool:
            assert object_key.startswith("data/paper_pdf_thumbnails/")
            return False

        def put_file(self, *, local_path: Path, object_key: str, content_type: str | None, delete_local: bool):
            uploads.append(
                {
                    "local_path": local_path,
                    "object_key": object_key,
                    "content_type": content_type,
                    "delete_local": delete_local,
                }
            )
            return type("StoredRef", (), {"object_key": f"latextrans-prod/{object_key}"})()

        def build_download_url(self, *, object_key: str, expires_in: int, params=None):
            assert object_key.startswith("data/paper_pdf_thumbnails/")
            assert expires_in == 600
            assert params == {"response-content-type": "image/png"}
            return f"https://cos.example.com/{object_key}?sign=abc"

    monkeypatch.setattr(paper_thumbnail_service, "_thumbnail_cache_dir", lambda: cache_dir)
    monkeypatch.setattr(paper_thumbnail_service, "_storage_backend_is_object_store", lambda _backend: True)
    monkeypatch.setattr(paper_thumbnail_service, "_get_storage_backend", lambda: _FakeBackend())
    monkeypatch.setattr(paper_thumbnail_service, "_render_pdf_thumbnail_bytes_from_path", lambda _path: b"png-bytes")

    delivery = asyncio.run(
        paper_thumbnail_service.ensure_pdf_thumbnail_delivery(
            cache_seed="translated:paper-1:asset-1",
            file_path=str(pdf_path),
        )
    )

    assert delivery == {"signed_url": f"https://cos.example.com/{uploads[0]['object_key']}?sign=abc"}
    assert uploads[0]["content_type"] == "image/png"
    assert uploads[0]["delete_local"] is False
