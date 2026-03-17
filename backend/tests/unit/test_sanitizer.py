"""
Unit tests for the Image Sanitizer module.

Tests use monkeypatching to avoid requiring Ghostscript or pdfinfo on CI.
"""
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.latex.sanitizer import (
    check_pdf_syntax_error,
    extract_failed_pdf_paths,
    patch_tex_includegraphics,
    sanitize_pdf,
    try_sanitize_images_in_errors,
)


# ---------------------------------------------------------------------------
# extract_failed_pdf_paths
# ---------------------------------------------------------------------------
class TestExtractFailedPdfPaths:
    def test_extracts_pdf_from_error_line(self, tmp_path):
        (tmp_path / "imgs").mkdir()
        pdf_file = tmp_path / "imgs" / "HOTA.pdf"
        pdf_file.write_bytes(b"fake")

        error_lines = [
            "./sec/5_experiments.tex:66: error:  (file imgs/HOTA.pdf) (pdf inclusion): reading image failed",
        ]
        result = extract_failed_pdf_paths(error_lines, tmp_path)
        assert len(result) == 1
        assert result[0] == pdf_file.resolve()

    def test_ignores_missing_files(self, tmp_path):
        error_lines = [
            "reading image failed",
            "(file imgs/MISSING.pdf)",
        ]
        result = extract_failed_pdf_paths(error_lines, tmp_path)
        assert result == []

    def test_no_reading_image_failed_returns_empty(self, tmp_path):
        (tmp_path / "figure.pdf").write_bytes(b"fake")
        error_lines = [
            "(file figure.pdf)",  # no "reading image failed" context
        ]
        result = extract_failed_pdf_paths(error_lines, tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# check_pdf_syntax_error
# ---------------------------------------------------------------------------
class TestCheckPdfSyntaxError:
    def test_returns_true_when_syntax_error_in_pdfinfo_output(self, tmp_path):
        fake = tmp_path / "bad.pdf"
        fake.write_bytes(b"not a real pdf")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Syntax Error: Illegal character ')'",
                stderr="",
            )
            assert check_pdf_syntax_error(fake) is True

    def test_returns_false_for_clean_pdf(self, tmp_path):
        fake = tmp_path / "good.pdf"
        fake.write_bytes(b"not a real pdf")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Title: ...")
            mock_run.return_value.stderr = ""
            assert check_pdf_syntax_error(fake) is False

    def test_returns_false_when_pdfinfo_not_found(self, tmp_path):
        fake = tmp_path / "any.pdf"
        fake.write_bytes(b"fake")
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="pdfinfo is required but not installed"):
                check_pdf_syntax_error(fake)


# ---------------------------------------------------------------------------
# sanitize_pdf
# ---------------------------------------------------------------------------
class TestSanitizePdf:
    def test_returns_sanitized_path_on_success(self, tmp_path):
        pdf = tmp_path / "HOTA.pdf"
        pdf.write_bytes(b"fake")
        sanitized = tmp_path / "HOTA.sanitized.pdf"

        def _fake_gs(args, **kwargs):
            # simulate ghostscript writing output file
            sanitized.write_bytes(b"clean pdf content")
            return MagicMock(returncode=0)

        with patch("backend.app.services.latex.sanitizer._find_ghostscript", return_value="gs"), \
             patch("subprocess.run", side_effect=_fake_gs):
            result = sanitize_pdf(pdf)
        assert result == sanitized
        assert result.exists()

    def test_returns_none_when_ghostscript_not_found(self, tmp_path):
        pdf = tmp_path / "HOTA.pdf"
        pdf.write_bytes(b"fake")
        with patch("backend.app.services.latex.sanitizer._find_ghostscript", return_value=None):
            result = sanitize_pdf(pdf)
        assert result is None

    def test_returns_none_when_gs_fails(self, tmp_path):
        import subprocess
        pdf = tmp_path / "HOTA.pdf"
        pdf.write_bytes(b"fake")
        with patch("backend.app.services.latex.sanitizer._find_ghostscript", return_value="gs"), \
             patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "gs")):
            result = sanitize_pdf(pdf)
        assert result is None


