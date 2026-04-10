from pathlib import Path

from backend.app.services.latex.parser import LatexParser


def test_merge_inputs_skips_directory_targets_instead_of_opening_them(tmp_path: Path) -> None:
    project_dir = tmp_path / "bundle"
    project_dir.mkdir()
    (project_dir / "figs" / "ablation").mkdir(parents=True)

    parser = LatexParser(dir=str(project_dir), output_dir=str(tmp_path / "out"))
    source = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\input{figs/ablation}\n"
        "Hello world.\n"
        "\\end{document}\n"
    )

    merged = parser._merge_inputs(source)

    assert "\\input{figs/ablation}" in merged
    assert "Hello world." in merged
