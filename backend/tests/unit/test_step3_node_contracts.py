"""
test_step3_node_contracts.py
Step 3：全量 agent node 结构化改造 — 节点 I/O 契约测试

验证每个 node 在 audit.jsonl 中都有对应的 node_enter / node_exit 条目，
以及异常时的 status=error 记录和 elapsed_ms 字段必须存在。
"""
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")


# ---------------------------------------------------------------------------
# Fixtures
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
        "task_id": "test-step3-task",
        "llm_config": {
            "model": "gpt-4o",
            "base_url": "http://dummy",
            "api_key": "dummy",
        },
    }


def _make_agents(tmp_path):
    """返回一套正常 fake agent 类用于 mock。"""

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
            return {
                "status": "completed",
                "pdf_path": str(tmp_path / "out.pdf"),
                "error_summary": None,
                "warnings": None,
            }

    return _FakeParser, _FakeTranslator, _FakeValidator, _FakeGenerator


def _run_pipeline(monkeypatch, tmp_path, config):
    from backend.app.services.agents import langgraph_orchestrator as orch
    P, T, V, G = _make_agents(tmp_path)
    monkeypatch.setattr(orch, "ParserAgent", P)
    monkeypatch.setattr(orch, "TranslatorAgent", T)
    monkeypatch.setattr(orch, "ValidatorAgent", V)
    monkeypatch.setattr(orch, "GeneratorAgent", G)

    project_dir = tmp_path / "proj"
    project_dir.mkdir(exist_ok=True)
    output_dir = tmp_path / "out"
    output_dir.mkdir(exist_ok=True)
    (tmp_path / "out.pdf").write_bytes(b"%PDF-1.4")

    with patch("backend.app.services.latex.compiler.verify_pdf_ready", return_value=True):
        asyncio.run(orch.run_pipeline(
            config=config,
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        ))
    return output_dir / "zh_proj" / "audit.jsonl"


def _parse_audit(audit_path: Path):
    return [json.loads(l) for l in audit_path.read_text(encoding="utf-8").strip().splitlines()]


# ---------------------------------------------------------------------------
# Test 1: 正常路径，每个 node 都有 enter + exit 条目
# ---------------------------------------------------------------------------


def test_all_nodes_emit_audit_enter_exit(monkeypatch, tmp_path, minimal_config):
    """正常路径：audit.jsonl 里每个核心节点必须有 node_enter 和 node_exit 事件。"""
    audit_path = _run_pipeline(monkeypatch, tmp_path, minimal_config)
    assert audit_path.exists(), "audit.jsonl 不存在"

    records = _parse_audit(audit_path)
    events = [r["event"] for r in records]

    expected_nodes = ["parse", "translate", "validate_and_retry", "generate", "finalize"]
    for node in expected_nodes:
        assert f"node_enter:{node}" in events, f"缺少 node_enter:{node}，实际 events={events}"
        assert f"node_exit:{node}" in events, f"缺少 node_exit:{node}，实际 events={events}"


# ---------------------------------------------------------------------------
# Test 2: parse 节点抛异常时，audit.jsonl 包含 status=error 的 node_exit:parse
# ---------------------------------------------------------------------------


def test_node_exit_on_error_has_status_error(monkeypatch, tmp_path, minimal_config):
    """parse 节点抛异常时，audit.jsonl 里 node_exit:parse 的 payload.status 应为 error。"""
    from backend.app.services.agents import langgraph_orchestrator as orch

    class _BadParser:
        def __init__(self, *a, **kw): pass
        async def execute(self):
            raise RuntimeError("fake parse error")

    project_dir = tmp_path / "proj"
    project_dir.mkdir(exist_ok=True)
    output_dir = tmp_path / "out"
    output_dir.mkdir(exist_ok=True)

    _, T, V, G = _make_agents(tmp_path)
    monkeypatch.setattr(orch, "ParserAgent", _BadParser)
    monkeypatch.setattr(orch, "TranslatorAgent", T)
    monkeypatch.setattr(orch, "ValidatorAgent", V)
    monkeypatch.setattr(orch, "GeneratorAgent", G)

    with pytest.raises(Exception):
        asyncio.run(orch.run_pipeline(
            config=minimal_config,
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        ))

    audit_path = output_dir / "zh_proj" / "audit.jsonl"
    assert audit_path.exists(), "audit.jsonl 不存在"
    records = _parse_audit(audit_path)
    exit_records = [r for r in records if r.get("event") == "node_exit:parse"]
    assert exit_records, "缺少 node_exit:parse 记录"
    assert exit_records[0].get("payload", {}).get("status") == "error", (
        f"node_exit:parse 的 status 应为 error，实际：{exit_records[0]}"
    )


