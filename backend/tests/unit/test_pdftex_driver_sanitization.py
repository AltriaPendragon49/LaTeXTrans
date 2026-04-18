from backend.app.services.latex.utils import _comment_out_pdflatex_commands


def test_comment_out_pdflatex_commands_rewrites_graphicx_pdftex_driver():
    source = "\\usepackage[pdftex]{graphicx}\n"

    sanitized = _comment_out_pdflatex_commands(source)

    assert "\\usepackage{graphicx}" in sanitized
    assert "[pdftex]" not in sanitized


def test_comment_out_pdflatex_commands_preserves_non_driver_graphicx_options():
    source = "\\usepackage[pdftex,draft]{graphicx}\n"

    sanitized = _comment_out_pdflatex_commands(source)

    assert "\\usepackage[draft]{graphicx}" in sanitized
    assert "pdftex" not in sanitized
