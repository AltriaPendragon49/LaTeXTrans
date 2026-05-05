import asyncio
from pathlib import Path

import pytest

from backend.app.services.agents import langgraph_orchestrator as orch


def test_pipeline_timeout_can_be_disabled(monkeypatch, tmp_path):
    project_dir = tmp_path / "proj"
    output_dir = tmp_path / "out"
    project_dir.mkdir()
    output_dir.mkdir()

    async def _fake_ainvoke(_state):
        return {
            "final_result": {
                "status": "completed",
                "pdf_path": str(Path("dummy.pdf")),
                "error_summary": None,
                "warnings": [],
            }
        }

    class _FakeGraph:
        ainvoke = staticmethod(_fake_ainvoke)

    monkeypatch.setattr(orch, "build_pipeline_graph", lambda **_kwargs: _FakeGraph())

    result = asyncio.run(
            orch.run_pipeline(
            config={"target_language": "zh", "pipeline_timeout_seconds": 0},
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        )
    )

    assert result["status"] == "completed"


def test_pipeline_timeout_still_raises_when_positive(monkeypatch, tmp_path):
    project_dir = tmp_path / "proj"
    output_dir = tmp_path / "out"
    project_dir.mkdir()
    output_dir.mkdir()

    async def _slow_ainvoke(_state):
        await asyncio.sleep(10)
        return {"final_result": {"status": "completed"}}

    class _SlowGraph:
        ainvoke = staticmethod(_slow_ainvoke)

    monkeypatch.setattr(orch, "build_pipeline_graph", lambda **_kwargs: _SlowGraph())

    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        asyncio.run(
            orch.run_pipeline(
                config={"target_language": "zh", "pipeline_timeout_seconds": 0.001},
                project_dir=str(project_dir),
                output_dir=str(output_dir),
            )
        )
