from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.scripts.audit_pipeline_regression import _artifact_summary


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_artifact_summary_flags_long_english_in_final_main_tex(tmp_path: Path):
    out_dir = tmp_path / "bundle"
    out_dir.mkdir()

    _write_json(
        out_dir / "sections_map.json",
        [
            {
                "section": "1",
                "content": r"\section{Results} English source.",
                "trans_content": r"\section{结果} 中文译文�?,
            }
        ],
    )
    _write_json(out_dir / "envs_map.json", [])
    _write_json(out_dir / "captions_map.json", [])
    _write_json(out_dir / "newcommands_map.json", [])
    _write_json(out_dir / "inputs_map.json", [])
    _write_json(out_dir / "errors_report.json", [])

    long_english = (
        "This final tex still contains a long English paragraph that should be "
        "reported by the audit because it survived reconstruction into the "
        "document body after translation and fallback processing."
    )
    (out_dir / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\section{结果}\n"
        "中文正文。\n\n"
        f"{long_english}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    summary = _artifact_summary(out_dir)

    assert summary["long_english_span_count"] == 0
    assert summary["main_tex_long_english_span_count"] >= 1
    assert summary["main_tex_long_english_span_samples"]
