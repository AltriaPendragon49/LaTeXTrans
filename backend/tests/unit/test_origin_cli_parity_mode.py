import json
from pathlib import Path
from types import SimpleNamespace


def test_advanced_config_defaults_to_origin_cli_parity():
    from backend.app.models.config_models import AdvancedConfig, ORIGIN_CLI_PARITY_MODE

    config = AdvancedConfig()

    assert config.translation_core_mode == ORIGIN_CLI_PARITY_MODE


def test_origin_cli_parity_normalizer_forces_legacy_core_and_disables_modern_systems():
    from backend.app.models.config_models import (
        MODERN_SYSTEMS_DISABLED_FOR_ORIGIN_CLI_PARITY,
        ORIGIN_CLI_PARITY_MODE,
        normalize_origin_cli_parity_agent_config,
    )

    normalized = normalize_origin_cli_parity_agent_config(
        {
            "translation_core_mode": "modern",
            "enable_legacy_translation_core": False,
            "use_compilation_diagnostics": True,
            "enable_compile_first_structural_fallback": True,
            "enable_post_compile_target_language_fallback": True,
            "enable_precompile_structure_guard": True,
            "enable_hard_freeze_tokens": True,
            "enable_parser_env_llm_judgment": True,
            "enable_section_internal_parallelism": True,
            "enable_intelligent_compiler_fallback": True,
        }
    )

    assert normalized["translation_core_mode"] == ORIGIN_CLI_PARITY_MODE
    assert normalized["enable_legacy_translation_core"] is True
    assert normalized["use_compilation_diagnostics"] is False
    assert normalized["enable_compile_first_structural_fallback"] is False
    assert normalized["enable_post_compile_target_language_fallback"] is False
    assert normalized["enable_precompile_structure_guard"] is False
    assert normalized["enable_hard_freeze_tokens"] is False
    assert normalized["enable_parser_env_llm_judgment"] is True
    assert normalized["enable_section_internal_parallelism"] is False
    assert normalized["enable_intelligent_compiler_fallback"] is False
    assert normalized["generate_terminology"] is False
    assert normalized["generate_terminology_table"] is False
    assert normalized["origin_cli_parity_modern_systems_not_invoked"] == MODERN_SYSTEMS_DISABLED_FOR_ORIGIN_CLI_PARITY


def test_origin_cli_parity_normalizer_forces_legacy_full_translation_mode():
    from backend.app.models.config_models import normalize_origin_cli_parity_agent_config

    normalized = normalize_origin_cli_parity_agent_config(
        {
            "mode": 3,
            "translation_mode": "quick_scan",
        }
    )

    assert normalized["mode"] == 0
    assert normalized["translation_mode"] == "full"


def test_origin_cli_parity_graph_contains_only_legacy_workflow_nodes():
    from backend.app.models.config_models import ORIGIN_CLI_PARITY_MODE
    from backend.app.services.agents.langgraph_orchestrator import build_pipeline_graph

    graph = build_pipeline_graph(config={"translation_core_mode": ORIGIN_CLI_PARITY_MODE})
    node_names = set(graph.get_graph().nodes)

    assert {"parse", "translate", "validate_and_retry", "generate", "finalize"}.issubset(node_names)
    assert "repair_translation" not in node_names
    assert "ultimate_downgrade" not in node_names
    assert "post_compile_target_language_fallback" not in node_names
    assert "compilation_diagnostic" not in node_names


