from __future__ import annotations

from backend.app.services.translation.ultimate_downgrade import (
    ultimate_downgrade_section_segment,
)


def test_section_downgrade_preserves_label_boundaries_and_paragraph_macros():
    original = (
        "\\section{Training details}\n"
        "\\label{sec:training}\n\n"
        "\\PAR{Pose optimization}\n"
        "Original paragraph.\n\n"
        "\\PARR{Training runtime}\n"
        "Original runtime paragraph."
    )
    translated = (
        "\\section{训练与定位细节}\n"
        "\\label{sec:training}\n\n"
        "\\PAR{位姿优化}\n"
        "给定一张位姿未知的查询图像，我们首先估计初始位姿。\n\n"
        "\\PARR{训练开销}\n"
        "所有模型均在单块 GPU 上完成训练。"
    )

    result = ultimate_downgrade_section_segment(original, translated)

    assert "\\label{sec:training}\n\n\\PAR{位姿优化}" in result
    assert "\\PAR{位姿优化}\n" in result
    assert "\\PARR{训练开销}\n" in result
    assert "Original paragraph." not in result
    assert "Original runtime paragraph." not in result


def test_section_downgrade_keeps_blank_lines_around_preserved_commands():
    original = (
        "\\section{Related work}\n"
        "\\label{sec:related}\n\n"
        "Original intro.\n\n"
        "\\PAR{Privacy-preserving visual localization}\n"
        "Original body."
    )
    translated = (
        "\\section{相关工作}\n"
        "\\label{sec:related}\n\n"
        "这是导语段落。\n\n"
        "\\PAR{隐私保护视觉定位}\n"
        "这是正文段落。"
    )

    result = ultimate_downgrade_section_segment(original, translated)

    assert "\\label{sec:related}\n\n这是导语段落。" in result
    assert "这是导语段落。\n\n\\PAR{隐私保护视觉定位}" in result


def test_section_downgrade_preserves_bibliography_and_semantic_custom_macros():
    original = (
        "\\section{Conclusion}\n\n"
        "Our \\PPNeSF{} outperforms \\ZipNeRFwoRGB{} and \\RGBPPNeSF.\n\n"
        "\\bibliography{main}\n"
        "\\bibliographystyle{ieeenat_fullname}\n"
        "\\appendix"
    )
    translated = (
        "\\section{结论}\n\n"
        "我们的 \\PPNeSF{} 优于 \\ZipNeRFwoRGB{} 和 \\RGBPPNeSF。\n\n"
        "\\bibliography{main}\n"
        "\\bibliographystyle{ieeenat_fullname}\n"
        "\\appendix"
    )

    result = ultimate_downgrade_section_segment(original, translated)

    assert "\\PPNeSF{}" in result
    assert "\\ZipNeRFwoRGB{}" in result
    assert "\\RGBPPNeSF" in result
    assert "\\bibliography{main}" in result
    assert "\\bibliographystyle{ieeenat_fullname}" in result
    assert "\\appendix" in result
    assert "Our " not in result


def test_section_downgrade_preserves_maketitle_in_first_body_chunk():
    original = (
        "\\begin{document}\n"
        "\\maketitle\n\n"
        "\\section{Introduction}\n\n"
        "Original body."
    )
    translated = (
        "\\begin{document}\n"
        "\\section{引言}\n\n"
        "中文正文。"
    )

    result = ultimate_downgrade_section_segment(
        original,
        translated,
        leading_structure_shell="\\begin{document}\n",
    )

    assert "\\begin{document}\n\\maketitle\n\n\\section{引言}" in result
    assert "Original body." not in result
