import json
import asyncio
import logging
import time
from pathlib import Path

from backend.app.services.agents.generator_agent import GeneratorAgent
from backend.app.services.agents.langgraph_orchestrator import (
    node_post_compile_target_language_fallback,
)
from backend.app.services.agents.pipeline_schema import FallbackReport
from backend.app.services.latex.compiler import find_main_tex_file
from backend.app.services.latex.structure_guard import validate_project_structure


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed_maps(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "sections_map.json", [])
    _write_json(out_dir / "captions_map.json", [])
    _write_json(out_dir / "envs_map.json", [])
    _write_json(out_dir / "newcommands_map.json", [])
    _write_json(out_dir / "inputs_map.json", [])


def test_generator_precompile_structure_guard_short_circuits_compile(tmp_path, monkeypatch):
    project_dir = tmp_path / "src_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nsource\n\\end{document}\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "translated_bundle"
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "sections_map.json",
        [
            {
                "section": "-1",
                "content": "\\documentclass{article}\n\\begin{document}\n\\end{figure}\n\\end{document}\n",
                "trans_content": "\\documentclass{article}\n\\begin{document}\n\\end{figure}\n\\end{document}\n",
            }
        ],
    )
    _write_json(output_dir / "captions_map.json", [])
    _write_json(output_dir / "envs_map.json", [])
    _write_json(output_dir / "newcommands_map.json", [])
    _write_json(output_dir / "inputs_map.json", [])

    def _compile_must_not_run(*args, **kwargs):
        raise AssertionError("compile_with_intelligent_fallback should not run on structure-invalid bundle")

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.compile_with_intelligent_fallback",
        _compile_must_not_run,
    )

    progress_messages = []

    agent = GeneratorAgent(
        config={
            "target_language": "zh",
            "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"},
        },
        project_dir=str(project_dir),
        output_dir=str(output_dir),
        on_progress=lambda _stage, _pct, message: progress_messages.append(message),
    )

    result = agent.execute()

    assert result["status"] == "structure_invalid"
    assert result["failure_class"] == "structural"
    assert result["guard_phase"] == "precompile"
    assert result["failure_reason_code"] in {
        "structure_env_stack_mismatch",
        "structure_latexwalker_unexpected_closing_env",
    }

    replay_ref = result.get("replay_bundle_ref")
    assert replay_ref
    replay_path = Path(replay_ref)
    assert replay_path.exists()
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    assert replay["guard_phase"] == "precompile"
    assert replay["failure_reason_code"] == result["failure_reason_code"]
    assert "Checking project structure..." in progress_messages
    assert "Compiling PDF document" not in progress_messages


def test_generator_execute_async_treats_existing_warning_pdf_as_success(tmp_path, monkeypatch):
    import backend.app.services.agents.compile_runtime as cr

    project_dir = tmp_path / "src_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nsource\n\\end{document}\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "translated_bundle"
    _seed_maps(output_dir)

    def _fake_construct(self, on_progress=None):
        main = Path(self.output_latex_dir) / "main.tex"
        main.parent.mkdir(parents=True, exist_ok=True)
        main.write_text(
            "\\documentclass{article}\n\\begin{document}\ntranslated\n\\end{document}\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.LatexConstructor.construct",
        _fake_construct,
    )
    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.validate_project_structure",
        lambda _p: {"ok": True},
    )

    async def _fake_compile_async(*args, **kwargs):
        pdf_path = output_dir / "src_project" / "main.lualatex.stage0.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4\n")
        return {
            "pdf_path": str(pdf_path),
            "status": "completed_with_warnings",
            "engine": "lualatex",
            "error_count": 1,
            "warnings": "Compilation completed with 1 errors using lualatex.",
            "errors": None,
        }

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.compile_with_intelligent_fallback_async",
        _fake_compile_async,
    )
    monkeypatch.setattr(cr, "_compile_semaphore", asyncio.Semaphore(1))

    progress_messages = []

    agent = GeneratorAgent(
        config={"target_language": "ja"},
        project_dir=str(project_dir),
        output_dir=str(output_dir),
        on_progress=lambda _stage, _pct, message: progress_messages.append(message),
    )

    result = asyncio.run(agent.execute_async())
    expected_pdf = output_dir / "src_project" / "main.lualatex.stage0.pdf"
    assert result["status"] == "completed_with_warnings"
    assert result["pdf_path"] == str(expected_pdf)
    assert result["error_summary"] is None
    assert "Checking project structure..." in progress_messages
    assert "Waiting for compile slot" not in progress_messages
    assert progress_messages.index("Checking project structure...") < progress_messages.index("Compiling PDF document")


