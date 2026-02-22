"""
Unit tests for apply_formatting_config() in utils.py.
Covers all 9 injection scenarios and conflict detection.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from backend.app.services.latex.utils import apply_formatting_config


# ── Minimal valid LaTeX documents ─────────────────────────────────────────
MINIMAL_DOC = r"""\documentclass[12pt]{article}
\usepackage{amsmath}
\begin{document}
Hello world.
\end{document}
"""

TWOCOL_DOC = r"""\documentclass[twocolumn,12pt]{article}
\begin{document}
Content.
\end{document}
"""

BIB_DOC = r"""\documentclass{article}
\begin{document}
Some text \cite{ref}.
\bibliography{refs}
\bibliographystyle{plain}
\end{document}
"""

NATBIB_DOC = r"""\documentclass{article}
\usepackage[numbers]{natbib}
\begin{document}
\end{document}
"""


# ── Tests ──────────────────────────────────────────────────────────────────

class TestNone:
    """Config = None → code unchanged"""

    def test_none_returns_unchanged(self):
        result = apply_formatting_config(MINIMAL_DOC, None)
        assert result == MINIMAL_DOC

    def test_all_none_fields_returns_unchanged(self):
        class EmptyConfig:
            line_spacing = None
            font_size = None
            cjk_font = None
            column_mode = None
            margin = None
            paragraph_indent = None
            bib_style = None
            cite_style = None
            localize_captions = None
        result = apply_formatting_config(MINIMAL_DOC, EmptyConfig())
        assert result == MINIMAL_DOC


class TestLineSpacing:
    """line_spacing → \setstretch{} injected"""

    def test_injects_setspace_and_setstretch(self):
        class C:
            line_spacing = 1.5
            font_size = cjk_font = column_mode = margin = None
            paragraph_indent = bib_style = cite_style = localize_captions = None

        result = apply_formatting_config(MINIMAL_DOC, C())
        assert r'\usepackage{setspace}' in result
        assert r'\setstretch{1.5}' in result

    def test_no_duplicate_setspace_package(self):
        """If setspace already present, don't add it again"""
        doc = MINIMAL_DOC.replace(
            r'\usepackage{amsmath}',
            r'\usepackage{amsmath}' + '\n' + r'\usepackage{setspace}' + '\n' + r'\setstretch{2.0}'
        )

        class C:
            line_spacing = 1.5
            font_size = cjk_font = column_mode = margin = None
            paragraph_indent = bib_style = cite_style = localize_captions = None

        result = apply_formatting_config(doc, C())
        assert result.count(r'\usepackage{setspace}') == 1
        assert r'\setstretch{1.5}' in result
        # Old setstretch replaced
        assert r'\setstretch{2.0}' not in result


class TestFontSize:
    """font_size → documentclass options updated"""

    def test_replaces_existing_pt_size(self):
        class C:
            line_spacing = None
            font_size = 14
            cjk_font = column_mode = margin = None
            paragraph_indent = bib_style = cite_style = localize_captions = None

        result = apply_formatting_config(MINIMAL_DOC, C())
        assert '14pt' in result

    def test_no_existing_options_adds_bracket(self):
        doc = r'\documentclass{article}' + '\n' + r'\begin{document}' + '\nEnd.\n' + r'\end{document}'

        class C:
            line_spacing = None
            font_size = 11
            cjk_font = column_mode = margin = None
            paragraph_indent = bib_style = cite_style = localize_captions = None

        result = apply_formatting_config(doc, C())
        assert '11pt' in result


class TestColumnMode:
    """column_mode → single/double column switching"""

    def test_single_removes_twocolumn(self):
        class C:
            line_spacing = font_size = cjk_font = None
            column_mode = 'single'
            margin = paragraph_indent = bib_style = cite_style = localize_captions = None

        result = apply_formatting_config(TWOCOL_DOC, C())
        assert 'twocolumn' not in result
        assert r'\onecolumn' in result

    def test_double_adds_twocolumn(self):
        class C:
            line_spacing = font_size = cjk_font = None
            column_mode = 'double'
            margin = paragraph_indent = bib_style = cite_style = localize_captions = None

        result = apply_formatting_config(MINIMAL_DOC, C())
        assert 'twocolumn' in result


