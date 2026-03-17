"""
Task 4: Tiered Compilation — TDD Tests
========================================
Tests verifying that compile_with_intelligent_fallback follows Stage 0/1/2
tiered strategy where Stage 0 (pristine) attempts compilation without any
user source modification.

Specifically, Stage 0 must NOT call:
  - _upgrade_outdated_cls_files
  - _apply_engine_compat_shims (shim injection into user .tex file)
  - _fallback_biblatex_to_thebibliography
"""
from pathlib import Path

from backend.app.services.latex import compiler


def _write_minimal_tex(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_minimal_cls(path: Path) -> None:
    """Write a minimal, harmless bundled .cls file to simulate IEEEtran.cls etc."""
    path.write_text(
        r"% Minimal bundled cls file (simulated bundled IEEEtran.cls)" + "\n"
        r"\ProvidesClass{minimal}[2023/01/01]" + "\n"
        r"\LoadClass{article}" + "\n",
        encoding="utf-8",
    )


def _fake_success_result(tex_file: str, output_dir: str) -> compiler.CompilationResult:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(tex_file).stem
    pdf_path = out_dir / f"{stem}.pdf"
    log_path = out_dir / f"{stem}.log"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    log_path.write_text("", encoding="utf-8")
    return compiler.CompilationResult(
        success=True,
        pdf_path=str(pdf_path),
        log_path=str(log_path),
        error_count=0,
        errors=[],
    )


def test_stage0_pristine_does_not_call_upgrade_cls_files(monkeypatch, tmp_path):
    """
    Stage 0 (pristine) compilation must NOT delete or replace user .cls files.
    `_upgrade_outdated_cls_files` must NOT be called on a Stage 0 attempt.
    """
    main_tex = tmp_path / "project" / "main.tex"
    bundled_cls = tmp_path / "project" / "IEEEtran.cls"
    out_dir = tmp_path / "out"

    _write_minimal_tex(main_tex, r"\documentclass{IEEEtran}" + "\n"
                       r"\begin{document}Hello.\end{document}")
    _write_minimal_cls(bundled_cls)

    upgrade_call_count = {"count": 0}

    def fake_upgrade_cls(tex_dir: str) -> None:
        upgrade_call_count["count"] += 1

    def fake_compile_latex(tex_file, output_dir, engine="pdflatex", max_runs=2):
        return _fake_success_result(tex_file, output_dir)

    monkeypatch.setattr(compiler, "_upgrade_outdated_cls_files", fake_upgrade_cls)
    monkeypatch.setattr(compiler, "compile_latex", fake_compile_latex)

    result = compiler.compile_with_intelligent_fallback(
        tex_file=str(main_tex),
        output_dir=str(out_dir),
        preferred_order=["pdflatex"],
    )

    assert result["status"] == "completed", f"Expected completed, got: {result['status']}"
    # Stage 0 must NOT have called _upgrade_outdated_cls_files
    assert upgrade_call_count["count"] == 0, (
        f"_upgrade_outdated_cls_files was called {upgrade_call_count['count']} times in Stage 0. "
        "Stage 0 must be pristine (no source modification)."
    )
    # The bundled .cls file must still exist
    assert bundled_cls.exists(), "Bundled .cls file was deleted during Stage 0!"


def test_stage0_pristine_does_not_shim_tex_file(monkeypatch, tmp_path):
    """
    Stage 0 compilation must NOT apply any engine compatibility shims to the user's .tex file.
    The .tex file content must remain identical after Stage 0.
    """
    main_tex = tmp_path / "project_shim" / "main.tex"
    out_dir = tmp_path / "out_shim"
    original_content = (
        r"\documentclass{article}" + "\n"
        r"\usepackage{hwemoji}" + "\n"
        r"\begin{document}Hello.\end{document}"
    )
    _write_minimal_tex(main_tex, original_content)

    def fake_compile_latex(tex_file, output_dir, engine="pdflatex", max_runs=2):
        return _fake_success_result(tex_file, output_dir)

    monkeypatch.setattr(compiler, "_upgrade_outdated_cls_files", lambda _: None)
    monkeypatch.setattr(compiler, "compile_latex", fake_compile_latex)

    compiler.compile_with_intelligent_fallback(
        tex_file=str(main_tex),
        output_dir=str(out_dir),
        preferred_order=["xelatex"],  # hwemoji shim exists for xelatex
    )

    # Stage 0 must leave the .tex content unchanged
    actual_content = main_tex.read_text(encoding="utf-8")
    assert actual_content == original_content, (
        f"Stage 0 modified the .tex file content!\n"
        f"Expected:\n{original_content}\n\n"
        f"Actual:\n{actual_content}"
    )


def test_stage1_shimmed_applied_after_stage0_fails(monkeypatch, tmp_path):
    """
    If Stage 0 (pristine) fails, Stage 1 (shimmed) should be attempted.
    Stage 1 applies engine compatibility shims, but still must NOT delete .cls files.
    """
    main_tex = tmp_path / "project_stage1" / "main.tex"
    bundled_cls = tmp_path / "project_stage1" / "IEEEtran.cls"
    out_dir = tmp_path / "out_stage1"

    _write_minimal_tex(main_tex, r"\documentclass{IEEEtran}" + "\n"
                       r"\usepackage{hwemoji}" + "\n"
                       r"\begin{document}Hello.\end{document}")
    _write_minimal_cls(bundled_cls)

    call_log = {"stage0_called": False, "stage1_called": False}

    def fake_compile_latex(tex_file, output_dir, engine="pdflatex", max_runs=2):
        # Check if shim has been applied to determine which stage we're in
        content = Path(tex_file).read_text(encoding="utf-8")
        shim_marker = "% disabled by engine compatibility shim"
        if shim_marker in content:
            call_log["stage1_called"] = True
            return _fake_success_result(tex_file, output_dir)
        else:
            call_log["stage0_called"] = True
            # Stage 0 fails
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            log_path = out / f"{Path(tex_file).stem}.log"
            log_path.write_text("! Undefined control sequence.", encoding="utf-8")
            return compiler.CompilationResult(
                success=False,
                pdf_path=None,
                log_path=str(log_path),
                error_count=1,
                errors=["Undefined control sequence"],
            )

    monkeypatch.setattr(compiler, "_upgrade_outdated_cls_files", lambda _: None)
    monkeypatch.setattr(compiler, "compile_latex", fake_compile_latex)

    result = compiler.compile_with_intelligent_fallback(
        tex_file=str(main_tex),
        output_dir=str(out_dir),
        preferred_order=["xelatex"],
    )

    assert call_log["stage0_called"], "Stage 0 must have been attempted first"
    assert call_log["stage1_called"], "Stage 1 (shimmed) must be attempted after Stage 0 fails"
    assert result["status"] == "completed", f"Expected completed, got: {result['status']}"
    # Even after Stage 1, the bundled .cls file must remain
    assert bundled_cls.exists(), "Bundled .cls file was deleted during Stage 1!"


def test_prepare_bibliography_inputs_skips_bibtex_for_manual_bbl_and_restores_prebuilt_bbl(tmp_path):
    project_dir = tmp_path / "project_manual_bbl"
    main_tex = project_dir / "main.tex"
    main_bib = project_dir / "main.bib"
    main_bbl = project_dir / "main.bbl"
    main_bbl_tex = project_dir / "main.bbl.tex"

    _write_minimal_tex(
        main_tex,
        r"\documentclass{article}" + "\n"
        r"\begin{document}" + "\n"
        r"\input{main.bbl}" + "\n"
        r"\end{document}" + "\n",
    )
    main_bib.write_text("% bibliography database exists\n", encoding="utf-8")
    main_bbl.write_text("", encoding="utf-8")
    main_bbl_tex.write_text(
        r"\begin{thebibliography}{1}" + "\n"
        r"\bibitem{key} Ref." + "\n"
        r"\end{thebibliography}" + "\n",
        encoding="utf-8",
    )

    bibtex_flag = compiler._prepare_bibliography_inputs(main_tex)

    assert bibtex_flag == "-bibtex-"
    assert main_bbl.read_text(encoding="utf-8") == main_bbl_tex.read_text(encoding="utf-8")


def test_prepare_bibliography_inputs_keeps_bibtex_for_standard_driver(tmp_path):
    project_dir = tmp_path / "project_bibtex"
    main_tex = project_dir / "main.tex"
    main_bib = project_dir / "main.bib"

    _write_minimal_tex(
        main_tex,
        r"\documentclass{article}" + "\n"
        r"\begin{document}" + "\n"
        r"\bibliographystyle{plain}" + "\n"
        r"\bibliography{main}" + "\n"
        r"\end{document}" + "\n",
    )
    main_bib.write_text("% bibliography database exists\n", encoding="utf-8")

    bibtex_flag = compiler._prepare_bibliography_inputs(main_tex)

    assert bibtex_flag == "-bibtex"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
