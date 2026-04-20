import asyncio
from pathlib import Path

from fpdf import FPDF
from PyPDF2 import PdfReader

from backend.app.services import paper_service


class _DownloadStubBackend:
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path

    def build_download_url(self, *, object_key: str, expires_in: int, params=None) -> None:
        del object_key, expires_in, params
        return None

    def download_file(self, *, object_key: str, local_path: Path) -> Path:
        del object_key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(self.source_path.read_bytes())
        return local_path


def _build_pdf_with_optional_leading_blank_page(
    pdf_path: Path,
    *,
    leading_blank: bool,
) -> None:
    pdf = FPDF()
    if leading_blank:
        pdf.add_page()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.multi_cell(0, 10, "Visual instruction tuning\nThis page contains meaningful translated content.")
    pdf.output(str(pdf_path))


def test_normalize_translated_pdf_trims_leading_blank_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "leading-blank.pdf"
    _build_pdf_with_optional_leading_blank_page(pdf_path, leading_blank=True)

    normalized_path = paper_service._normalize_translated_pdf_leading_blank_pages(pdf_path)

    assert normalized_path != pdf_path
    reader = PdfReader(str(normalized_path))
    assert len(reader.pages) == 1
    assert "Visual instruction tuning" in (reader.pages[0].extract_text() or "")


def test_normalize_translated_pdf_keeps_meaningful_first_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "normal.pdf"
    _build_pdf_with_optional_leading_blank_page(pdf_path, leading_blank=False)

    normalized_path = paper_service._normalize_translated_pdf_leading_blank_pages(pdf_path)

    assert normalized_path == pdf_path


def test_normalize_translated_pdf_uses_pdftotext_when_pypdf_is_unavailable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "leading-blank-no-pypdf.pdf"
    _build_pdf_with_optional_leading_blank_page(pdf_path, leading_blank=True)

    monkeypatch.setattr(paper_service, "PdfReader", None)
    monkeypatch.setattr(paper_service, "PdfWriter", None)

    normalized_path = paper_service._normalize_translated_pdf_leading_blank_pages(pdf_path)

    assert normalized_path != pdf_path
    reader = PdfReader(str(normalized_path))
    assert len(reader.pages) == 1
    assert "Visual instruction tuning" in (reader.pages[0].extract_text() or "")


def test_resolve_translated_pdf_preview_uses_normalized_pdf_for_blank_leading_page(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "preview-blank.pdf"
    _build_pdf_with_optional_leading_blank_page(pdf_path, leading_blank=True)

    async def fake_ensure_public_paper(_paper_id: str):
        return {"id": "paper-1", "visibility": "public", "status": "published"}

    async def fake_fetch_asset_map_for_paper(*, paper_id: str):
        assert paper_id == "paper-1"
        return {
            "translated_pdf": {
                "id": "asset-translated-1",
                "asset_type": "translated_pdf",
                "storage_backend": "local_disk",
                "file_path": str(pdf_path),
                "file_name": "translated.pdf",
                "mime_type": "application/pdf",
            }
        }

    monkeypatch.setattr(paper_service, "_ensure_public_paper", fake_ensure_public_paper)
    monkeypatch.setattr(paper_service, "_fetch_asset_map_for_paper", fake_fetch_asset_map_for_paper)

    payload = asyncio.run(paper_service.resolve_paper_translated_pdf_preview(paper_id="paper-1"))

    served_path = Path(payload["file_path"])
    assert served_path != pdf_path
    reader = PdfReader(str(served_path))
    assert len(reader.pages) == 1
    assert "Visual instruction tuning" in (reader.pages[0].extract_text() or "")


def test_resolve_translated_pdf_preview_materializes_and_normalizes_object_storage_asset(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "object-storage-blank.pdf"
    _build_pdf_with_optional_leading_blank_page(pdf_path, leading_blank=True)

    async def fake_ensure_public_paper(_paper_id: str):
        return {"id": "paper-1", "visibility": "public", "status": "published"}

    async def fake_fetch_asset_map_for_paper(*, paper_id: str):
        assert paper_id == "paper-1"
        return {
            "translated_pdf": {
                "id": "asset-translated-obj-1",
                "asset_type": "translated_pdf",
                "storage_backend": "object_storage",
                "file_path": "community/paper-1/translated.pdf",
                "file_name": "translated.pdf",
                "mime_type": "application/pdf",
            }
        }

    monkeypatch.setattr(paper_service, "_ensure_public_paper", fake_ensure_public_paper)
    monkeypatch.setattr(paper_service, "_fetch_asset_map_for_paper", fake_fetch_asset_map_for_paper)
    monkeypatch.setattr(
        paper_service,
        "_get_storage_backend",
        lambda: _DownloadStubBackend(pdf_path),
    )

    payload = asyncio.run(paper_service.resolve_paper_translated_pdf_preview(paper_id="paper-1"))

    assert "signed_url" not in payload
    served_path = Path(payload["file_path"])
    assert served_path != pdf_path
    reader = PdfReader(str(served_path))
    assert len(reader.pages) == 1
    assert "Visual instruction tuning" in (reader.pages[0].extract_text() or "")
