import asyncio
import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")


class _FakeProc:
    def __init__(self, pid: int, on_communicate=None):
        self.pid = pid
        self.returncode = 0
        self._on_communicate = on_communicate

    async def communicate(self):
        if self._on_communicate:
            await self._on_communicate()
        return b"", b""

    async def wait(self):
        return self.returncode


def _write_tex(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")


def test_compile_latex_async_cancel_kills_process_tree(monkeypatch, tmp_path):
    from backend.app.services.latex import compiler

    tex = tmp_path / "p" / "main.tex"
    out = tmp_path / "out"
    _write_tex(tex)
    out.mkdir(parents=True, exist_ok=True)

    killed = {"called": False}

    async def _slow_communicate():
        await asyncio.sleep(5)

    async def _spawn(*args, **kwargs):
        return _FakeProc(pid=4321, on_communicate=_slow_communicate)

    async def _terminate(proc):
        killed["called"] = True

    monkeypatch.setattr(compiler, "_spawn_latex_process_async", _spawn)
    monkeypatch.setattr(compiler, "_terminate_process_tree_and_wait", _terminate)

    seen_start = {"pid": None}
    seen_end = {"count": 0}

    async def _run():
        task = asyncio.create_task(
            compiler.compile_latex_async(
                str(tex),
                str(out),
                engine="pdflatex",
                on_process_start=lambda pid, eng: seen_start.__setitem__("pid", pid),
                on_process_end=lambda: seen_end.__setitem__("count", seen_end["count"] + 1),
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(_run())
    assert seen_start["pid"] == 4321
    assert killed["called"], "cancel path must terminate subprocess tree"
    assert seen_end["count"] == 1, "on_process_end must run exactly once on cancellation"


def test_compile_latex_async_timeout_kills_process_tree(monkeypatch, tmp_path):
    from backend.app.services.latex import compiler

    tex = tmp_path / "p" / "main.tex"
    out = tmp_path / "out"
    _write_tex(tex)
    out.mkdir(parents=True, exist_ok=True)

    async def _slow_communicate():
        await asyncio.sleep(1.0)

    async def _spawn(*args, **kwargs):
        return _FakeProc(pid=9876, on_communicate=_slow_communicate)

    killed = {"called": False}

    async def _terminate(proc):
        killed["called"] = True

    monkeypatch.setattr(compiler, "_spawn_latex_process_async", _spawn)
    monkeypatch.setattr(compiler, "_terminate_process_tree_and_wait", _terminate)

    result = asyncio.run(
        compiler.compile_latex_async(
            str(tex),
            str(out),
            engine="pdflatex",
            compilation_timeout=0,
        )
    )
    assert result.success is False
    assert result.exit_code == -2
    assert killed["called"], "timeout path must terminate subprocess tree"


def test_node_generate_no_longer_serializes_full_generator(monkeypatch, tmp_path):
    from backend.app.services.agents import langgraph_orchestrator as orch

    timeline = []

    class _FakeGenerator:
        def __init__(self, *args, **kwargs):
            pass

        async def execute_async(self):
            timeline.append(("start", time.perf_counter()))
            await asyncio.sleep(0.15)
            timeline.append(("end", time.perf_counter()))
            return {
                "status": "failed_compilation",
                "pdf_path": None,
                "error_summary": "x",
                "warnings": None,
                "engine": "xelatex",
                "error_count": 1,
            }

    monkeypatch.setattr(orch, "GeneratorAgent", _FakeGenerator)
    monkeypatch.setattr(orch, "_write_audit_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(orch, "_write_stage_failed_log", lambda *args, **kwargs: None)

    class _TM:
        def set_compile_runtime(self, *args, **kwargs):
            return True

    monkeypatch.setattr("backend.app.services.task_manager.task_manager", _TM())

    base_dir = tmp_path / "out"
    base_dir.mkdir(parents=True, exist_ok=True)
    state1 = {
        "transed_project_dir": str(base_dir / "t1"),
        "project_dir": str(tmp_path / "p1"),
        "config": {},
        "task_id": "t1",
        "base_name": "b1",
        "on_progress": None,
    }
    state2 = {
        "transed_project_dir": str(base_dir / "t2"),
        "project_dir": str(tmp_path / "p2"),
        "config": {},
        "task_id": "t2",
        "base_name": "b2",
        "on_progress": None,
    }
    Path(state1["transed_project_dir"]).mkdir(parents=True, exist_ok=True)
    Path(state2["transed_project_dir"]).mkdir(parents=True, exist_ok=True)

    async def _run():
        await asyncio.gather(orch.node_generate(state1), orch.node_generate(state2))

    asyncio.run(_run())
    starts = [t for k, t in timeline if k == "start"]
    ends = [t for k, t in timeline if k == "end"]
    assert len(starts) == 2 and len(ends) == 2
    assert starts[1] < ends[0], "node_generate should not serialize the entire generator flow"


def test_async_intelligent_fallback_uses_async_compile_path_and_preserves_selection(monkeypatch, tmp_path):
    from backend.app.services.latex import compiler
    from backend.app.core import config as app_config

    monkeypatch.setattr(app_config.settings, "async_compiler_enabled", True, raising=False)

    tex = tmp_path / "paper" / "TRODO.tex"
    out = tmp_path / "out"
    _write_tex(tex)
    out.mkdir(parents=True, exist_ok=True)

    calls = {"engines": [], "sync_called": False}

    def _should_not_call_sync(*args, **kwargs):
        calls["sync_called"] = True
        raise AssertionError("sync fallback path should not run when async compiler is enabled")

    async def _fake_compile_latex_async(
        tex_file,
        output_dir,
        engine="pdflatex",
        max_runs=2,
        *,
        on_process_start=None,
        on_process_end=None,
        compilation_timeout=300,
    ):
        calls["engines"].append(engine)
        if on_process_start:
            on_process_start(1000 + len(calls["engines"]), engine)
        try:
            stem = Path(tex_file).stem
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            log_path = out_dir / f"{stem}.log"
            log_path.write_text("mock log", encoding="utf-8")
            if engine == "lualatex":
                pdf_path = out_dir / f"{stem}.pdf"
                pdf_path.write_bytes(b"%PDF-1.4\n")
                return compiler.CompilationResult(
                    success=False,
                    pdf_path=str(pdf_path),
                    log_path=str(log_path),
                    error_count=1,
                    errors=["minor warning-level compile error"],
                    exit_code=1,
                )
            return compiler.CompilationResult(
                success=False,
                pdf_path=None,
                log_path=str(log_path),
                error_count=2,
                errors=["harder compile errors"],
                exit_code=1,
            )
        finally:
            if on_process_end:
                on_process_end()

    monkeypatch.setattr(compiler, "compile_with_intelligent_fallback", _should_not_call_sync)
    monkeypatch.setattr(compiler, "compile_latex_async", _fake_compile_latex_async)
    monkeypatch.setattr(compiler, "_upgrade_outdated_cls_files", lambda _tex_dir: None)

    async def _run():
        return await compiler.compile_with_intelligent_fallback_async(
            tex_file=str(tex),
            output_dir=str(out),
            preferred_order=["xelatex", "lualatex"],
            target_language="ja",
        )

    result = asyncio.run(_run())
    assert calls["sync_called"] is False
    assert calls["engines"], "async compiler path must invoke compile_latex_async"
    assert result["status"] == "completed_with_warnings"
    assert result["engine"] == "lualatex"
    assert result["pdf_path"]
    assert Path(result["pdf_path"]).exists()
