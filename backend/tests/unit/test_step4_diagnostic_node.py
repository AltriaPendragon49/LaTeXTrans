"""
test_step4_diagnostic_node.py
Step 4 TDD（RED 阶段）：Phase 4b CompilationDiagnosticNode 守卫测试

6 个测试，分别验证�?
  1. feature flag 默认禁用时路由不激活诊断节�?
  2. 启用�?DiagnosticReport 符合 schema
  3. 启用时无任何 .tex 文件被修�?
  4. 启用�?audit.jsonl 包含 node_enter / node_exit 事件
  5. 所�?DiagnosticSuggestion.action_type 只允许白名单�?
  6. build_pipeline_graph() 默认不含 compilation_diagnostic 节点
"""
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_config():
    return {
        "sys_name": "LaTeXTrans",
        "target_language": "zh",
        "source_language": "en",
        "mode": 0,
        "latex_engine": "auto",
        "use_verification_agent": False,
        "generate_terminology": False,
        "use_compilation_diagnostics": False,  # 显式关闭以测试关闭逻辑
        "task_id": "test-step4-task",
        "llm_config": {
            "model": "gpt-4o",
            "base_url": "http://dummy",
            "api_key": "dummy",
        },
    }


@pytest.fixture
def enabled_config(base_config):
    return {**base_config, "use_compilation_diagnostics": True}


def _fake_agents(tmp_path):
    """返回一套正�?fake agent，编译结果为 failed_compilation（用于测试诊断节点激活）�?""
    class _FakeParser:
        def __init__(self, *a, **kw): pass
        async def execute(self): pass

    class _FakeTranslator:
        structural_fallback_count = 0
        structural_fallback_ratio = 0.0
        structural_fallback_cap = 0.38
        structural_fallback_cap_mode = "soft"
        structural_fallback_parts = []
        noop_sections = []
        c1_retry_enforced_once = False
        structural_fallback_warning = None
        def __init__(self, *a, **kw): pass
        async def execute(self, *a, **kw): pass

    class _FakeValidator:
        code_like_filtered_bare_tokens = 0
        def __init__(self, *a, **kw): pass
        def execute(self, *a, **kw): return []

    class _FailingGenerator:
        """返回 failed_compilation 状态，触发诊断节点路由�?""
        def __init__(self, *a, **kw): pass
        def execute(self):
            return {
                "status": "failed",
                "pdf_path": None,
                "error_summary": "Compilation failed with all engines:\n\n./main.tex:5: Missing $ inserted.",
                "warnings": None,
                "error_count": 5,
                "engine": None,
            }

    class _SuccessGenerator:
        """返回 completed 状态，不触发诊断路由�?""
        def __init__(self, *a, **kw): pass
        def execute(self):
            return {
                "status": "completed",
                "pdf_path": str(tmp_path / "out.pdf"),
                "error_summary": None,
                "warnings": None,
            }

    return _FakeParser, _FakeTranslator, _FakeValidator, _FailingGenerator, _SuccessGenerator


def _run_pipeline(monkeypatch, tmp_path, config, use_failing_generator=False):
    from backend.app.services.agents import langgraph_orchestrator as orch
    P, T, V, FailG, SuccG = _fake_agents(tmp_path)
    monkeypatch.setattr(orch, "ParserAgent", P)
    monkeypatch.setattr(orch, "TranslatorAgent", T)
    monkeypatch.setattr(orch, "ValidatorAgent", V)
    monkeypatch.setattr(orch, "GeneratorAgent", FailG if use_failing_generator else SuccG)

    project_dir = tmp_path / "proj"
    project_dir.mkdir(exist_ok=True)
    output_dir = tmp_path / "out"
    output_dir.mkdir(exist_ok=True)
    if not use_failing_generator:
        (tmp_path / "out.pdf").write_bytes(b"%PDF-1.4")

    with patch("backend.app.services.latex.compiler.verify_pdf_ready", return_value=True):
        result = asyncio.run(orch.run_pipeline(
            config=config,
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        ))
    return result, output_dir / "zh_proj"


# ---------------------------------------------------------------------------
# Test 1: feature flag 显式禁用时，诊断节点不激�?
# ---------------------------------------------------------------------------


def test_diagnostic_disabled_when_explicitly_disabled(monkeypatch, tmp_path, base_config):
    """feature flag 显式关闭时，compilation_diagnostic 节点不被触发�?
    成功路径�?audit.jsonl 中不含任�?compilation_diagnostic 事件�?""
    result, trans_dir = _run_pipeline(monkeypatch, tmp_path, base_config, use_failing_generator=False)

    audit_path = trans_dir / "audit.jsonl"
    assert audit_path.exists(), "audit.jsonl 不存�?
    events = [json.loads(l)["event"] for l in audit_path.read_text().strip().splitlines()]
    diag_events = [e for e in events if "compilation_diagnostic" in e]
    assert diag_events == [], f"feature flag 关闭时不应有诊断事件，实际：{diag_events}"