def test_generator_compile_phase_respects_compile_semaphore(monkeypatch, tmp_path):
    import backend.app.services.agents.compile_runtime as cr

    proj1 = tmp_path / "p1"
    proj2 = tmp_path / "p2"
    proj1.mkdir(parents=True, exist_ok=True)
    proj2.mkdir(parents=True, exist_ok=True)
    (proj1 / "main.tex").write_text("\\documentclass{article}\\begin{document}a\\end{document}", encoding="utf-8")
    (proj2 / "main.tex").write_text("\\documentclass{article}\\begin{document}b\\end{document}", encoding="utf-8")

    out1 = tmp_path / "o1"
    out2 = tmp_path / "o2"
    _seed_maps(out1)
    _seed_maps(out2)

    def _fake_construct(self, on_progress=None):
        main = Path(self.output_latex_dir) / "main.tex"
        main.parent.mkdir(parents=True, exist_ok=True)
        main.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.LatexConstructor.construct",
        _fake_construct,
    )
    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.validate_project_structure",
        lambda _p: {"ok": True},
    )

    timeline = []

    async def _fake_compile_async(*args, **kwargs):
        timeline.append(("compile_start", time.perf_counter()))
        await asyncio.sleep(0.12)
        out_dir = Path(kwargs["output_dir"])
        pdf = out_dir / "main.lualatex.stage0.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        timeline.append(("compile_end", time.perf_counter()))
        return {
            "pdf_path": str(pdf),
            "status": "completed_with_warnings",
            "engine": "lualatex",
            "error_count": 1,
            "warnings": "w",
            "errors": None,
        }

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.compile_with_intelligent_fallback_async",
        _fake_compile_async,
    )
    monkeypatch.setattr(cr, "_compile_semaphore", asyncio.Semaphore(1))

    g1 = GeneratorAgent(config={"target_language": "ja"}, project_dir=str(proj1), output_dir=str(out1))
    g2 = GeneratorAgent(config={"target_language": "ja"}, project_dir=str(proj2), output_dir=str(out2))

    async def _run():
        await asyncio.gather(g1.execute_async(), g2.execute_async())

    asyncio.run(_run())
    starts = [t for k, t in timeline if k == "compile_start"]
    ends = [t for k, t in timeline if k == "compile_end"]
    assert len(starts) == 2 and len(ends) == 2
    assert starts[1] >= ends[0] - 1e-3, "compile semaphore should serialize only compile phase"


def test_generator_execute_async_reports_waiting_only_on_real_contention(monkeypatch, tmp_path):
    import backend.app.services.agents.compile_runtime as cr

    project_dir = tmp_path / "src_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nsource\n\\end{document}\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "translated_bundle"
    _seed_maps(output_dir)

    def _fake_construct(self, on_progress=None):
        main = Path(self.output_latex_dir) / "main.tex"
        main.parent.mkdir(parents=True, exist_ok=True)
        main.write_text(
            "\\documentclass{article}\n\\begin{document}\ntranslated\n\\end{document}\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.LatexConstructor.construct",
        _fake_construct,
    )
    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.validate_project_structure",
        lambda _p: {"ok": True},
    )

    async def _fake_compile_async(*args, **kwargs):
        pdf_path = output_dir / "src_project" / "main.lualatex.stage0.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4\n")
        return {
            "pdf_path": str(pdf_path),
            "status": "completed",
            "engine": "lualatex",
            "error_count": 0,
            "warnings": None,
            "errors": None,
        }

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.compile_with_intelligent_fallback_async",
        _fake_compile_async,
    )

    semaphore = asyncio.Semaphore(1)
    asyncio.run(semaphore.acquire())
    monkeypatch.setattr(cr, "_compile_semaphore", semaphore)

    progress_messages = []
    agent = GeneratorAgent(
        config={"target_language": "ja"},
        project_dir=str(project_dir),
        output_dir=str(output_dir),
        on_progress=lambda _stage, _pct, message: progress_messages.append(message),
    )

    async def _run():
        async def _release_later():
            await asyncio.sleep(0.05)
            semaphore.release()

        await asyncio.gather(agent.execute_async(), _release_later())

    asyncio.run(_run())
    assert "Checking project structure..." in progress_messages
    assert "Waiting for compile slot" in progress_messages
    assert progress_messages.index("Checking project structure...") < progress_messages.index("Waiting for compile slot")
    assert progress_messages.index("Waiting for compile slot") < progress_messages.index("Compiling PDF document")


def test_validate_project_structure_logs_elapsed_ms(tmp_path, caplog):
    main_tex = tmp_path / "main.tex"
    main_tex.write_text(
        "\\documentclass{article}\n\\begin{document}\nhello\n\\end{document}\n",
        encoding="utf-8",
    )

    with caplog.at_level(logging.INFO, logger="backend.app.services.latex.structure_guard"):
        result = validate_project_structure(str(main_tex))

    assert result["ok"] is True
    messages = [record.getMessage() for record in caplog.records]
    assert any("elapsed_ms=" in message for message in messages)
    assert any("main.tex" in message for message in messages)
    assert any("ok=True" in message for message in messages)
    assert any("reason_code=None" in message for message in messages)


