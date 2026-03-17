from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.services.latex.reconstruct import LatexConstructor


def test_merge_sections_does_not_revert_fallback_section_to_source():
    original = r"\section{Discussion}" + "\n\n" + "The Reef-building larvae show substantial variation."
    translated = (
        "% [LaTeX-Trans: ultimate downgrade applied — chunk: 4]\n"
        "讨论\n\n"
        "造礁珊瑚幼虫表现出显著的差异。"
    )
    sections = [
        {
            "section": "4",
            "content": original,
            "trans_content": translated,
            "translation_status": "final_target_language_fallback_applied",
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

    assert r"\section{讨论}" in merged
    assert "造礁珊瑚幼虫表现出显著的差异。" in merged
    assert "The Reef-building larvae show substantial variation." not in merged
