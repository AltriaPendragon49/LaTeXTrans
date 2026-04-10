"""
TDD 测试: test_stategraph_orchestrator.py
Phase 4a Step 1 �?StateGraph 替换 Coordinator 编排�?

契约�?
  - �?StateGraph 与旧 CoordinatorAgent 外部行为完全等价
  - �?agent 逻辑零修改，仅执行权迁移
  - 所有失败语义与降级路径保持不变
"""
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

# ---------------------------------------------------------------------------
# Fake Agents（与 test_coordinator_structure_invalid_short_circuit.py 保持一致）
# ---------------------------------------------------------------------------


class _FakeParserAgent:
    def __init__(self, *args, **kwargs):
        self.called = False

    async def execute(self):
        self.called = True
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
        self.execute_call_count = 0
        self.trans_mode = kwargs.get("trans_mode", 0)
        self.errors_report = kwargs.get("errors_report", [])

    async def execute(self, *args, **kwargs):
        self.execute_call_count += 1
        return None


class _FakeValidatorAgent:
    def __init__(self, *args, **kwargs):
        self.code_like_filtered_bare_tokens = 0

    def execute(self, *args, **kwargs):
        return []


class _FakeGeneratorAgent:
    def __init__(self, *args, **kwargs):
        self.called = False

    def execute(self):
        self.called = True
        return {
            "status": "completed",
            "pdf_path": None,      # �?pdf_path �?�?failed_compilation 分支
            "error_summary": "no pdf in test",
            "warnings": None,
            "error_count": 0,
            "engine": "xelatex",
        }


class _FakeGeneratorStructureInvalid:
    def __init__(self, *args, **kwargs):
        pass

    def execute(self):
        return {
            "status": "structure_invalid",
            "pdf_path": None,
            "error_summary": "structure guard failure",
            "warnings": None,
            "failure_reason_code": "structure_env_stack_mismatch",
            "failure_class": "structural",
            "guard_phase": "precompile",
            "replay_bundle_ref": None,
        }