def test_validate_project_structure_macro_body_tabular_is_warning_only(tmp_path):
    main_tex = tmp_path / "main.tex"
    main_tex.write_text(
        "\\documentclass{article}\n"
        "\\usepackage{titling}\n"
        "\\usepackage{array}\n"
        "\\preauthor{\\begin{center}\\begin{tabular}{c}}\n"
        "\\postauthor{\\end{tabular}\\end{center}}\n"
        "\\makeatletter\n"
        "\\renewcommand\\and{\\end{tabular}\\hfill\\begin{tabular}{c}}\n"
        "\\makeatother\n"
        "\\begin{document}\n"
        "\\title{Title}\n"
        "\\author{Alice \\and Bob}\n"
        "\\maketitle\n"
        "Hello\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    result = validate_project_structure(str(main_tex))

    assert result["ok"] is True
    assert result["warning_only"] is True
    assert result["guard_blocking"] is False
    assert result["guard_scope"] == "preamble"
    assert result["reason_code"] == "structure_env_stack_mismatch"


def test_generator_execute_compiles_when_structure_guard_is_warning_only(tmp_path, monkeypatch):
    project_dir = tmp_path / "src_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nsource\n\\end{document}\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "translated_bundle"
    _seed_maps(output_dir)

    def _fake_construct(self, on_progress=None):
        main = Path(self.output_latex_dir) / "main.tex"
        main.parent.mkdir(parents=True, exist_ok=True)
        main.write_text(
            "\\documentclass{article}\n"
            "\\usepackage{titling}\n"
            "\\usepackage{array}\n"
            "\\preauthor{\\begin{center}\\begin{tabular}{c}}\n"
            "\\postauthor{\\end{tabular}\\end{center}}\n"
            "\\makeatletter\n"
            "\\renewcommand\\and{\\end{tabular}\\hfill\\begin{tabular}{c}}\n"
            "\\makeatother\n"
            "\\begin{document}\n"
            "\\title{Title}\n"
            "\\author{Alice \\and Bob}\n"
            "\\maketitle\n"
            "translated\n"
            "\\end{document}\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.LatexConstructor.construct",
        _fake_construct,
    )

    def _fake_compile(*args, **kwargs):
        pdf_path = output_dir / "src_project" / "main.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4\n")
        return {
            "pdf_path": str(pdf_path),
            "status": "completed",
            "engine": "pdflatex",
            "error_count": 0,
            "warnings": None,
            "errors": None,
        }

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.compile_with_intelligent_fallback",
        _fake_compile,
    )

    agent = GeneratorAgent(
        config={"target_language": "zh", "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"}},
        project_dir=str(project_dir),
        output_dir=str(output_dir),
    )

    result = agent.execute()

    assert result["status"] == "completed"
    assert result["guard_warning_only"] is True
    assert result["guard_scope"] == "preamble"
    assert "[Structure Guard Warning]" in (result["warnings"] or "")
    replay = json.loads((output_dir / "replay_bundle.json").read_text(encoding="utf-8"))
    assert replay["guard_warning_only"] is True
    assert replay["compile_attempted"] is True
    assert replay["compile_verdict_source"] == "compiler"


def test_find_main_tex_file_returns_none_for_ambiguous_tex_without_documentclass(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "iclr2022_conference.tex").write_text("\\input{expt}\n", encoding="utf-8")
    (bundle / "expt.tex").write_text("Body only\n", encoding="utf-8")

    assert find_main_tex_file(str(bundle)) is None


def test_post_compile_fallback_preserves_document_root_chunks(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    _write_json(
        bundle / "sections_map.json",
        [
            {
                "section": "-1_chunk_1",
                "content": "\\documentclass{article}\n\\usepackage{times}\n",
                "trans_content": "根据要求，我会保�?LaTeX 结构并输出翻译结果。\n\\title{坏掉的标题}\n",
                "translation_status": "structural_fallback_pending_compile",
                "chunk_role": "document_root",
            },
            {
                "section": "9",
                "content": "\\section{Setup}\nOriginal body.",
                "trans_content": "\\section{Setup}\nTranslated body.",
                "translation_status": "structural_fallback_pending_compile",
                "chunk_role": "normal",
            },
        ],
    )
    _write_json(bundle / "envs_map.json", [])

    state = {
        "transed_project_dir": str(bundle),
        "task_id": "case-1",
        "compile_fallback_reports": [
            FallbackReport(
                fallback_kind="c2_structural_collapse",
                chunk_scope="-1_chunk_1",
                root_cause="c2_global_structure_collapse",
                translated_text="broken preamble",
            ),
            FallbackReport(
                fallback_kind="c2_structural_collapse",
                chunk_scope="9",
                root_cause="c2_global_structure_collapse",
                translated_text="broken section",
            ),
        ],
    }

    asyncio.run(node_post_compile_target_language_fallback(state))

    sections = json.loads((bundle / "sections_map.json").read_text(encoding="utf-8"))
    preserved_root = next(section for section in sections if section["section"] == "-1_chunk_1")
    downgraded_section = next(section for section in sections if section["section"] == "9")

    assert preserved_root["trans_content"] == "\\documentclass{article}\n\\usepackage{times}\n"
    assert preserved_root["translation_status"] == "structural_fallback_pending_compile"
    assert preserved_root["document_root_fallback_preserved"] is True
    assert downgraded_section["translation_status"] == "final_target_language_fallback_applied"
