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
