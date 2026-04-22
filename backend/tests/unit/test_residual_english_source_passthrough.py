from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.app.services.agents.langgraph_orchestrator import (
    node_post_compile_target_language_fallback,
)
from backend.app.services.agents.pipeline_schema import FallbackReport


def _write_maps(base_dir: Path, sections: list[dict], envs: list[dict]) -> None:
    (base_dir / "sections_map.json").write_text(
        json.dumps(sections, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (base_dir / "envs_map.json").write_text(
        json.dumps(envs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_post_compile_fallback_uses_source_passthrough_for_residual_english(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    original = (
        r"\subsection{Participants}" + "\n\n"
        + r"Participants were paid \$13.75 for a study expected to last 50 minutes."
    )
    _write_maps(
        out_dir,
        sections=[
            {
                "section": "4_3",
                "content": original,
                "trans_content": (
                    r"\subsection{Participants}" + "\n\n"
                    + r"Participants were paid \textbackslash\{\}$13.75 for a study expected to last 50 minutes."
                ),
                "translation_status": "structural_fallback_pending_compile",
            }
        ],
        envs=[],
    )

    state = {
        "config": {"enable_post_compile_target_language_fallback": True},
        "transed_project_dir": str(out_dir),
        "task_id": "task-residual-english",
        "base_name": "task-residual-english",
        "compile_fallback_reports": [
            FallbackReport(
                fallback_kind="c2_structural_collapse",
                chunk_scope="4_3",
                root_cause="c2",
            )
        ],
        "residual_english_requires_fallback": True,
        "post_compile_fallback_attempted": False,
        "on_progress": None,
    }

    asyncio.run(node_post_compile_target_language_fallback(state))

    sections = json.loads((out_dir / "sections_map.json").read_text(encoding="utf-8"))
    section = sections[0]
    assert section["translation_status"] == "source_pass_through"
    assert section["trans_content"] == original
    assert r"\$13.75" in section["trans_content"]
    assert r"\textbackslash\{\}$13.75" not in section["trans_content"]


def test_post_compile_fallback_also_passthroughs_api_failed_sections_for_residual_english(
    tmp_path: Path,
):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _write_maps(
        out_dir,
        sections=[
            {
                "section": "2_4",
                "content": r"\subsection{Agents}" + "\n\n" + r"Safe source with \(h_t\) and \(\psi\).",
                "trans_content": r"\subsection{坏标题" + "\n\n" + r"broken translated target",
                "translation_status": "structural_fallback_pending_compile",
            },
            {
                "section": "2_5",
                "content": r"\subsection{World models}" + "\n\n" + r"Safe source with \Cref{def:cmp} and \(P_{ss'}(a)\).",
                "trans_content": r"\subsection{World models}" + "\n\n" + r"Broken target (\Cref坏: cmp}) $P_{ss'}(a)",
                "translation_status": "fallback_source_api_failure",
            },
        ],
        envs=[],
    )

    state = {
        "config": {"enable_post_compile_target_language_fallback": True},
        "transed_project_dir": str(out_dir),
        "task_id": "task-residual-expansion",
        "base_name": "task-residual-expansion",
        "compile_fallback_reports": [
            FallbackReport(
                fallback_kind="c2_structural_collapse",
                chunk_scope="2_4",
                root_cause="c2",
            )
        ],
        "residual_english_requires_fallback": True,
        "payload_invariant_sections": ["2_5"],
        "post_compile_fallback_attempted": False,
        "on_progress": None,
    }

    asyncio.run(node_post_compile_target_language_fallback(state))

    sections = json.loads((out_dir / "sections_map.json").read_text(encoding="utf-8"))
    by_id = {section["section"]: section for section in sections}
    assert by_id["2_4"]["translation_status"] == "source_pass_through"
    assert by_id["2_4"]["trans_content"] == by_id["2_4"]["content"]
    assert by_id["2_5"]["translation_status"] == "source_pass_through"
    assert by_id["2_5"]["trans_content"] == by_id["2_5"]["content"]
