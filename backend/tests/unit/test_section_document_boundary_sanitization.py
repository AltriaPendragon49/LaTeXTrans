from backend.app.services.latex.reconstruct import LatexConstructor


def test_merge_sections_strips_document_boundary_leaks_even_without_structure_shell():
    sections = [
        {
            "section": "9",
            "content": "\\section{Method}\n\nOriginal text.",
            "trans_content": (
                "\\section{Methods}\n\n"
                "Translated body.\n"
                "\\end{document}\n"
                "More translated body."
            ),
            "contains_structure_shell": False,
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

    assert "\\begin{document}" not in merged
    assert "\\end{document}" not in merged
    assert "Translated body." in merged
    assert "More translated body." in merged


def test_merge_sections_preserves_owned_structure_shells_while_stripping_boundary_leaks():
    sections = [
        {
            "section": "10",
            "content": "\\section{Appendix}\n\nOriginal text.",
            "trans_content": (
                "\\begin{appendix}\n"
                "\\section{Appendix}\n\n"
                "Translated body.\n"
                "\\end{document}\n"
                "\\end{appendix}"
            ),
            "contains_structure_shell": True,
            "leading_structure_shell": "\\begin{appendix}\n",
            "trailing_structure_shell": "\n\\end{appendix}",
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

    assert merged.startswith("\\begin{appendix}\n\\section{Appendix}")
    assert merged.rstrip().endswith("\\end{appendix}")
    assert "\\end{document}" not in merged
