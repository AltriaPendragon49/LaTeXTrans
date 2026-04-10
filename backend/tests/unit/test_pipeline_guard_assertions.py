"""
test_pipeline_guard_assertions.py
Gate 4b-4：不可变守护测试套件（Guard Assertions�?

这些测试用例锁定 Phase 4b 的核心不变量�?
- 最大轮次硬性限�?
- 全局超时上下文拦�?
- JSONL 审计日志完整�?
- Pydantic Schema 校验
- 架构完整性（�?DiagnosticNode�?

全部测试遵循 TDD 策略（先写测试，后实现）�?
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")


# ---------------------------------------------------------------------------
# 公共 Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_config():
    return {
        "sys_name": "LaTeXTrans",
        "target_language": "zh",
        "source_language": "en",
        "mode": 0,
        "latex_engine": "auto",
        "use_verification_agent": False,
        "generate_terminology": False,
        "llm_config": {
            "model": "gpt-4o",
            "base_url": "http://dummy",
            "api_key": "dummy",
        },
    }


# ---------------------------------------------------------------------------
# Test 1: Gate 4b-1 �?PipelineInput 缺少必填字段时抛 ValidationError
# ---------------------------------------------------------------------------


def test_pydantic_input_rejects_invalid():
    """PipelineInput 缺少必填字段时应�?ValidationError�?""
    from backend.app.services.agents.pipeline_schema import PipelineInput
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PipelineInput()  # 缺少 task_id / config / project_dir / output_dir


def test_pydantic_input_accepts_valid(minimal_config, tmp_path):
    """PipelineInput 提供全部必填字段时应正常构建�?""
    from backend.app.services.agents.pipeline_schema import PipelineInput

    obj = PipelineInput(
        task_id="test-task-001",
        config=minimal_config,
        project_dir=str(tmp_path / "proj"),
        output_dir=str(tmp_path / "out"),
        mode=0,
    )
    assert obj.task_id == "test-task-001"
    assert obj.mode == 0


# ---------------------------------------------------------------------------
# Test 3: Gate 4b-1 �?audit.jsonl 存在且包�?task_id
# ---------------------------------------------------------------------------


def test_audit_log_contains_task_id(monkeypatch, tmp_path, minimal_config):
    """audit.jsonl 中每条记录必须包�?task_id 字段�?""
    from backend.app.services.agents import langgraph_orchestrator as orch

    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()

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

    class _FakeGenerator:
        def __init__(self, *a, **kw): pass
        def execute(self):
            return {"status": "completed", "pdf_path": str(tmp_path / "out.pdf"), "error_summary": None, "warnings": None}

    monkeypatch.setattr(orch, "ParserAgent", _FakeParser)
    monkeypatch.setattr(orch, "TranslatorAgent", _FakeTranslator)
    monkeypatch.setattr(orch, "ValidatorAgent", _FakeValidator)
    monkeypatch.setattr(orch, "GeneratorAgent", _FakeGenerator)

    # 创建�?PDF
    (tmp_path / "out.pdf").write_bytes(b"%PDF-1.4")

    with patch("backend.app.services.latex.compiler.verify_pdf_ready", return_value=True):
        asyncio.run(orch.run_pipeline(
            config=minimal_config,
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        ))

    audit_path = output_dir / "zh_proj" / "audit.jsonl"
    assert audit_path.exists(), "audit.jsonl 应该存在"

    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1, "audit.jsonl 至少应有一条记�?
    for line in lines:
        record = json.loads(line)
        assert "task_id" in record, f"缺少 task_id 字段：{record}"


# ---------------------------------------------------------------------------
# Test 4: Gate 4b-1 �?正常路径�?audit.jsonl 中写�?pipeline_start / pipeline_end
# ---------------------------------------------------------------------------


def test_audit_log_entries_on_happy_path(monkeypatch, tmp_path, minimal_config):
    """正常路径应在 audit.jsonl 中写�?pipeline_start �?pipeline_end 事件�?""
    from backend.app.services.agents import langgraph_orchestrator as orch

    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()

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

    class _FakeGenerator:
        def __init__(self, *a, **kw): pass
        def execute(self):
            return {"status": "completed", "pdf_path": str(tmp_path / "out.pdf"), "error_summary": None, "warnings": None}

    monkeypatch.setattr(orch, "ParserAgent", _FakeParser)
    monkeypatch.setattr(orch, "TranslatorAgent", _FakeTranslator)
    monkeypatch.setattr(orch, "ValidatorAgent", _FakeValidator)
    monkeypatch.setattr(orch, "GeneratorAgent", _FakeGenerator)

    (tmp_path / "out.pdf").write_bytes(b"%PDF-1.4")

    with patch("backend.app.services.latex.compiler.verify_pdf_ready", return_value=True):
        asyncio.run(orch.run_pipeline(
            config=minimal_config,
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        ))

    audit_path = output_dir / "zh_proj" / "audit.jsonl"
    assert audit_path.exists()
    events = [json.loads(l)["event"] for l in audit_path.read_text(encoding="utf-8").strip().splitlines()]
    assert "pipeline_start" in events, f"缺少 pipeline_start，got: {events}"
    assert "pipeline_end" in events, f"缺少 pipeline_end，got: {events}"


# ---------------------------------------------------------------------------
# Test 5: Gate 4b-2 �?超时拦截
# ---------------------------------------------------------------------------


def test_pipeline_timeout_raises(monkeypatch, tmp_path, minimal_config):
    """�?graph.ainvoke 超时，应引发 asyncio.TimeoutError�?""
    from backend.app.services.agents import langgraph_orchestrator as orch

    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    # 将超时设置为极小值触�?
    monkeypatch.setattr(orch, "MAX_PIPELINE_TIMEOUT_SEC", 0.001)

    class _SlowParser:
        def __init__(self, *a, **kw): pass
        async def execute(self):
            await asyncio.sleep(10)  # 故意超时

    monkeypatch.setattr(orch, "ParserAgent", _SlowParser)

    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        asyncio.run(orch.run_pipeline(
            config=minimal_config,
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        ))


# ---------------------------------------------------------------------------
# Test 6: Gate 4b-4 / Gate 4b-3 �?架构守护：由 feature flag 严格控制 DiagnosticNode
# ---------------------------------------------------------------------------


def test_diagnostic_node_controlled_by_feature_flag():
    """架构编排必须�?feature flag 严格控制 diagnostic 节点的挂载�?""
    from backend.app.services.agents.langgraph_orchestrator import build_pipeline_graph

    def get_nodes(graph):
        raw = getattr(graph, "_graph", None) or getattr(graph, "graph", None)
        if raw is not None:
            return list(raw.nodes.keys())
        try:
            return list(graph.get_graph().nodes.keys())
        except Exception:
            return []

    # 显式关闭时，绝对禁止混入 diagnostic 节点
    nodes_off = get_nodes(build_pipeline_graph(enable_diagnostics=False))
    diagnostic_nodes_off = [n for n in nodes_off if "diagnostic" in str(n).lower()]
    assert diagnostic_nodes_off == [], (
        f"架构守护失败：feature flag 关闭时发现诊断节�?{diagnostic_nodes_off}"
    )

    # 显式开启时，必须包�?
    nodes_on = get_nodes(build_pipeline_graph(enable_diagnostics=True))
    diagnostic_nodes_on = [n for n in nodes_on if "diagnostic" in str(n).lower()]
    assert diagnostic_nodes_on != [], "feature flag 开启时未能挂载诊断节点"