# ---------------------------------------------------------------------------
# patch_tex_includegraphics
# ---------------------------------------------------------------------------
class TestPatchTexIncludegraphics:
    def test_patches_simple_include(self, tmp_path):
        original = tmp_path / "HOTA.pdf"
        sanitized = tmp_path / "HOTA.sanitized.pdf"
        tex = r"\includegraphics[width=\linewidth]{imgs/HOTA.pdf}"
        patched, count = patch_tex_includegraphics(tex, original, sanitized)
        assert count == 1
        assert "HOTA.sanitized.pdf" in patched

    def test_does_not_patch_unrelated_file(self, tmp_path):
        original = tmp_path / "HOTA.pdf"
        sanitized = tmp_path / "HOTA.sanitized.pdf"
        tex = r"\includegraphics{other.pdf}"
        patched, count = patch_tex_includegraphics(tex, original, sanitized)
        assert count == 0
        assert patched == tex

    def test_patches_multiple_references(self, tmp_path):
        original = tmp_path / "FIG.pdf"
        sanitized = tmp_path / "FIG.sanitized.pdf"
        tex = textwrap.dedent("""\
            \\includegraphics{imgs/FIG.pdf}
            \\includegraphics[width=10cm]{imgs/FIG.pdf}
        """)
        patched, count = patch_tex_includegraphics(tex, original, sanitized)
        assert count == 2


# ---------------------------------------------------------------------------
# try_sanitize_images_in_errors (integration mock)
# ---------------------------------------------------------------------------
class TestTrySanitizeImagesInErrors:
    def test_end_to_end_sanitization(self, tmp_path):
        (tmp_path / "imgs").mkdir()
        pdf = tmp_path / "imgs" / "HOTA.pdf"
        pdf.write_bytes(b"broken")
        sanitized = tmp_path / "imgs" / "HOTA.sanitized.pdf"

        main_tex = tmp_path / "main.tex"
        main_tex.write_text(r"\includegraphics[width=\linewidth]{imgs/HOTA.pdf}", encoding="utf-8")
        
        error_lines = [
            "./sec/5_experiments.tex:66: error:  (file imgs/HOTA.pdf) (pdf inclusion): reading image failed",
        ]

        def _fake_run(args, **kwargs):
            sanitized.write_bytes(b"clean")
            return MagicMock(returncode=0, stdout="Syntax Error", stderr="")

        with patch("backend.app.services.latex.sanitizer._find_ghostscript", return_value="gs"), \
             patch("subprocess.run", side_effect=_fake_run):
            san_list, any_san, newly_set = try_sanitize_images_in_errors(error_lines, tmp_path)

        assert any_san is True
        assert len(san_list) == 1
        assert pdf.resolve() in newly_set

        # Verify file patching
        patched_tex = main_tex.read_text(encoding="utf-8")
        assert "HOTA.sanitized.pdf" in patched_tex

    def test_no_action_when_no_reading_image_failed(self, tmp_path):
        main_tex = tmp_path / "main.tex"
        main_tex.write_text(r"\includegraphics{fig.pdf}", encoding="utf-8")
        error_lines = ["! LaTeX Error: Missing \\begin{document}"]
        san_list, any_san, newly_set = try_sanitize_images_in_errors(error_lines, tmp_path)
        assert any_san is False
        assert newly_set == set()
        assert main_tex.read_text(encoding="utf-8") == r"\includegraphics{fig.pdf}"

    def test_skips_already_sanitized_pdfs(self, tmp_path):
        """Files listed in already_sanitized MUST NOT be re-processed."""
        (tmp_path / "imgs").mkdir()
        pdf = tmp_path / "imgs" / "HOTA.pdf"
        pdf.write_bytes(b"broken")

        error_lines = [
            "./main.tex:10: error:  (file imgs/HOTA.pdf) (pdf inclusion): reading image failed",
        ]
        # Pretend this PDF was already repaired in a previous round.
        san_list, any_san, newly_set = try_sanitize_images_in_errors(
            error_lines, tmp_path, already_sanitized={pdf.resolve()}
        )
        assert any_san is False
        assert san_list == []
        assert newly_set == set()

    def test_new_pdf_added_to_newly_sanitized_set(self, tmp_path):
        """A PDF not in already_sanitized must appear in the returned newly_sanitized set."""
        (tmp_path / "imgs").mkdir()
        pdf_a = tmp_path / "imgs" / "A.pdf"
        pdf_b = tmp_path / "imgs" / "B.pdf"
        pdf_a.write_bytes(b"broken")
        pdf_b.write_bytes(b"broken")
        san_b = tmp_path / "imgs" / "B.sanitized.pdf"

        error_lines = [
            "(file imgs/A.pdf) (pdf inclusion): reading image failed",
            "(file imgs/B.pdf) (pdf inclusion): reading image failed",
        ]

        def _fake_run(args, **kwargs):
            san_b.write_bytes(b"clean")
            return MagicMock(returncode=0, stdout="Syntax Error", stderr="")

        # A was already repaired; only B should be processed this round.
        with patch("backend.app.services.latex.sanitizer._find_ghostscript", return_value="gs"), \
             patch("subprocess.run", side_effect=_fake_run):
            san_list, any_san, newly_set = try_sanitize_images_in_errors(
                error_lines, tmp_path, already_sanitized={pdf_a.resolve()}
            )

        assert any_san is True
        assert pdf_b.resolve() in newly_set
        assert pdf_a.resolve() not in newly_set
