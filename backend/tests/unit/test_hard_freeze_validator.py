"""
Hard Freeze Validator �?TDD tests
==================================
Tests for:
  1. _validate_escaped_dollar_leak  �?detects \\$ leakage (C1)
  2. _revert_inputs tolerance        �?unmatched end tag must NOT crash
"""
import pytest

from backend.app.services.agents.validator_agent import (
    ValidatorAgent,
    ERROR_TYPE_C1,
)
from backend.app.services.latex.reconstruct import LatexConstructor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_validator() -> ValidatorAgent:
    return ValidatorAgent(
        config={
            "llm_config": {"model": "test", "base_url": "http://x", "api_key": "x"},
            "source_language": "en",
            "target_language": "zh",
        },
        project_dir="dummy",
        output_dir="dummy",
    )


# ---------------------------------------------------------------------------
# _validate_escaped_dollar_leak
# ---------------------------------------------------------------------------

class TestEscapedDollarLeak:

    def test_escaped_dollar_detected_as_c1(self):
        """
        Original has no \\$; translated has extra \\$ �?should be caught as C1.
        This mimics the OmniTrack$_{E2E}$ �?OmniTrack\\$_{E2E}\\$ failure.
        """
        validator = _make_validator()
        part = {
            "section": "5",
            "content": r"Performance of OmniTrack$_{E2E}$ is shown in the table.",
            "trans_content": r"表中显示�?OmniTrack\$_{E2E}\$ 的性能�?,
        }
        error = validator._validate_escaped_dollar_leak(part)
        assert error is not None, "Should detect the escaped dollar leak"
        assert "escaped_dollar_leak" in error

    def test_no_false_positive_on_legit_escaped_dollar(self):
        """
        Original already contains \\$; translated has the same amount �?no error.
        """
        validator = _make_validator()
        part = {
            "section": "3",
            "content": r"Price is \$100 per unit.",
            "trans_content": r"价格为每单位 \$100�?,
        }
        error = validator._validate_escaped_dollar_leak(part)
        assert error is None, "Should not flag \\$ that was already in the original"

    def test_no_false_positive_when_no_dollar_in_trans(self):
        """
        Translation contains no \\$ at all �?fast-exit, no error.
        """
        validator = _make_validator()
        part = {
            "section": "1",
            "content": r"We prove $x > 0$.",
            "trans_content": r"我们证明 x 大于 0�?,
        }
        error = validator._validate_escaped_dollar_leak(part)
        assert error is None

    def test_full_validate_classifies_as_c1(self):
        """
        When _validate_escaped_dollar_leak fires, classify_error should return C1.
        """
        validator = _make_validator()
        part = {
            "section": "5",
            "content": r"Value is $x + y$.",
            "trans_content": r"値は \$x + y\$ です�?,
        }
        report = validator._validate(part)
        assert report is not None
        assert report.get("error_type") == ERROR_TYPE_C1
        assert "escaped_dollar_leak" in report.get("math_error", "")

    def test_single_extra_escaped_dollar_flagged(self):
        """
        Translation adds one extra \\$ (asymmetric count) �?flagged.
        """
        validator = _make_validator()
        part = {
            "section": "2",
            "content": r"Equation $E = mc^2$ is famous.",
            "trans_content": r"方程�?E = mc\$^2 は有名です�?,
        }
        error = validator._validate_escaped_dollar_leak(part)
        assert error is not None
        assert "1 extra" in error

    def test_document_boundary_leak_classified_as_c2(self):
        validator = _make_validator()
        part = {
            "section": "8",
            "content": r"\section{Intro} Original body.",
            "trans_content": r"\section{寮曡█} Translated body. \end{document}",
            "leading_structure_shell": "",
            "trailing_structure_shell": "",
            "chunk_role": "normal",
        }

        report = validator._validate(part)

        assert report is not None
        assert report.get("error_type") == "C2"
        assert "document_boundary_leak" in report.get("math_error", "")


# ---------------------------------------------------------------------------
# _revert_inputs tolerance (Step 1 regression guard)
# ---------------------------------------------------------------------------

class TestRevertInputsTolerance:

    def test_unmatched_end_tag_does_not_crash_revert_inputs(self, tmp_path):
        """
        An orphaned end tag in the translated tex must NOT raise an exception.
        The constructor should skip it (with a warning) and continue.
        """
        import os

        # Create a stub main.tex so _revert_inputs can write the output
        main_tex = tmp_path / "main.tex"
        main_tex.write_text("\\documentclass{article}\n\\begin{document}\nFOO\n\\end{document}\n", encoding="utf-8")

        # Build inputs list with the begin/end tag format that _revert_inputs expects
        inputs = [
            {
                "begin": "<PLACEHOLDER_sec_1_begin>",
                "end": "<PLACEHOLDER_sec_1_end>",
                "path": "sec/intro",
                "command": r"\input{sec/intro}",
            }
        ]

        # tex has an orphaned end tag (begin tag missing �?LLM ate it)
        tex_with_orphan = (
            "仮の翻訳テキスト。\n"
            "<PLACEHOLDER_sec_1_end>\n"   # orphaned �?no matching begin
            "後続テキスト�?
        )

        constructor = LatexConstructor(
            sections=[],
            captions=[],
            envs=[],
            inputs=inputs,
            newcommands=[],
            output_latex_dir=str(tmp_path),
        )

        # Must NOT raise any exception
        try:
            constructor._revert_inputs(tex_with_orphan)
        except Exception as exc:
            pytest.fail(f"_revert_inputs raised an unexpected exception: {exc}")

