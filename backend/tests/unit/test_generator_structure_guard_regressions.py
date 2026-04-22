import json
from pathlib import Path

from backend.app.services.agents.generator_agent import GeneratorAgent
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


def test_validate_project_structure_ignores_placeholder_tokens_inside_comments(tmp_path):
    main_tex = tmp_path / "main.tex"
    main_tex.write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "% [LaTeX-Trans: ultimate downgrade applied - chunk: <PLACEHOLDER_ENV_67>]\n"
        "hello\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    result = validate_project_structure(str(main_tex))

    assert result["ok"] is True
    assert result["warning_only"] is False
    assert result["reason_code"] is None


def test_generator_execute_compiles_when_precompile_structure_guard_disabled(tmp_path, monkeypatch):
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
            "\\begin{document}\n"
            "\\end{figure}\n"
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
        config={
            "target_language": "zh",
            "enable_precompile_structure_guard": False,
            "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"},
        },
        project_dir=str(project_dir),
        output_dir=str(output_dir),
    )

    result = agent.execute()

    assert result["status"] == "completed"
    assert result["guard_warning_only"] is True
    assert result["guard_reason_code"] in {
        "structure_env_stack_mismatch",
        "structure_latexwalker_unexpected_closing_env",
    }
    assert "precompile structure guard disabled via config" in (result["warnings"] or "")

    replay = json.loads((output_dir / "replay_bundle.json").read_text(encoding="utf-8"))
    assert replay["guard_warning_only"] is True
    assert replay["guard_blocking"] is False
    assert replay["structure_guard_details"]["guard_disabled_via_config"] is True
