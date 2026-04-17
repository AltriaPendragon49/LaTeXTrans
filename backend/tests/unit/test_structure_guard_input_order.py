import unittest
from pathlib import Path

from backend.app.services.latex.structure_guard import _collect_project_text


class TestStructureGuardInputOrder(unittest.TestCase):
    def test_collect_project_text_inlines_input_at_callsite(self):
        tmp_root = Path("backend/tests/.tmp_runtime/structure-guard-input-order")
        tmp_root.mkdir(parents=True, exist_ok=True)

        main_tex = tmp_root / "main.tex"
        appendix_tex = tmp_root / "06_appendix.tex"
        vtab_tex = tmp_root / "vtab_table.tex"

        main_tex.write_text(
            "\\documentclass{article}\n"
            "\\usepackage{tabularx}\n"
            "\\begin{document}\n"
            "\\input{06_appendix}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        appendix_tex.write_text(
            "\\section{Appendix}\n"
            "\\begin{table}[ht]\n"
            "\\centering\n"
            "\\caption{Breakdown}\n"
            "\\input{vtab_table}\n"
            "\\label{tab:vtab_tasks}\n"
            "\\end{table}\n",
            encoding="utf-8",
        )
        vtab_tex.write_text(
            "\\begin{tabularx}{\\linewidth}{CC}\n"
            "A & B \\\\\n"
            "\\end{tabularx}\n",
            encoding="utf-8",
        )

        assembled = _collect_project_text(main_tex)

        table_begin = assembled.index("\\begin{table}[ht]")
        tabular_begin = assembled.index("\\begin{tabularx}{\\linewidth}{CC}")
        tabular_end = assembled.index("\\end{tabularx}")
        table_end = assembled.index("\\end{table}")

        self.assertLess(table_begin, tabular_begin, assembled)
        self.assertLess(tabular_begin, tabular_end, assembled)
        self.assertLess(tabular_end, table_end, assembled)

    def test_collect_project_text_resolves_nested_relative_inputs_from_current_file(self):
        tmp_root = Path("backend/tests/.tmp_runtime/structure-guard-nested-relative")
        sections_dir = tmp_root / "sections"
        tables_dir = sections_dir / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)

        main_tex = tmp_root / "main.tex"
        appendix_tex = sections_dir / "appendix.tex"
        table_body_tex = tables_dir / "vtab_table.tex"

        main_tex.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\input{sections/appendix}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        appendix_tex.write_text(
            "\\section{Appendix}\n"
            "\\begin{table}\n"
            "\\input{tables/vtab_table}\n"
            "\\end{table}\n",
            encoding="utf-8",
        )
        table_body_tex.write_text(
            "\\begin{tabular}{cc}\n"
            "A & B \\\\\n"
            "\\end{tabular}\n",
            encoding="utf-8",
        )

        assembled = _collect_project_text(main_tex)

        self.assertIn("\\section{Appendix}", assembled)
        self.assertIn("\\begin{tabular}{cc}", assembled)
        self.assertNotIn("\\input{tables/vtab_table}", assembled)


if __name__ == "__main__":
    unittest.main()