def test_parser_origin_cli_parity_omits_backend_only_chunk_metadata(tmp_path):
    from backend.app.services.latex.parser import LatexParser

    project_dir = tmp_path / "paper"
    project_dir.mkdir()
    repeated = " ".join(["word"] * 5000)
    (project_dir / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\section{Intro}\n"
        f"{repeated}\n"
        "\\begin{theorem}Important theorem text.\\end{theorem}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    parser = LatexParser(str(project_dir), str(tmp_path / "out"), origin_cli_parity=True)
    parser.parse()

    assert all("_chunk_" not in str(section["section"]) for section in parser.sections_json)
    assert all("chunk_kind" not in section for section in parser.sections_json)
    theorem_env = next(env for env in parser.envs_json if env["env_name"] == "theorem")
    assert theorem_env["need_trans"] is True


def test_reconstructor_origin_cli_parity_keeps_translated_section_bytes(tmp_path):
    from backend.app.services.latex.reconstruct import LatexConstructor

    constructor = LatexConstructor(
        sections=[
            {
                "section": "1",
                "content": "\\section{Results}\nOriginal English text.",
                "trans_content": "译文正文，不含 section 命令。",
            }
        ],
        captions=[],
        envs=[],
        inputs=[],
        newcommands=[],
        output_latex_dir=str(tmp_path),
        target_language="zh",
        origin_cli_parity=True,
    )

    assert constructor._merge_sections() == "译文正文，不含 section 命令。\n"


def test_compile_with_origin_cli_parity_stops_after_pdflatex_pdf(monkeypatch, tmp_path):
    from backend.app.services.latex import compiler

    tex_file = tmp_path / "main.tex"
    tex_file.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")
    calls = []

    def fake_run(cmd, check, capture_output, cwd):
        engine = next(part[1:] for part in cmd if part in {"-pdflatex", "-xelatex"})
        output_dir = Path(next(part.split("=", 1)[1] for part in cmd if part.startswith("-outdir=")))
        calls.append((Path(cmd[-1]).name, output_dir.name, engine, check, capture_output, Path(cwd).name))
        output_dir.mkdir(parents=True, exist_ok=True)
        if engine == "pdflatex":
            (output_dir / "main.pdf").write_bytes(b"%PDF")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(compiler.subprocess, "run", fake_run)

    result = compiler.compile_with_origin_cli_parity(str(tex_file), str(tmp_path))

    assert result["pdf_path"].endswith("build_pdflatex\\main.pdf") or result["pdf_path"].endswith("build_pdflatex/main.pdf")
    assert result["engine"] == "pdflatex"
    assert calls == [("main.tex", "build_pdflatex", "pdflatex", True, True, tmp_path.name)]


def test_run_pipeline_logs_parity_mode_and_not_invoked_systems(monkeypatch, tmp_path):
    import backend.app.services.agents.langgraph_orchestrator as orch_mod
    from backend.app.models.config_models import (
        MODERN_SYSTEMS_DISABLED_FOR_ORIGIN_CLI_PARITY,
        ORIGIN_CLI_PARITY_MODE,
    )

    project_dir = tmp_path / "paper"
    project_dir.mkdir()
    (project_dir / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}hello\\end{document}",
        encoding="utf-8",
    )
    output_root = tmp_path / "out"
    output_root.mkdir()

    class Parser:
        def __init__(self, *args, **kwargs):
            pass

        async def execute(self):
            return None

    class Translator:
        structural_fallback_count = 0
        structural_fallback_ratio = 0.0
        structural_fallback_cap = 0.1
        structural_fallback_cap_mode = "soft"
        structural_fallback_parts = []
        noop_sections = []
        payload_invariant_sections = []
        c1_retry_enforced_once = False
        structural_fallback_warning = None

        def __init__(self, *args, **kwargs):
            self.trans_mode = kwargs.get("trans_mode", 0)

        async def execute(self, *args, **kwargs):
            return None

    class Validator:
        code_like_filtered_bare_tokens = 0

        def __init__(self, *args, **kwargs):
            pass

        def execute(self, *args, **kwargs):
            return []

    class Generator:
        def __init__(self, *args, **kwargs):
            pass

        async def execute_async(self):
            return {"status": "completed", "pdf_path": str(tmp_path / "paper.pdf"), "engine": "pdflatex"}

    (tmp_path / "paper.pdf").write_bytes(b"%PDF")
    monkeypatch.setattr(orch_mod, "ParserAgent", Parser)
    monkeypatch.setattr(orch_mod, "TranslatorAgent", Translator)
    monkeypatch.setattr(orch_mod, "ValidatorAgent", Validator)
    monkeypatch.setattr(orch_mod, "GeneratorAgent", Generator)

    result = orch_mod.asyncio.run(
        orch_mod.run_pipeline(
            config={"translation_core_mode": ORIGIN_CLI_PARITY_MODE, "target_language": "zh"},
            project_dir=str(project_dir),
            output_dir=str(output_root),
        )
    )

    assert result["status"] == "completed"
    task_log = json.loads((output_root / "zh_paper" / "task_log.json").read_text(encoding="utf-8"))
    task_started = next(entry for entry in task_log if entry["event"] == "task_started")
    assert task_started["config"]["translation_core_mode"] == ORIGIN_CLI_PARITY_MODE
    assert task_started["config"]["origin_cli_parity_modern_systems_not_invoked"] == MODERN_SYSTEMS_DISABLED_FOR_ORIGIN_CLI_PARITY
