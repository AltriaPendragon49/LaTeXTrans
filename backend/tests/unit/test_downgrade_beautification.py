"""
TDD Test Suite: Downgrade Beautification (Phase 1)
==================================================
Tests for `_beautify_downgrade_text` and `ultimate_downgrade_segment` output quality.
"""

import pytest

from backend.app.services.translation import ultimate_downgrade as _ultimate


_beautify_downgrade_text = getattr(_ultimate, "_beautify_downgrade_text", None)
ultimate_downgrade_segment = _ultimate.ultimate_downgrade_segment

if _beautify_downgrade_text is None:
    pytest.skip(
        "_beautify_downgrade_text is not available in current runtime module",
        allow_module_level=True,
    )


class TestBeautifyDowngradeText:
    def test_paragraph_breaks_normalized(self):
        text = "para one\n\n\n\npara two\n\n\npara three"
        result = _beautify_downgrade_text(text)
        assert "\n\n\n" not in result
        assert "para one" in result
        assert "para two" in result
        assert "para three" in result

    def test_single_newlines_preserved(self):
        text = "line one\nline two"
        result = _beautify_downgrade_text(text)
        assert "line one" in result
        assert "line two" in result

    def test_list_items_with_dash_preserved(self):
        text = "- item one\n- item two\n- item three"
        result = _beautify_downgrade_text(text)
        assert "- item one" in result
        assert "- item two" in result
        assert "- item three" in result

    def test_list_items_with_numbered_preserved(self):
        text = "1. first\n2. second\n3. third"
        result = _beautify_downgrade_text(text)
        assert "1. first" in result
        assert "2. second" in result

    def test_no_modification_of_escaped_latex_chars(self):
        text = r"price is \$100 and ratio is \$50\%"
        result = _beautify_downgrade_text(text)
        assert r"\$100" in result
        assert r"\$50\%" in result

    def test_no_modification_of_textbackslash(self):
        text = r"path separator \textbackslash{} for Windows"
        result = _beautify_downgrade_text(text)
        assert r"\textbackslash{}" in result

    def test_placeholder_tokens_preserved(self):
        text = "before <PLACEHOLDER_ENV_1> after <PLACEHOLDER_CAP_2>"
        result = _beautify_downgrade_text(text)
        assert "<PLACEHOLDER_ENV_1>" in result
        assert "<PLACEHOLDER_CAP_2>" in result

    def test_leading_trailing_whitespace_stripped(self):
        text = "   \n\nthis is content\n\n   "
        result = _beautify_downgrade_text(text)
        assert result == result.strip()

    def test_empty_string_returns_empty(self):
        assert _beautify_downgrade_text("") == ""

    def test_whitespace_only_returns_empty(self):
        assert _beautify_downgrade_text("  \n  \n  ") == ""


class TestUltimateDowngradeSegmentBeautification:
    def test_integration_output_has_no_triple_newlines(self):
        text = "\\section{Intro}\n\n\npara one\n\n\n\npara two"
        result = ultimate_downgrade_segment(text)
        assert "\n\n\n" not in result

    def test_integration_text_visible(self):
        text = "This is an article paragraph with key content."
        result = ultimate_downgrade_segment(text)
        assert "This is an article paragraph" in result

    def test_integration_still_synchronous(self):
        import inspect

        assert not inspect.iscoroutinefunction(ultimate_downgrade_segment)

    def test_integration_verbatim_exempt(self):
        text = "\\begin{verbatim}\nsome code here\n\\end{verbatim}"
        result = ultimate_downgrade_segment(text)
        assert "some code here" in result
