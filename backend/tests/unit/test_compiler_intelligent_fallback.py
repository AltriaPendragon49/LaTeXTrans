from pathlib import Path

from backend.app.services.latex import compiler


def _write_minimal_tex(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


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


def test_target_language_ja_forces_cjk_engine_family(monkeypatch, tmp_path):
    main_tex = tmp_path / "paper" / "main.tex"
    out_dir = tmp_path / "out"
    _write_minimal_tex(
        main_tex,
        r"\documentclass{article}"
        "\n"
        r"\begin{document}"
        "\nHello world."
        "\n"
        r"\end{document}",
    )

    called_engines = []

    def fake_compile_latex(tex_file, output_dir, engine="pdflatex", max_runs=2):
        called_engines.append(engine)
        return _fake_success_result(tex_file, output_dir)

    monkeypatch.setattr(compiler, "compile_latex", fake_compile_latex)
    monkeypatch.setattr(compiler, "_upgrade_outdated_cls_files", lambda _tex_dir: None)

    result = compiler.compile_with_intelligent_fallback(
        tex_file=str(main_tex),
        output_dir=str(out_dir),
        target_language="ja",
    )

    assert result["status"] == "completed"
    assert result["engine"] == "xelatex"
    assert called_engines[0] == "xelatex"
    assert result["language_decision"]["resolved_language"] == "cjk"
    assert result["language_decision"]["target_language_family"] == "cjk"
    assert "target_language=ja->cjk" in result["language_decision"]["reason"]
    assert isinstance(result["engine_order_reason"], str)
    assert isinstance(result["compat_shims_applied"], list)


def test_hwemoji_is_shimmed_for_xelatex(monkeypatch, tmp_path):
    """
    When Stage 0 fails, Stage 1 must apply the hwemoji compatibility shim for xelatex.
    The shim must comment out \\usepackage{hwemoji} and inject a fallback macro.
    """
    main_tex = tmp_path / "paper_hwemoji" / "main.tex"
    out_dir = tmp_path / "out_hwemoji"
    _write_minimal_tex(
        main_tex,
        r"\documentclass{article}"
        "\n"
        r"\usepackage{hwemoji}"
        "\n"
        r"\begin{document}"
        "\n"
        r"\emoji{smile}"
        "\n"
        r"\end{document}",
    )

    observed_tex_by_stage = {}
    call_count = {"n": 0}

    def fake_compile_latex(tex_file, output_dir, engine="pdflatex", max_runs=2):
        call_count["n"] += 1
        content = Path(tex_file).read_text(encoding="utf-8", errors="replace")
        shim_marker = "% disabled by engine compatibility shim"
        if shim_marker in content:
            # Stage 1 onwards: record the shimmed content and return success
            observed_tex_by_stage["shimmed"] = content
            return _fake_success_result(tex_file, output_dir)
        else:
            # Stage 0: pristine content, return failure to trigger Stage 1
            observed_tex_by_stage["pristine"] = content
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            log_path = out / f"{Path(tex_file).stem}.log"
            log_path.write_text("! LaTeX Error: hwemoji not found.", encoding="utf-8")
            return compiler.CompilationResult(
                success=False,
                pdf_path=None,
                log_path=str(log_path),
                error_count=1,
                errors=["hwemoji not found"],
            )

    monkeypatch.setattr(compiler, "compile_latex", fake_compile_latex)
    monkeypatch.setattr(compiler, "_upgrade_outdated_cls_files", lambda _tex_dir: None)

    result = compiler.compile_with_intelligent_fallback(
        tex_file=str(main_tex),
        output_dir=str(out_dir),
        preferred_order=["xelatex"],
    )

    assert result["status"] == "completed"
    assert result["engine"] == "xelatex"
    # Stage 0 must have been pristine (no shim applied)
    assert "pristine" in observed_tex_by_stage, "Stage 0 must have been attempted"
    assert "% disabled by engine compatibility shim" not in observed_tex_by_stage["pristine"], \
        "Stage 0 must NOT apply shims"
    # Stage 1 must have applied the hwemoji shim
    assert "shimmed" in observed_tex_by_stage, "Stage 1 (shimmed) must have been attempted after Stage 0 failure"
    assert "% \\usepackage{hwemoji} % disabled by engine compatibility shim" in observed_tex_by_stage["shimmed"]
    assert r"\providecommand{\emoji}[1]{#1}" in observed_tex_by_stage["shimmed"]
    # Verify compat_shims_applied log contains a Stage 1 entry with the shim name
    stage1_shims = [
        entry for entry in result["compat_shims_applied"]
        if entry.get("stage") == 1 and entry.get("engine") == "xelatex"
    ]
    assert stage1_shims, "compat_shims_applied must include a Stage 1 xelatex entry"
    assert "disable_hwemoji_for_modern_engine" in stage1_shims[0]["shims"]


def test_failed_compilation_returns_diagnostics_fields(monkeypatch, tmp_path):

    main_tex = tmp_path / "paper_fail" / "main.tex"
    out_dir = tmp_path / "out_fail"
    _write_minimal_tex(
        main_tex,
        r"\documentclass{article}"
        "\n"
        r"\begin{document}"
        "\nFail path."
        "\n"
        r"\end{document}",
    )

    def fake_compile_latex(tex_file, output_dir, engine="pdflatex", max_runs=2):
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

    monkeypatch.setattr(compiler, "compile_latex", fake_compile_latex)
    monkeypatch.setattr(compiler, "_upgrade_outdated_cls_files", lambda _tex_dir: None)

    result = compiler.compile_with_intelligent_fallback(
        tex_file=str(main_tex),
        output_dir=str(out_dir),
        preferred_order=["pdflatex"],
    )

    assert result["status"] == "failed_compilation"
    assert "language_decision" in result
    assert "engine_order_reason" in result
    assert "compat_shims_applied" in result
    assert isinstance(result["compat_shims_applied"], list)


def test_stage3_entrypoint_not_bypassed_on_image_compile_failure(monkeypatch, tmp_path):
    main_tex = tmp_path / "paper_stage3" / "main.tex"
    out_dir = tmp_path / "out_stage3"
    _write_minimal_tex(
        main_tex,
        r"\documentclass{article}"
        "\n"
        r"\begin{document}"
        "\nImage fail path."
        "\n"
        r"\end{document}",
    )

    def fake_compile_latex(tex_file, output_dir, engine="pdflatex", max_runs=2):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        log_path = out / f"{Path(tex_file).stem}.log"
        log_path.write_text("! image failure", encoding="utf-8")
        return compiler.CompilationResult(
            success=False,
            pdf_path=None,
            log_path=str(log_path),
            error_count=1,
            errors=["(file imgs/HOTA.pdf) (pdf inclusion): reading image failed"],
        )

    stage3_calls = {"count": 0}

    def fake_try_sanitize(error_lines, tex_dir, already_sanitized=None):
        stage3_calls["count"] += 1
        return [], False, set()

    monkeypatch.setattr(compiler, "compile_latex", fake_compile_latex)
    monkeypatch.setattr(compiler, "_upgrade_outdated_cls_files", lambda _tex_dir: None)
    monkeypatch.setattr(compiler, "try_sanitize_images_in_errors", fake_try_sanitize)

    result = compiler.compile_with_intelligent_fallback(
        tex_file=str(main_tex),
        output_dir=str(out_dir),
        preferred_order=["pdflatex"],
    )

    assert stage3_calls["count"] >= 1
    assert result["status"] in {"failed_compilation", "completed_with_warnings", "completed"}


def test_pdf_inclusion_multiline_variant_triggers_stage3(monkeypatch, tmp_path):
    main_tex = tmp_path / "paper_stage3_multiline" / "main.tex"
    out_dir = tmp_path / "out_stage3_multiline"
    _write_minimal_tex(
        main_tex,
        r"\documentclass{article}"
        "\n"
        r"\begin{document}"
        "\nImage fail multiline path."
        "\n"
        r"\end{document}",
    )

    def fake_compile_latex(tex_file, output_dir, engine="pdflatex", max_runs=2):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        log_path = out / f"{Path(tex_file).stem}.log"
        log_path.write_text("! image failure multiline", encoding="utf-8")
        return compiler.CompilationResult(
            success=False,
            pdf_path=None,
            log_path=str(log_path),
            error_count=1,
            errors=[
                "(./main.tex:10: error:  (file imgs/HOTA.pdf) (pdf inclusion):",
                "reading image failed",
            ],
        )

    stage3_calls = {"count": 0}

    def fake_try_sanitize(error_lines, tex_dir, already_sanitized=None):
        stage3_calls["count"] += 1
        return [], False, set()

    monkeypatch.setattr(compiler, "compile_latex", fake_compile_latex)
    monkeypatch.setattr(compiler, "_upgrade_outdated_cls_files", lambda _tex_dir: None)
    monkeypatch.setattr(compiler, "try_sanitize_images_in_errors", fake_try_sanitize)

    compiler.compile_with_intelligent_fallback(
        tex_file=str(main_tex),
        output_dir=str(out_dir),
        preferred_order=["pdflatex"],
    )

    assert stage3_calls["count"] >= 1


def test_stage0_unresolved_natbib_citations_do_not_short_circuit_success(monkeypatch, tmp_path):
    main_tex = tmp_path / "paper_cites" / "main.tex"
    out_dir = tmp_path / "out_cites"
    _write_minimal_tex(
        main_tex,
        r"\documentclass{article}"
        "\n"
        r"\begin{document}"
        "\nHello world."
        "\n"
        r"\end{document}",
    )

    call_count = {"n": 0}

    def fake_compile_latex(tex_file, output_dir, engine="pdflatex", max_runs=2):
        call_count["n"] += 1
        out_dir_local = Path(output_dir)
        out_dir_local.mkdir(parents=True, exist_ok=True)
        stem = Path(tex_file).stem
        pdf_path = out_dir_local / f"{stem}.pdf"
        log_path = out_dir_local / f"{stem}.log"
        pdf_path.write_bytes(b"%PDF-1.4\n")
        if call_count["n"] == 1:
            log_path.write_text(
                "Package natbib Warning: Citation `brown_language_2020' on page 1 undefined on input line 10.\n",
                encoding="utf-8",
            )
        else:
            log_path.write_text("", encoding="utf-8")
        return compiler.CompilationResult(
            success=True,
            pdf_path=str(pdf_path),
            log_path=str(log_path),
            error_count=0,
            errors=[],
            bibliography_issue_count=1 if call_count["n"] == 1 else 0,
            bibliography_issues=(
                ["Package natbib Warning: Citation `brown_language_2020' on page 1 undefined on input line 10."]
                if call_count["n"] == 1 else []
            ),
        )

    monkeypatch.setattr(compiler, "compile_latex", fake_compile_latex)
    monkeypatch.setattr(compiler, "_upgrade_outdated_cls_files", lambda _tex_dir: None)

    result = compiler.compile_with_intelligent_fallback(
        tex_file=str(main_tex),
        output_dir=str(out_dir),
        preferred_order=["xelatex"],
    )

    assert result["status"] == "completed"
    assert call_count["n"] >= 2, "unresolved natbib citations should not count as a perfect compile"
