import asyncio
import json
import os
from pathlib import Path

class _FakeParserAgent:
    def __init__(self, *args, **kwargs):
        pass

    async def execute(self):
        return None


class _FakeTranslatorAgent:
    def __init__(self, *args, **kwargs):
        self.structural_fallback_count = 0
        self.structural_fallback_ratio = 0.0
        self.structural_fallback_cap = 0.38
        self.structural_fallback_cap_mode = "soft"
        self.structural_fallback_parts = []
        self.noop_sections = []
        self.c1_retry_enforced_once = False
        self.structural_fallback_warning = None

    async def execute(self, *args, **kwargs):
        return None


class _FakeValidatorAgent:
    def __init__(self, *args, **kwargs):
        self.code_like_filtered_bare_tokens = 0

    def execute(self, *args, **kwargs):
        return []


class _FakeGeneratorAgent:
    def __init__(self, *args, **kwargs):
        pass

    def execute(self):
        return {
            "status": "structure_invalid",
            "pdf_path": None,
            "error_summary": "synthetic structure guard failure",
            "warnings": None,
            "failure_reason_code": "structure_env_stack_mismatch",
            "failure_class": "structural",
            "guard_phase": "precompile",
            "replay_bundle_ref": "/tmp/replay_bundle.json",
        }


def test_coordinator_short_circuits_on_structure_invalid(monkeypatch, tmp_path):
    os.environ.setdefault("LLM_API_KEY", "dummy-key")
    os.environ.setdefault("LLM_BASE_URL", "http://dummy")
    os.environ.setdefault("LLM_MODEL", "gpt-4o")

    from backend.app.services.agents import langgraph_orchestrator as orch_module
    from backend.app.services.agents.coordinator_agent import CoordinatorAgent

    monkeypatch.setattr(orch_module, "ParserAgent", _FakeParserAgent)
    monkeypatch.setattr(orch_module, "TranslatorAgent", _FakeTranslatorAgent)
    monkeypatch.setattr(orch_module, "ValidatorAgent", _FakeValidatorAgent)
    monkeypatch.setattr(orch_module, "GeneratorAgent", _FakeGeneratorAgent)

    project_dir = tmp_path / "paper"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nhello\n\\end{document}\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "out"
    output_root.mkdir(parents=True, exist_ok=True)

    agent = CoordinatorAgent(
        config={
            "sys_name": "LaTeXTrans",
            "target_language": "zh",
            "source_language": "en",
            "mode": 0,
            "latex_engine": "auto",
            "use_verification_agent": False,
            "generate_terminology": False,
            "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"},
        },
        project_dir=str(project_dir),
        output_dir=str(output_root),
    )

    result = asyncio.run(agent.workflow_latextrans_async())
    assert result["status"] == "structure_invalid"
    assert result["failure_reason_code"] == "structure_env_stack_mismatch"
    assert result["guard_phase"] == "precompile"

    task_log_path = output_root / f"zh_{project_dir.name}" / "task_log.json"
    assert task_log_path.exists()
    events = json.loads(task_log_path.read_text(encoding="utf-8"))
    event_names = [entry.get("event", "") for entry in events]
    assert "structure_guard_failed_precompile" in event_names
    assert "structure_invalid_aborted" in event_names
    assert not any(name.startswith("compilation_") for name in event_names)
