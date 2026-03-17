"""
test_ultimate_downgrade.py
eliminate-silent-fallback — Unit tests for ultimate_downgrade_segment

Tests:
  1. Document-boundary isolation: \begin{document} / \end{document} must be stripped.
  2. Verbatim blocks exempt from downgrade.
  3. Basic natural language extraction and escaping.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.services.translation.ultimate_downgrade import (
    ultimate_downgrade_segment,
    ultimate_downgrade_section_segment,
    _extract_natural_language,
)


# ---------------------------------------------------------------------------
# Document boundary isolation (regression for structure_env_stack_mismatch)
# ---------------------------------------------------------------------------


class TestDocumentBoundaryIsolation:
    """Regression: document-boundary commands must never appear in chunk output."""

    def test_segment_strips_begin_document(self):
        chunk = r"\begin{document}\section{Intro} Introduction text."
        result = ultimate_downgrade_segment(chunk)
        assert r"\begin{document}" not in result
        assert "Intro" in result

    def test_segment_strips_end_document(self):
        chunk = r"Final paragraph.\end{document}"
        result = ultimate_downgrade_segment(chunk)
        assert r"\end{document}" not in result
        assert "Final" in result

    def test_segment_strips_both_boundaries(self):
        chunk = r"\begin{document}\maketitle Hello world.\end{document}"
        result = ultimate_downgrade_segment(chunk)
        assert r"\begin{document}" not in result
        assert r"\end{document}" not in result
        assert "Hello world" in result

    def test_extract_strips_begin_document_before_other_envs(self):
        """_extract_natural_language must strip document boundary in step 0."""
        text = r"\begin{document}\begin{itemize}item\end{itemize}\end{document}"
        result = _extract_natural_language(text)
        assert r"\begin{document}" not in result
        assert r"\end{document}" not in result
        assert "item" in result

    def test_segment_doc_boundary_only_returns_comment(self):
        """Chunk containing only document-boundary commands → safe comment."""
        chunk = r"\begin{document}\end{document}"
        result = ultimate_downgrade_segment(chunk)
        assert r"\begin{document}" not in result
        assert r"\end{document}" not in result
        # Must be a LaTeX comment line (starts with %)
        assert result.strip().startswith("%")


# ---------------------------------------------------------------------------
# Basic downgrade behaviour (sanity checks)
# ---------------------------------------------------------------------------


class TestUltimateDowngradeBasic:
    def test_empty_returns_comment(self):
        result = ultimate_downgrade_segment("")
        assert result.startswith("%")

    def test_whitespace_returns_comment(self):
        result = ultimate_downgrade_segment("   \n  ")
        assert result.startswith("%")

    def test_natural_language_preserved(self):
        chunk = r"\textbf{Important} result here."
        result = ultimate_downgrade_segment(chunk)
        assert "Important" in result
        assert "result here" in result

    def test_latex_special_chars_escaped(self):
        chunk = "100% success rate & great results"
        result = ultimate_downgrade_segment(chunk)
        assert r"\%" in result
        assert r"\&" in result

    def test_verbatim_block_exempt(self):
        chunk = r"\begin{verbatim}code here\end{verbatim}"
        result = ultimate_downgrade_segment(chunk)
        # Verbatim blocks return as-is
        assert "code here" in result

    def test_section_downgrade_preserves_section_wrapper_and_target_language_title(self):
        original = r"\subsection{Setup}" + "\n\n" + "For the purposes of this study, we consider ..."
        translated = r"\subsection{实验设置}" + "\n\n" + "在本研究中，我们考虑太平洋上的一个矩形区域。"

        result = ultimate_downgrade_section_segment(original, translated)

        assert r"\subsection{实验设置}" in result
        assert "For the purposes of this study" not in result
        assert "在本研究中，我们考虑太平洋上的一个矩形区域。" in result

    def test_section_downgrade_preserves_structure_shells(self):
        original = r"\section{Results}" + "\n\n" + "We begin by examining the left panel."
        translated = r"\section{结果}" + "\n\n" + "我们首先考察左侧面板。"

        result = ultimate_downgrade_section_segment(
            original,
            translated,
            leading_structure_shell="\\begin{snugshade*}\n",
            trailing_structure_shell="\n\\end{snugshade*}",
        )

        assert result.startswith("\\begin{snugshade*}\n\\section{结果}")
        assert result.endswith("\n\\end{snugshade*}")
        assert "We begin by examining the left panel." not in result

    def test_section_downgrade_preserves_internal_structure_tokens_in_body(self):
        original = (
            r"\section{Significance Statement}"
            + "\n\n"
            + "English lead."
            + " <PLACEHOLDER_ENV_3> "
            + r"\end{snugshade*}"
            + " "
            + r"\newpage"
            + " "
            + r"\noindent \lettrine[findent=2pt]{\fbox{\textbf{T}}}{ }"
            + " English tail."
        )
        translated = (
            r"\section{重要性声明}"
            + "\n\n"
            + "中文前言。"
            + " <PLACEHOLDER_ENV_3> "
            + r"\end{snugshade*}"
            + " "
            + r"\newpage"
            + " "
            + r"\noindent \lettrine[findent=2pt]{\fbox{\textbf{T}}}{ }"
            + " 中文尾段。"
        )

        result = ultimate_downgrade_section_segment(original, translated)

        assert r"\section{重要性声明}" in result
        assert "<PLACEHOLDER_ENV_3>" in result
        assert r"\end{snugshade*}" in result
        assert r"\newpage" in result
        assert r"\noindent" in result
        assert r"\lettrine[findent=2pt]{\fbox{\textbf{T}}}{ }" in result
        assert "English lead." not in result
        assert "English tail." not in result

    def test_section_downgrade_dedupes_trailing_shell_and_end_document(self):
        original = r"\subsection{Appendix Note}" + "\n\n" + "Original text."
        translated = (
            r"\subsection{闄勫綍璇存槑}"
            + "\n\n"
            + "缈昏瘧鍚庣殑姝ｆ枃銆?"
            + "\n\n<PLACEHOLDER_supplementary_end>\n\n\\end{document}\n"
        )

        result = ultimate_downgrade_section_segment(
            original,
            translated,
            trailing_structure_shell="<PLACEHOLDER_supplementary_end>\n\n\\end{document}",
        )

        assert result.count(r"\end{document}") == 1
        assert result.endswith("<PLACEHOLDER_supplementary_end>\n\n\\end{document}")

    def test_section_downgrade_preserves_math_refs_and_footnotes_without_literal_escaping(self):
        original = (
            r"\section{Introduction}"
            + "\n\n"
            + r"Inspired by GPT-2~\citep{radford2019}, we use $d_{model}$."
            + "\n\n"
            + r"\footnote{See~\autoref{fig:test}.}"
        )
        translated = (
            r"\section{引言}"
            + "\n\n"
            + r"受 GPT-2~\citep{radford2019} 启发，我们使用 $d_{model}$。"
            + "\n\n"
            + r"\footnote{见~\autoref{fig:test}。}"
        )

        result = ultimate_downgrade_section_segment(original, translated)

        assert r"GPT-2~\citep{radford2019}" in result
        assert r"$d_{model}$" in result
        assert r"\footnote{见~\autoref{fig:test}。}" in result
        assert r"\textasciitilde{}" not in result
        assert r"\textbackslash{}" not in result
        assert r"\$d\_{model}\$" not in result

    def test_section_downgrade_preserves_display_math_blocks(self):
        original = r"\section{Method}" + "\n\n" + r"Original $$\phi(A, B)=1$$ text."
        translated = r"\section{方法}" + "\n\n" + r"我们定义 $$\phi(A, B)=1$$ 作为目标。"

        result = ultimate_downgrade_section_segment(original, translated)

        assert r"$$\phi(A, B)=1$$" in result
        assert r"\$\$" not in result
