import json
from pathlib import Path

from backend.app.services.agents.generator_agent import GeneratorAgent


def _seed_maps(output_dir: Path) -> None:
    payloads = {
        "sections_map.json": [
            {
                "section": "1",
                "content": "translated body",
                "trans_content": "translated body",
                "translation_status": "translated",
            }
        ],
        "captions_map.json": [],
        "envs_map.json": [],
        "newcommands_map.json": [],
        "inputs_map.json": [],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def test_generator_allows_compile_when_source_matches_same_walker_guard_failure(
    tmp_path,
    monkeypatch,
):
    project_dir = tmp_path / "src_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    source_main = project_dir / "main.tex"
    source_main.write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Baseline text with odd math start $ and no closing delimiter.\n"
        "\\end{document}\n",
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
            "Translated text with odd math start $ and no closing delimiter.\n"
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
            "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"},
        },
        project_dir=str(project_dir),
        output_dir=str(output_dir),
    )

    result = agent.execute()

    assert result["status"] == "completed"
    assert result["guard_warning_only"] is True
    assert result["guard_reason_code"] == "structure_latexwalker_unexpected_closing_env"
    assert "source baseline" in (result["warnings"] or "")

    replay = json.loads((output_dir / "replay_bundle.json").read_text(encoding="utf-8"))
    assert replay["guard_warning_only"] is True
    assert replay["compile_attempted"] is True
    assert replay["compile_verdict_source"] == "compiler"
