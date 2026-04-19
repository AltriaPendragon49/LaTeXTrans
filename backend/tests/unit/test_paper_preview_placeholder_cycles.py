import json
import os
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_preview_service


def test_generate_preview_html_breaks_placeholder_self_reference_cycles(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "30",
            "content": "\\section{Body}\n<PLACEHOLDER_ENV_1>",
            "trans_content": "\\section{正文}\n<PLACEHOLDER_ENV_1>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "quote",
            "content": "\\begin{quote}Example body.\\end{quote}",
            "trans_content": (
                "% [LaTeX-Trans: ultimate downgrade applied - chunk: <PLACEHOLDER_ENV_1>]\n"
                "\\begin{quote}Example body.\\end{quote}"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "Example body." in html
    assert "<PLACEHOLDER_ENV_1>" not in html
