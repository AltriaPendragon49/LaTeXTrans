from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.services.latex.reconstruct import LatexConstructor
from backend.app.services.latex.utils import restore_sectioning_command_structure


def test_restore_sectioning_command_structure_accepts_starred_sections():
    original = (
        r"\section*{Acknowledgments}" + "\n\n" + "English ack."
        + "\n\n" + r"\section*{Funding}" + "\n\n" + "English funding."
    )
    translated = (
        r"\section*{致谢}" + "\n\n" + "中文致谢�?
        + "\n\n" + r"\section*{资助声明}" + "\n\n" + "未接受外部资助�?
    )

    restored = restore_sectioning_command_structure(original, translated)

    assert restored == translated
    assert r"\section*{致谢}" in restored
    assert "English ack." not in restored


def test_reconstruct_preserves_starred_tail_sections_in_target_language():
    sections = [
        {
            "section": "6+7+8",
            "content": (
                r"\section*{Acknowledgments}" + "\n\n" + "English ack."
                + "\n\n" + r"\section*{Funding}" + "\n\n" + "English funding."
            ),
            "trans_content": (
                r"\section*{致谢}" + "\n\n" + "中文致谢�?
                + "\n\n" + r"\section*{资助声明}" + "\n\n" + "未接受外部资助�?
            ),
            "translation_status": "translated",
        }
    ]

    merged = LatexConstructor(
        sections=sections,
        captions=[],
        envs=[],
        inputs=[],
        newcommands=[],
        output_latex_dir=".",
    )._merge_sections()

    assert r"\section*{致谢}" in merged
    assert r"\section*{资助声明}" in merged
    assert "English ack." not in merged
    assert "English funding." not in merged
