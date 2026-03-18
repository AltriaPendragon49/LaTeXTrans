import json
import os
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_preview_service


def test_generate_preview_html_writes_semantic_reader_output(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "-1",
            "content": "\\documentclass{article}",
            "trans_content": "\\documentclass{article}",
        },
        {
            "section": "1",
            "content": "\\section{Introduction}\nFirst paragraph.\n\n<PLACEHOLDER_ENV_1>",
            "trans_content": "\\section{引言}\n第一段。\n\n<PLACEHOLDER_ENV_1>",
        },
        {
            "section": "1_1",
            "content": "\\subsection{Method}\nSecond paragraph with $E=mc^2$.",
            "trans_content": "\\subsection{方法}\n第二段包含 $E=mc^2$。",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "equation",
            "content": "\\begin{equation}a=b\\end{equation}",
            "trans_content": "\\begin{equation}a=b\\end{equation}",
        }
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert result["asset_type"] == "preview_html"
    assert "<h2" in html
    assert "引言" in html
    assert "<h3" in html
    assert "方法" in html
    assert "<p>第一段。</p>" in html
    assert "\\begin{equation}a=b\\end{equation}" in html
    assert "$E=mc^2$" in html
