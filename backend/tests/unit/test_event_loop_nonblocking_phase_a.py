import asyncio
import json
import os
import time
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")


async def _tick_probe(duration: float = 0.25, interval: float = 0.01) -> float:
    """
    Measure worst scheduler gap while a target coroutine is running.
    Returns maximum observed interval between ticks.
    """
    loop = asyncio.get_running_loop()
    end_at = loop.time() + duration
    last = loop.time()
    max_gap = 0.0
    while loop.time() < end_at:
        await asyncio.sleep(interval)
        now = loop.time()
        max_gap = max(max_gap, now - last)
        last = now
    return max_gap


def test_parser_execute_does_not_pin_event_loop(monkeypatch, tmp_path):
    """
    Behavior gate:
    parser phase includes a blocking parse() implementation, but event loop
    should stay responsive while ParserAgent.execute() is running.
    """
    from backend.app.services.agents import parser_agent as parser_mod

    class _SlowParser:
        def __init__(self, project_dir, output_dir):
            self.inputs_json = []
            self.envs_json = []
            self.captions_json = []
            self.newcommands_json = []
            self.sections_json = []

        def parse(self, on_progress=None):
            time.sleep(0.30)

    monkeypatch.setattr(parser_mod, "LatexParser", _SlowParser)

    project_dir = tmp_path / "proj"
    output_dir = tmp_path / "out"
    project_dir.mkdir()
    output_dir.mkdir()

    agent = parser_mod.ParserAgent(
        config={"source_language": "en", "target_language": "zh"},
        project_dir=str(project_dir),
        output_dir=str(output_dir),
    )

    async def _run():
        t = asyncio.create_task(agent.execute())
        max_gap = await _tick_probe()
        await t
        return max_gap

    max_gap = asyncio.run(_run())
    assert max_gap < 0.05, f"event loop stalled during parser phase (max_gap={max_gap:.3f}s)"


def test_validate_node_does_not_pin_event_loop(monkeypatch, tmp_path):
    """
    Behavior gate:
    validator execute() may be CPU-heavy; orchestration node must keep loop healthy.
    """
    from backend.app.services.agents import langgraph_orchestrator as orch

    class _SlowValidator:
        def __init__(self, *args, **kwargs):
            self.code_like_filtered_bare_tokens = 0

        def execute(self, *args, **kwargs):
            time.sleep(0.30)
            return []

    class _NoopTranslator:
        structural_fallback_count = 0
        structural_fallback_ratio = 0.0
        structural_fallback_cap = 0.38
        structural_fallback_cap_mode = "soft"
        structural_fallback_parts = []
        noop_sections = []
        c1_retry_enforced_once = False
        structural_fallback_warning = None

        async def execute(self, *args, **kwargs):
            return None

    monkeypatch.setattr(orch, "ValidatorAgent", _SlowValidator)

    transed_project_dir = tmp_path / "zh_proj"
    transed_project_dir.mkdir(parents=True, exist_ok=True)
    (transed_project_dir / "sections_map.json").write_text("[]", encoding="utf-8")
    (transed_project_dir / "envs_map.json").write_text("[]", encoding="utf-8")

    state = {
        "config": {"target_language": "zh"},
        "project_dir": str(tmp_path / "proj"),
        "transed_project_dir": str(transed_project_dir),
        "mode": 0,
        "translator_agent": _NoopTranslator(),
        "base_name": "proj",
        "task_id": "task-1",
        "on_progress": None,
    }

    async def _run():
        t = asyncio.create_task(orch.node_validate_and_retry(state))
        max_gap = await _tick_probe()
        await t
        return max_gap

    max_gap = asyncio.run(_run())
    assert max_gap < 0.05, f"event loop stalled during validate node (max_gap={max_gap:.3f}s)"


def test_parallel_tasks_not_serialized_by_parser_phase(monkeypatch, tmp_path):
    """
    Behavior gate:
    two parser tasks with blocking parse() should complete close to parallel wall time.
    """
    from backend.app.services.agents import parser_agent as parser_mod

    class _SlowParser:
        def __init__(self, project_dir, output_dir):
            self.inputs_json = []
            self.envs_json = []
            self.captions_json = []
            self.newcommands_json = []
            self.sections_json = []

        def parse(self, on_progress=None):
            time.sleep(0.30)

    monkeypatch.setattr(parser_mod, "LatexParser", _SlowParser)

    async def _run_once(idx: int):
        project_dir = tmp_path / f"proj_{idx}"
        output_dir = tmp_path / f"out_{idx}"
        project_dir.mkdir()
        output_dir.mkdir()
        agent = parser_mod.ParserAgent(
            config={"source_language": "en", "target_language": "zh"},
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        )
        await agent.execute()

    async def _run():
        start = time.perf_counter()
        await asyncio.gather(_run_once(1), _run_once(2))
        return time.perf_counter() - start

    elapsed = asyncio.run(_run())
    assert elapsed < 0.50, f"parser tasks look serialized (elapsed={elapsed:.3f}s)"