# ---------------------------------------------------------------------------
# Test 2: feature flag 启用且编译失败时，DiagnosticReport 符合 schema
# ---------------------------------------------------------------------------


def test_diagnostic_report_schema_when_enabled(monkeypatch, tmp_path, enabled_config):
    """启用 use_compilation_diagnostics=True 且编译失败时�?
    final_result 中包含有效格式的 diagnostic_report�?""
    from backend.app.services.agents.compilation_diagnostic_node import (
        CompilationDiagnosticNode,
        DiagnosticReport,
    )

    fake_report = DiagnosticReport(
        task_id="test-step4-task",
        error_count=5,
        root_cause_category="syntax_error",
        suggestions=[],
        confidence=0.8,
        is_actionable=False,
        raw_llm_response="dummy",
    )

    mock_node = AsyncMock(return_value=fake_report)
    monkeypatch.setattr(
        "backend.app.services.agents.langgraph_orchestrator.CompilationDiagnosticNode",
        lambda *a, **kw: MagicMock(execute=mock_node),
    )

    result, trans_dir = _run_pipeline(monkeypatch, tmp_path, enabled_config, use_failing_generator=True)

    assert "diagnostic_report" in result, "启用诊断�?final_result 中应�?diagnostic_report 字段"
    report = result["diagnostic_report"]
    assert isinstance(report, (dict, DiagnosticReport)), "diagnostic_report 类型不符"


# ---------------------------------------------------------------------------
# Test 3: 启用时无任何 .tex 文件被修�?
# ---------------------------------------------------------------------------


def test_diagnostic_node_no_tex_mutation(monkeypatch, tmp_path, enabled_config):
    """诊断节点执行后，project dir 中所�?.tex 文件内容与执行前完全一致�?""
    from backend.app.services.agents.compilation_diagnostic_node import (
        CompilationDiagnosticNode,
        DiagnosticReport,
    )

    # �?project dir 中写入一�?fake .tex 文件
    project_dir = tmp_path / "proj"
    project_dir.mkdir(exist_ok=True)
    tex_file = project_dir / "main.tex"
    original_content = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n"
    tex_file.write_text(original_content, encoding="utf-8")

    fake_report = DiagnosticReport(
        task_id="test-step4-task",
        error_count=5,
        root_cause_category="package_conflict",
        suggestions=[],
        confidence=0.9,
        is_actionable=False,
        raw_llm_response="dummy",
    )
    mock_node = AsyncMock(return_value=fake_report)
    monkeypatch.setattr(
        "backend.app.services.agents.langgraph_orchestrator.CompilationDiagnosticNode",
        lambda *a, **kw: MagicMock(execute=mock_node),
    )

    from backend.app.services.agents import langgraph_orchestrator as orch
    P, T, V, FailG, _ = _fake_agents(tmp_path)
    monkeypatch.setattr(orch, "ParserAgent", P)
    monkeypatch.setattr(orch, "TranslatorAgent", T)
    monkeypatch.setattr(orch, "ValidatorAgent", V)
    monkeypatch.setattr(orch, "GeneratorAgent", FailG)

    output_dir = tmp_path / "out"
    output_dir.mkdir(exist_ok=True)

    with patch("backend.app.services.latex.compiler.verify_pdf_ready", return_value=True):
        asyncio.run(orch.run_pipeline(
            config=enabled_config,
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        ))

    # 验证 .tex 文件未被修改
    after_content = tex_file.read_text(encoding="utf-8")
    assert after_content == original_content, (
        f"诊断节点修改�?.tex 文件！\n---Before---\n{original_content}\n---After---\n{after_content}"
    )