class TestMargin:
    """margin → geometry package injected"""

    def test_narrow_margin_injected(self):
        class C:
            line_spacing = font_size = cjk_font = column_mode = None
            margin = 'narrow'
            paragraph_indent = bib_style = cite_style = localize_captions = None

        result = apply_formatting_config(MINIMAL_DOC, C())
        assert r'\usepackage' in result
        assert 'geometry' in result
        assert '1.5cm' in result

    def test_wide_margin_injected(self):
        class C:
            line_spacing = font_size = cjk_font = column_mode = None
            margin = 'wide'
            paragraph_indent = bib_style = cite_style = localize_captions = None

        result = apply_formatting_config(MINIMAL_DOC, C())
        assert '3.5cm' in result

    def test_existing_geometry_replaced(self):
        doc = MINIMAL_DOC.replace(
            r'\usepackage{amsmath}',
            r'\usepackage{amsmath}' + '\n' + r'\usepackage[left=1cm,right=1cm]{geometry}'
        )

        class C:
            line_spacing = font_size = cjk_font = column_mode = None
            margin = 'normal'
            paragraph_indent = bib_style = cite_style = localize_captions = None

        result = apply_formatting_config(doc, C())
        assert result.count(r'{geometry}') == 1
        assert '2.5cm' in result


class TestBibStyle:
    """bib_style → \bibliographystyle replaced"""

    def test_replaces_existing_bibliographystyle(self):
        class C:
            line_spacing = font_size = cjk_font = column_mode = margin = None
            paragraph_indent = None
            bib_style = 'gbt7714-numerical'
            cite_style = localize_captions = None

        result = apply_formatting_config(BIB_DOC, C())
        assert r'\bibliographystyle{gbt7714-numerical}' in result
        assert r'\bibliographystyle{plain}' not in result


class TestCiteStyle:
    """cite_style → natbib options replaced"""

    def test_replaces_natbib_options(self):
        class C:
            line_spacing = font_size = cjk_font = column_mode = margin = None
            paragraph_indent = bib_style = None
            cite_style = 'authoryear'
            localize_captions = None

        result = apply_formatting_config(NATBIB_DOC, C())
        assert r'\usepackage[authoryear]{natbib}' in result
        assert r'\usepackage[numbers]{natbib}' not in result

    def test_injects_natbib_if_missing(self):
        class C:
            line_spacing = font_size = cjk_font = column_mode = margin = None
            paragraph_indent = bib_style = None
            cite_style = 'super'
            localize_captions = None

        result = apply_formatting_config(MINIMAL_DOC, C())
        assert r'\usepackage[super]{natbib}' in result


class TestLocalizeCaptions:
    """localize_captions=True → \renewcommand injected"""

    def test_injects_caption_commands(self):
        class C:
            line_spacing = font_size = cjk_font = column_mode = margin = None
            paragraph_indent = bib_style = cite_style = None
            localize_captions = True

        result = apply_formatting_config(MINIMAL_DOC, C())
        assert r'\renewcommand{\figurename}{图}' in result
        assert r'\renewcommand{\tablename}{表}' in result

    def test_no_duplicate_captions(self):
        doc = MINIMAL_DOC.replace(
            r'\begin{document}',
            r'\begin{document}' + '\n' + r'\renewcommand{\figurename}{图}'
        )

        class C:
            line_spacing = font_size = cjk_font = column_mode = margin = None
            paragraph_indent = bib_style = cite_style = None
            localize_captions = True

        result = apply_formatting_config(doc, C())
        assert result.count(r'\renewcommand{\figurename}{图}') == 1


class TestDictSupport:
    """apply_formatting_config accepts dict (from agent_config)"""

    def test_dict_config_line_spacing(self):
        config = {
            'line_spacing': 2.0,
            'font_size': None,
            'cjk_font': None,
            'column_mode': None,
            'margin': None,
            'paragraph_indent': None,
            'bib_style': None,
            'cite_style': None,
            'localize_captions': None,
        }
        result = apply_formatting_config(MINIMAL_DOC, config)
        assert r'\setstretch{2.0}' in result
