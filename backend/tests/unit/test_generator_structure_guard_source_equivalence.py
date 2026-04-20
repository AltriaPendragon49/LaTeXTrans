import json
from pathlib import Path

from backend.app.services.agents.generator_agent import GeneratorAgent


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed_maps(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "sections_map.json", [])
    _write_json(out_dir / "captions_map.json", [])
    _write_json(out_dir / "envs_map.json", [])
    _write_json(out_dir / "newcommands_map.json", [])
    _write_json(out_dir / "inputs_map.json", [])


def test_generator_execute_downgrades_source_equivalent_walker_failure_with_different_offsets(
    tmp_path, monkeypatch
):
    project_dir = tmp_path / "src_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    source_main = project_dir / "main.tex"
    source_main.write_text(
        "\\documentclass{article}\n\\begin{document}\nsource\n\\end{document}\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "translated_bundle"
    _seed_maps(output_dir)
    translated_root = output_dir / "src_project"
    translated_main = translated_root / "main.tex"

    def _fake_construct(self, on_progress=None):
        translated_root.mkdir(parents=True, exist_ok=True)
        translated_main.write_text(
            "\\documentclass{article}\n\\begin{document}\ntranslated\n\\end{document}\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.LatexConstructor.construct",
        _fake_construct,
    )

    def _fake_validate(path: str):
        normalized = str(Path(path))
        if normalized == str(translated_main):
            return {
                "ok": False,
                "reason_code": "structure_latexwalker_unexpected_closing_env",
                "message": (
                    "Unexpected closing environment: 'document' @(677,0)\n"
                    "Open LaTeX blocks:\n"
                    "          @(100,0)  begin environment \"document\"\n"
                    "        @(543,316)  math mode \"$\"\n"
                ),
                "details": {},
                "warning_only": False,
                "guard_blocking": True,
                "guard_scope": "project",
            }
        if normalized == str(source_main):
            return {
                "ok": False,
                "reason_code": "structure_latexwalker_unexpected_closing_env",
                "message": (
                    "Unexpected closing environment: 'document' @(683,0)\n"
                    "Open LaTeX blocks:\n"
                    "           @(89,0)  begin environment \"document\"\n"
                    "        @(525,689)  math mode \"$\"\n"
                ),
                "details": {},
                "warning_only": False,
                "guard_blocking": True,
                "guard_scope": "project",
            }
        raise AssertionError(f"Unexpected validate_project_structure path: {path}")

    monkeypatch.setattr(
        "backend.app.services.agents.generator_agent.validate_project_structure",
        _fake_validate,
    )

    def _fake_compile(*args, **kwargs):
        pdf_path = translated_root / "main.pdf"
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
            "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"},
        },
        project_dir=str(project_dir),
        output_dir=str(output_dir),
    )

    result = agent.execute()

    assert result["status"] == "completed"
    assert result["guard_warning_only"] is True
    assert result["guard_reason_code"] == "structure_latexwalker_unexpected_closing_env"
    replay = json.loads((output_dir / "replay_bundle.json").read_text(encoding="utf-8"))
    assert replay["guard_warning_only"] is True
    assert replay["guard_reason_code"] == "structure_latexwalker_unexpected_closing_env"