# ---------------------------------------------------------------------------
# Test 4: 启用�?audit.jsonl 包含诊断节点�?enter/exit 事件
# ---------------------------------------------------------------------------


def test_diagnostic_node_audit_logged(monkeypatch, tmp_path, enabled_config):
    """诊断节点启用运行后，audit.jsonl 中必须包�?
    node_enter:compilation_diagnostic �?node_exit:compilation_diagnostic�?""
    from backend.app.services.agents.compilation_diagnostic_node import (
        CompilationDiagnosticNode,
        DiagnosticReport,
    )

    fake_report = DiagnosticReport(
        task_id="test-step4-task",
        error_count=5,
        root_cause_category="unknown",
        suggestions=[],
        confidence=0.5,
        is_actionable=False,
        raw_llm_response="dummy",
    )
    mock_node = AsyncMock(return_value=fake_report)
    monkeypatch.setattr(
        "backend.app.services.agents.langgraph_orchestrator.CompilationDiagnosticNode",
        lambda *a, **kw: MagicMock(execute=mock_node),
    )

    result, trans_dir = _run_pipeline(monkeypatch, tmp_path, enabled_config, use_failing_generator=True)

    audit_path = trans_dir / "audit.jsonl"
    assert audit_path.exists(), "audit.jsonl 不存�?
    events = [json.loads(l)["event"] for l in audit_path.read_text().strip().splitlines()]
    assert "node_enter:compilation_diagnostic" in events, (
        f"缺少 node_enter:compilation_diagnostic，实�?events={events}"
    )
    assert "node_exit:compilation_diagnostic" in events, (
        f"缺少 node_exit:compilation_diagnostic，实�?events={events}"
    )


# ---------------------------------------------------------------------------
# Test 5: DiagnosticSuggestion.action_type 只允许白名单�?
# ---------------------------------------------------------------------------


def test_diagnostic_suggestions_only_whitelisted_actions(tmp_path):
    """DiagnosticSuggestion �?action_type 必须是白名单枚举值；
    传入非法值必须在 schema 层面被拒绝（ValidationError）�?""
    from pydantic import ValidationError

    from backend.app.services.agents.compilation_diagnostic_node import DiagnosticSuggestion

    # 合法值应被接�?
    valid_suggestion = DiagnosticSuggestion(
        action_type="comment_package",
        target="axessibility",
        reason="Incompatible with XeLaTeX",
        is_whitelisted=True,
        reversible=True,
    )
    assert valid_suggestion.action_type == "comment_package"

    # 非法值必须被拒绝
    with pytest.raises((ValidationError, ValueError)):
        DiagnosticSuggestion(
            action_type="DELETE_FILE",  # 非法手段
            target="main.tex",
            reason="Evil action",
            is_whitelisted=False,
            reversible=False,
        )


# ---------------------------------------------------------------------------
# Test 6: build_pipeline_graph() 默认包含 compilation_diagnostic 节点
# ---------------------------------------------------------------------------


def test_diagnostic_node_in_graph_by_default():
    """调用 build_pipeline_graph()（无 config 参数，默认行为）
    编译出的图中默认应包含名�?compilation_diagnostic 的节点（基于用户请求调整）�?""
    from backend.app.services.agents.langgraph_orchestrator import build_pipeline_graph

    graph = build_pipeline_graph()
    # LangGraph 编译图可通过 .nodes �?.graph.nodes 访问节点�?
    node_names = set(graph.graph.nodes) if hasattr(graph, "graph") else set(getattr(graph, "nodes", {}).keys())
    assert "compilation_diagnostic" in node_names, (
        f"默认图应当包�?compilation_diagnostic 节点，实际节点：{node_names}"
    )

def test_diagnostic_node_not_in_graph_when_disabled():
    """显式传入配置关闭诊断节点时图中不再包�?""
    from backend.app.services.agents.langgraph_orchestrator import build_pipeline_graph

    graph = build_pipeline_graph(enable_diagnostics=False)
    node_names = set(graph.graph.nodes) if hasattr(graph, "graph") else set(getattr(graph, "nodes", {}).keys())
    assert "compilation_diagnostic" not in node_names, (
        f"显式关闭时不应包�?compilation_diagnostic 节点，实际节点：{node_names}"
    )
