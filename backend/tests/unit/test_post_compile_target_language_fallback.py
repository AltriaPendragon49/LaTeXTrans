from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.services.agents.langgraph_orchestrator import (
    node_post_compile_target_language_fallback,
)
from backend.app.services.agents.pipeline_schema import FallbackReport
from backend.app.services.latex.reconstruct import LatexConstructor


def _write_maps(base_dir: Path, sections: list[dict], envs: list[dict]) -> None:
    (base_dir / "sections_map.json").write_text(
        json.dumps(sections, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (base_dir / "envs_map.json").write_text(
        json.dumps(envs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_post_compile_fallback_preserves_placeholders_and_target_language(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _write_maps(
        out_dir,
        sections=[
            {
                "section": "3_chunk_1",
                "content": "<PLACEHOLDER_ENV_1>Hello world<PLACEHOLDER_CAP_2>",
                "trans_content": "<PLACEHOLDER_ENV_1>你好世界<PLACEHOLDER_CAP_2>",
                "translation_status": "structural_fallback_pending_compile",
            }
        ],
        envs=[],
    )

    state = {
        "config": {"enable_post_compile_target_language_fallback": True},
        "transed_project_dir": str(out_dir),
        "task_id": "task-1",
        "base_name": "task-1",
        "compile_fallback_reports": [
            FallbackReport(
                fallback_kind="c2_structural_collapse",
                chunk_scope="3_chunk_1",
                root_cause="c2",
            )
        ],
        "post_compile_fallback_attempted": False,
        "on_progress": None,
    }

    new_state = asyncio.run(node_post_compile_target_language_fallback(state))

    sections = json.loads((out_dir / "sections_map.json").read_text(encoding="utf-8"))
    section = sections[0]
    assert section["translation_status"] == "final_target_language_fallback_applied"
    assert "<PLACEHOLDER_ENV_1>" in section["trans_content"]
    assert "<PLACEHOLDER_CAP_2>" in section["trans_content"]
    assert "你好世界" in section["trans_content"]
    assert "Hello world" not in section["trans_content"]
    assert new_state["post_compile_fallback_attempted"] is True

    task_log = json.loads((out_dir / "task_log.json").read_text(encoding="utf-8"))
    events = [entry["event"] for entry in task_log]
    assert "post_compile_target_language_fallback_started" in events
    assert "post_compile_target_language_fallback_completed" in events
    assert "compile_retry_after_target_language_fallback" in events


def test_post_compile_fallback_marks_empty_target_as_failed(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _write_maps(
        out_dir,
        sections=[
            {
                "section": "4_chunk_1",
                "content": "Original english",
                "trans_content": "",
                "translation_status": "structural_fallback_pending_compile",
            }
        ],
        envs=[],
    )

    state = {
        "config": {"enable_post_compile_target_language_fallback": True},
        "transed_project_dir": str(out_dir),
        "task_id": "task-2",
        "base_name": "task-2",
        "compile_fallback_reports": [
            FallbackReport(
                fallback_kind="c1_structural_rollback",
                chunk_scope="4_chunk_1",
                root_cause="c1",
            )
        ],
        "post_compile_fallback_attempted": False,
        "on_progress": None,
    }

    asyncio.run(node_post_compile_target_language_fallback(state))

    sections = json.loads((out_dir / "sections_map.json").read_text(encoding="utf-8"))
    section = sections[0]
    assert section["translation_status"] == "final_target_language_fallback_failed"
    assert section["trans_content"] == ""


def test_post_compile_fallback_reconstruction_keeps_target_language_section_body(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _write_maps(
        out_dir,
        sections=[
            {
                "section": "2_3",
                "content": r"\subsection{Setup}" + "\n\n"
                + "For the purposes of this study, we consider a rectangular domain.",
                "trans_content": r"\subsection{实验设置}" + "\n\n"
                + "在本研究中，我们考虑一个矩形海域�?,
                "translation_status": "structural_fallback_pending_compile",
            },
            {
                "section": "3",
                "content": r"\section{Results}" + "\n\n"
                + "We begin by examining the left panel of Figure 1.",
                "trans_content": r"\section{结果}" + "\n\n"
                + "我们首先考察�?的左侧面板�?,
                "translation_status": "structural_fallback_pending_compile",
            },
            {
                "section": "4",
                "content": r"\section{Discussion}" + "\n\n"
                + "The Reef-building larvae show substantial variation.",
                "trans_content": r"\section{讨论}" + "\n\n"
                + "造礁珊瑚幼虫表现出显著的差异�?,
                "translation_status": "structural_fallback_pending_compile",
            },
        ],
        envs=[],
    )

    state = {
        "config": {"enable_post_compile_target_language_fallback": True},
        "transed_project_dir": str(out_dir),
        "task_id": "task-3",
        "base_name": "task-3",
        "compile_fallback_reports": [
            FallbackReport(fallback_kind="c2_structural_collapse", chunk_scope="2_3", root_cause="c2"),
            FallbackReport(fallback_kind="c2_structural_collapse", chunk_scope="3", root_cause="c2"),
            FallbackReport(fallback_kind="c1_structural_rollback", chunk_scope="4", root_cause="c1"),
        ],
        "post_compile_fallback_attempted": False,
        "on_progress": None,
    }

    asyncio.run(node_post_compile_target_language_fallback(state))

    sections = json.loads((out_dir / "sections_map.json").read_text(encoding="utf-8"))
    constructor = LatexConstructor(
        sections=sections,
        captions=[],
        envs=[],
        inputs=[],
        newcommands=[],
        output_latex_dir=str(out_dir),
    )
    merged_tex = constructor._merge_sections()

    assert r"\subsection{实验设置}" in merged_tex
    assert r"\section{结果}" in merged_tex
    assert r"\section{讨论}" in merged_tex
    assert "For the purposes of this study" not in merged_tex
    assert "We begin by examining" not in merged_tex
    assert "The Reef-building larvae" not in merged_tex
