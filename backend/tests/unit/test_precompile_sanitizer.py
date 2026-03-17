import textwrap
from backend.app.services.latex.sanitizer import apply_precompile_sanitization

def test_comments_out_axessibility():
    tex = textwrap.dedent(r"""
        \documentclass{article}
        \usepackage{axessibility}
        \usepackage{graphicx}
        \begin{document}
        Hello
        \end{document}
    """)
    sanitized, warnings = apply_precompile_sanitization(tex)
    assert r"% \usepackage{axessibility}" in sanitized
    assert "Sanitized" in sanitized
    assert len(warnings) == 1
    assert "axessibility" in warnings[0]

def test_comments_out_multiple_packages():
    tex = textwrap.dedent(r"""
        \usepackage{accsupp, graphicx, pdfcomment}
    """)
    sanitized, warnings = apply_precompile_sanitization(tex)
    assert r"% \usepackage{accsupp, graphicx, pdfcomment}" in sanitized
    assert "accsupp" in warnings[0]
    assert "pdfcomment" in warnings[0]

def test_no_action_on_safe_packages():
    tex = textwrap.dedent(r"""
        \usepackage{graphicx}
        \usepackage[utf8]{inputenc}
    """)
    sanitized, warnings = apply_precompile_sanitization(tex)
    assert sanitized.strip() == tex.strip()
    assert len(warnings) == 0

def test_handles_options():
    tex = r"\usepackage[math]{axessibility}"
    sanitized, warnings = apply_precompile_sanitization(tex)
    assert r"% \usepackage[math]{axessibility}" in sanitized
    assert len(warnings) == 1