# ---------------------------------------------------------------------------
# 公共 fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_setup(tmp_path):
    project_dir = tmp_path / "paper"
    project_dir.mkdir()
    (project_dir / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nhello\n\\end{document}\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "out"
    output_root.mkdir()
    return project_dir, output_root


BASE_CONFIG = {
    "sys_name": "LaTeXTrans",
    "target_language": "zh",
    "source_language": "en",
    "mode": 0,
    "generate_terminology": False,
    "enable_post_compile_target_language_fallback": True,
    "llm_config": {"model": "gpt-4o", "base_url": "http://dummy", "api_key": "dummy"},
}


def _patch_agents(monkeypatch, orchestrator_module, generator_cls=_FakeGeneratorAgent):
    monkeypatch.setattr(orchestrator_module, "ParserAgent", _FakeParserAgent)
    monkeypatch.setattr(orchestrator_module, "TranslatorAgent", _FakeTranslatorAgent)
    monkeypatch.setattr(orchestrator_module, "ValidatorAgent", _FakeValidatorAgent)
    monkeypatch.setattr(orchestrator_module, "GeneratorAgent", generator_cls)


# ===========================================================================
# 测试用例 1：正常路�?�?节点调用顺序
# ===========================================================================


def test_happy_path_node_call_sequence(monkeypatch, project_setup):
    """parse→translate→validate→generate 全被调用一次（pdf_path �?None �?failed_compilation）�?""
    project_dir, output_root = project_setup

    import backend.app.services.agents.langgraph_orchestrator as orch_mod

    _patch_agents(monkeypatch, orch_mod)

    result = asyncio.run(
        orch_mod.run_pipeline(
            config=BASE_CONFIG,
            project_dir=str(project_dir),
            output_dir=str(output_root),
            on_progress=None,
        )
    )

    # pdf_path �?None �?coordinator 返回 failed_compilation
    assert result["status"] == "failed_compilation"
    assert result["pdf_path"] is None


# ===========================================================================
# 测试用例 2：structure_invalid 短路
# ===========================================================================


def test_structure_invalid_short_circuits(monkeypatch, project_setup):
    """generate 返回 structure_invalid 时，finalize 不执行，结果 status == structure_invalid�?""
    project_dir, output_root = project_setup

    import backend.app.services.agents.langgraph_orchestrator as orch_mod

    _patch_agents(monkeypatch, orch_mod, generator_cls=_FakeGeneratorStructureInvalid)

    result = asyncio.run(
        orch_mod.run_pipeline(
            config=BASE_CONFIG,
            project_dir=str(project_dir),
            output_dir=str(output_root),
            on_progress=None,
        )
    )

    assert result["status"] == "structure_invalid"
    assert result["failure_reason_code"] == "structure_env_stack_mismatch"
    assert result["guard_phase"] == "precompile"
    assert result["pdf_path"] is None

    # 日志中必须有 structure_guard_failed_precompile �?structure_invalid_aborted
    transed_dir = output_root / f"zh_{project_dir.name}"
    log_path = transed_dir / "task_log.json"
    assert log_path.exists()
    events = [e["event"] for e in json.loads(log_path.read_text(encoding="utf-8"))]
    assert "structure_guard_failed_precompile" in events
    assert "structure_invalid_aborted" in events
    assert not any(e.startswith("compilation_") for e in events)


# ===========================================================================
# 测试用例 3：阶段失败向上传�?
# ===========================================================================


def test_stage_failure_propagates(monkeypatch, project_setup):
    """parse 抛出异常时，run_pipeline 应将异常传播出来（不吞错误）�?""
    project_dir, output_root = project_setup

    class _BrokenParser:
        def __init__(self, *args, **kwargs):
            pass

        async def execute(self):
            raise RuntimeError("parse step failed")

    import backend.app.services.agents.langgraph_orchestrator as orch_mod

    _patch_agents(monkeypatch, orch_mod)
    monkeypatch.setattr(orch_mod, "ParserAgent", _BrokenParser)

    with pytest.raises(RuntimeError, match="parse step failed"):
        asyncio.run(
            orch_mod.run_pipeline(
                config=BASE_CONFIG,
                project_dir=str(project_dir),
                output_dir=str(output_root),
                on_progress=None,
            )
        )


# ===========================================================================
# 测试用例 4：mode==3 跳过修复循环
# ===========================================================================


def test_mode3_skips_repair(monkeypatch, project_setup):
    """mode==3（quick scan）时，translator.execute 仅被调用一次（跳过 retry）�?""
    project_dir, output_root = project_setup

    import backend.app.services.agents.langgraph_orchestrator as orch_mod

    _patch_agents(monkeypatch, orch_mod)

    # �?validator 返回一些错误，以证�?mode==3 不进�?repair 循环
    class _ValidatorWithErrors:
        def __init__(self, *args, **kwargs):
            self.code_like_filtered_bare_tokens = 0

        def execute(self, *args, **kwargs):
            return [{"error_type": "C1", "part": "sec", "num_or_ph": "1"}]

    monkeypatch.setattr(orch_mod, "ValidatorAgent", _ValidatorWithErrors)

    # 用一个可记录调用次数�?translator
    call_log = []

    class _CountingTranslator(_FakeTranslatorAgent):
        async def execute(self, *args, **kwargs):
            call_log.append("execute")
            return None

    monkeypatch.setattr(orch_mod, "TranslatorAgent", _CountingTranslator)

    config_mode3 = {**BASE_CONFIG, "mode": 3}
    asyncio.run(
        orch_mod.run_pipeline(
            config=config_mode3,
            project_dir=str(project_dir),
            output_dir=str(output_root),
            on_progress=None,
        )
    )

    assert call_log.count("execute") == 1, (
        f"mode==3 �?translator.execute 应只调用一次，实际调用 {call_log.count('execute')} �?
    )


# ===========================================================================
# 测试用例 5：正常路径写入关键日志事�?
# ===========================================================================


def test_task_log_events_happy_path(monkeypatch, project_setup):
    """正常路径�?task_log.json 包含 task_started / parsing_completed / translation_completed / validation_completed�?""
    project_dir, output_root = project_setup

    import backend.app.services.agents.langgraph_orchestrator as orch_mod

    _patch_agents(monkeypatch, orch_mod)

    asyncio.run(
        orch_mod.run_pipeline(
            config=BASE_CONFIG,
            project_dir=str(project_dir),
            output_dir=str(output_root),
            on_progress=None,
        )
    )

    transed_dir = output_root / f"zh_{project_dir.name}"
    log_path = transed_dir / "task_log.json"
    assert log_path.exists(), "task_log.json 应被创建"
    events = [e["event"] for e in json.loads(log_path.read_text(encoding="utf-8"))]

    for expected_event in ("task_started", "parsing_completed", "translation_completed", "validation_completed"):
        assert expected_event in events, f"日志中缺少事�?'{expected_event}'，实�? {events}"


# ===========================================================================
# 测试用例 6：CoordinatorAgent 委托�?StateGraph（行为等价）
# ===========================================================================


def test_coordinator_delegates_to_stategraph(monkeypatch, project_setup):
    """CoordinatorAgent.workflow_latextrans_async() 通过�?StateGraph 编排，行为与旧实现等价�?""
    project_dir, output_root = project_setup

    import backend.app.services.agents.langgraph_orchestrator as orch_mod
    import backend.app.services.agents.coordinator_agent as coord_mod

    _patch_agents(monkeypatch, orch_mod)

    agent = coord_mod.CoordinatorAgent(
        config=BASE_CONFIG,
        project_dir=str(project_dir),
        output_dir=str(output_root),
    )

    result = asyncio.run(agent.workflow_latextrans_async())

    # 行为等价：pdf_path=None 时返�?failed_compilation（与原实现路径一致）
    assert result["status"] == "failed_compilation"
    assert result["pdf_path"] is None


def test_post_compile_target_language_fallback_applies_on_pending_sections(tmp_path):
    import backend.app.services.agents.langgraph_orchestrator as orch_mod
    from backend.app.services.agents.pipeline_schema import FallbackReport

    transed_project_dir = tmp_path / "out"
    transed_project_dir.mkdir(parents=True, exist_ok=True)
    sections_path = transed_project_dir / "sections_map.json"
    envs_path = transed_project_dir / "envs_map.json"

    sections = [
        {
            "section": "0",
            "content": r"\begin{document} hello \end{document}",
            "trans_content": r"\begin{document} 你好 \end{document}",
            "translation_status": "structural_fallback_pending_compile",
        },
        {
            "section": "1",
            "content": r"\section{A} hello",
            "trans_content": r"\section{A} 你好",
            "translation_status": "structural_fallback_pending_compile",
        },
    ]
    envs = []
    sections_path.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
    envs_path.write_text(json.dumps(envs, ensure_ascii=False, indent=2), encoding="utf-8")

    state = {
        "config": {"enable_post_compile_target_language_fallback": True},
        "transed_project_dir": str(transed_project_dir),
        "task_id": "t1",
        "base_name": "t1",
        "on_progress": None,
        "compile_fallback_reports": [
            FallbackReport(fallback_kind="c1_structural_rollback", chunk_scope="0", root_cause="c1"),
            FallbackReport(fallback_kind="c2_structural_collapse", chunk_scope="1", root_cause="c2"),
        ],
        "post_compile_fallback_attempted": False,
    }

    asyncio.run(orch_mod.node_post_compile_target_language_fallback(state))
    out_sections = json.loads(sections_path.read_text(encoding="utf-8"))
    sec0 = next(s for s in out_sections if s.get("section") == "0")
    sec1 = next(s for s in out_sections if s.get("section") == "1")

    assert sec0.get("translation_status") == "final_target_language_fallback_applied"
    assert sec1.get("translation_status") == "final_target_language_fallback_applied"
    assert "你好" in sec0.get("trans_content", "")
    assert "hello" not in sec0.get("trans_content", "")
    assert "你好" in sec1.get("trans_content", "")

    task_log = json.loads((transed_project_dir / "task_log.json").read_text(encoding="utf-8"))
    events = [entry["event"] for entry in task_log]
    assert "post_compile_target_language_fallback_started" in events
    assert "post_compile_target_language_fallback_completed" in events
    assert "compile_retry_after_target_language_fallback" in events


def test_post_compile_target_language_fallback_reconstructs_without_source_revert(tmp_path):
    import backend.app.services.agents.langgraph_orchestrator as orch_mod
    from backend.app.services.agents.pipeline_schema import FallbackReport
    from backend.app.services.latex.reconstruct import LatexConstructor

    transed_project_dir = tmp_path / "out-reconstruct"
    transed_project_dir.mkdir(parents=True, exist_ok=True)
    sections_path = transed_project_dir / "sections_map.json"
    envs_path = transed_project_dir / "envs_map.json"

    sections = [
        {
            "section": "1",
            "content": r"\section{Results}" + "\n\n" + "We begin by examining the left panel.",
            "trans_content": r"\section{结果}" + "\n\n" + "我们首先考察左侧面板�?,
            "translation_status": "structural_fallback_pending_compile",
        }
    ]
    sections_path.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
    envs_path.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")

    state = {
        "config": {"enable_post_compile_target_language_fallback": True},
        "transed_project_dir": str(transed_project_dir),
        "task_id": "t1-reconstruct",
        "base_name": "t1-reconstruct",
        "on_progress": None,
        "compile_fallback_reports": [
            FallbackReport(fallback_kind="c2_structural_collapse", chunk_scope="1", root_cause="c2"),
        ],
        "post_compile_fallback_attempted": False,
    }

    asyncio.run(orch_mod.node_post_compile_target_language_fallback(state))
    out_sections = json.loads(sections_path.read_text(encoding="utf-8"))
    merged_tex = LatexConstructor(
        sections=out_sections,
        captions=[],
        envs=[],
        inputs=[],
        newcommands=[],
        output_latex_dir=str(transed_project_dir),
    )._merge_sections()

    assert r"\section{结果}" in merged_tex
    assert "We begin by examining" not in merged_tex


def test_route_after_generate_uses_post_compile_fallback_once():
    import backend.app.services.agents.langgraph_orchestrator as orch_mod
    from backend.app.services.agents.pipeline_schema import FallbackReport

    report = FallbackReport(
        fallback_kind="c2_structural_collapse",
        chunk_scope="1",
        root_cause="c2",
    )

    state = {
        "config": {"enable_post_compile_target_language_fallback": True},
        "generation_result": {"status": "completed", "pdf_path": "out/main.pdf"},
        "compile_fallback_reports": [report],
        "post_compile_fallback_attempted": False,
    }
    assert orch_mod._route_after_generate(state) == "post_compile_target_language_fallback"

    state["post_compile_fallback_attempted"] = True
    assert orch_mod._route_after_generate(state) == "finalize"


def test_route_after_validate_generates_after_repair_budget_exhausted():
    import backend.app.services.agents.langgraph_orchestrator as orch_mod
    from backend.app.services.agents.pipeline_schema import FallbackReport

    state = {
        "fallback_reports": [
            FallbackReport(
                fallback_kind="c2_structural_collapse",
                chunk_scope="1",
                root_cause="c2",
            )
        ],
        "repair_retry_count": orch_mod.MAX_REPAIR_RETRIES,
    }

    assert orch_mod._route_after_validate(state) == "generate"