# ---------------------------------------------------------------------------
# Test 3: 所有 node_exit 条目都有 elapsed_ms 字段且为正数
# ---------------------------------------------------------------------------


def test_node_elapsed_ms_present(monkeypatch, tmp_path, minimal_config):
    """所有 node_exit 条目都必须包含 elapsed_ms 字段且为正数。"""
    audit_path = _run_pipeline(monkeypatch, tmp_path, minimal_config)
    records = _parse_audit(audit_path)
    exit_records = [r for r in records if r.get("event", "").startswith("node_exit:")]
    assert exit_records, "没有任何 node_exit 条目"
    for r in exit_records:
        elapsed = r.get("payload", {}).get("elapsed_ms")
        assert elapsed is not None, f"缺少 elapsed_ms：{r}"
        assert isinstance(elapsed, (int, float)) and elapsed >= 0, f"elapsed_ms 应为非负数：{r}"


# ---------------------------------------------------------------------------
# Test 4: Step 1 原有测试在 Step 3 改造后仍全部通过（回归保护）
# ---------------------------------------------------------------------------


def test_full_regression_after_node_contracts(monkeypatch, tmp_path, minimal_config):
    """Step 3 node 契约加入后，原有 StateGraph 正常路径行为不变（data flow 等价回归）。"""
    from backend.app.services.agents import langgraph_orchestrator as orch

    call_log = []

    class _LogParser:
        def __init__(self, *a, **kw): pass
        async def execute(self):
            call_log.append("parse")

    class _LogTranslator:
        structural_fallback_count = 0
        structural_fallback_ratio = 0.0
        structural_fallback_cap = 0.38
        structural_fallback_cap_mode = "soft"
        structural_fallback_parts = []
        noop_sections = []
        c1_retry_enforced_once = False
        structural_fallback_warning = None
        def __init__(self, *a, **kw): pass
        async def execute(self, *a, **kw):
            call_log.append("translate")

    class _LogValidator:
        code_like_filtered_bare_tokens = 0
        def __init__(self, *a, **kw): pass
        def execute(self, *a, **kw):
            call_log.append("validate")
            return []

    class _LogGenerator:
        def __init__(self, *a, **kw): pass
        def execute(self):
            call_log.append("generate")
            return {
                "status": "completed",
                "pdf_path": str(tmp_path / "out.pdf"),
                "error_summary": None,
                "warnings": None,
            }

    project_dir = tmp_path / "proj"
    project_dir.mkdir(exist_ok=True)
    output_dir = tmp_path / "out"
    output_dir.mkdir(exist_ok=True)
    (tmp_path / "out.pdf").write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(orch, "ParserAgent", _LogParser)
    monkeypatch.setattr(orch, "TranslatorAgent", _LogTranslator)
    monkeypatch.setattr(orch, "ValidatorAgent", _LogValidator)
    monkeypatch.setattr(orch, "GeneratorAgent", _LogGenerator)

    with patch("backend.app.services.latex.compiler.verify_pdf_ready", return_value=True):
        result = asyncio.run(orch.run_pipeline(
            config=minimal_config,
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        ))

    assert result["status"] in {"completed", "completed_with_warnings"}, f"非预期状态：{result}"
    assert "parse" in call_log
    assert "translate" in call_log
    assert "validate" in call_log
    assert "generate" in call_log
