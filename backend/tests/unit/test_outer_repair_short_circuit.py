import asyncio
import json
import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")


def test_pipeline_short_circuits_repeated_outer_repair_without_progress(monkeypatch, tmp_path):
    import backend.app.services.agents.langgraph_orchestrator as orch_mod
    from backend.app.services.agents.pipeline_schema import FallbackReport

    class _FakeParserAgent:
        def __init__(self, *args, **kwargs):
            pass

        async def execute(self):
            return None

    class _TranslatorWithStaticFallback:
        structural_fallback_count = 0
        structural_fallback_ratio = 0.0
        structural_fallback_cap = 0.38
        structural_fallback_cap_mode = "soft"
        structural_fallback_parts = []
        noop_sections = []
        payload_invariant_sections = []
        c1_retry_enforced_once = False
        structural_fallback_warning = None

        def __init__(self, *args, **kwargs):
            self.execute_call_count = 0
            self.trans_mode = kwargs.get("trans_mode", 0)
            self.errors_report = kwargs.get("errors_report", [])
            self.fallback_reports = []

        async def execute(self, *args, **kwargs):
            self.execute_call_count += 1
            self.fallback_reports = [
                FallbackReport(
                    fallback_kind="c2_structural_collapse",
                    chunk_scope="1",
                    root_cause="same-root",
                    validation_evidence={"command_error": "same-error"},
                    translated_text="broken",
                )
            ]
            return None

    class _ValidatorWithStaticErrors:
        def __init__(self, *args, **kwargs):
            self.code_like_filtered_bare_tokens = 0

        def execute(self, *args, **kwargs):
            return [
                {
                    "part": "sec",
                    "num_or_ph": "1",
                    "error_type": "C2",
                    "command_error": "same-error",
                }
            ]

    class _FakeGeneratorAgent:
        def __init__(self, *args, **kwargs):
            pass

        def execute(self):
            return {
                "status": "failed_compilation",
                "pdf_path": None,
                "error_summary": "no pdf in test",
                "warnings": None,
                "error_count": 0,
                "engine": "xelatex",
            }

    repair_calls = {"value": 0}

    async def _fake_repair_translation(state):
        repair_calls["value"] += 1
        return {
            **state,
            "fallback_reports": [],
            "repair_retry_count": int(state.get("repair_retry_count") or 0) + 1,
        }

    monkeypatch.setattr(orch_mod, "ParserAgent", _FakeParserAgent)
    monkeypatch.setattr(orch_mod, "TranslatorAgent", _TranslatorWithStaticFallback)
    monkeypatch.setattr(orch_mod, "ValidatorAgent", _ValidatorWithStaticErrors)
    monkeypatch.setattr(orch_mod, "GeneratorAgent", _FakeGeneratorAgent)
    monkeypatch.setattr(orch_mod, "node_repair_translation", _fake_repair_translation)

    project_dir = tmp_path / "paper"
    project_dir.mkdir()
    (project_dir / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nhello\n\\end{document}\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "out"
    output_root.mkdir()

    asyncio.run(
        orch_mod.run_pipeline(
            config={
                "sys_name": "LaTeXTrans",
                "target_language": "zh",
                "source_language": "en",
                "mode": 0,
                "generate_terminology": False,
                "enable_post_compile_target_language_fallback": True,
                "use_compilation_diagnostics": False,
                "llm_config": {
                    "model": "gpt-4o",
                    "base_url": "http://dummy",
                    "api_key": "dummy",
                },
            },
            project_dir=str(project_dir),
            output_dir=str(output_root),
            on_progress=None,
        )
    )

    assert repair_calls["value"] == 1

    transed_dir = output_root / f"zh_{project_dir.name}"
    task_log = json.loads((transed_dir / "task_log.json").read_text(encoding="utf-8"))
    assert any(
        entry["event"] == "repair_loop_short_circuited_no_progress" for entry in task_log
    )
