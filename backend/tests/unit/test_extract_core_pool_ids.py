from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_module():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "extract_core_pool_ids.py"
    spec = importlib.util.spec_from_file_location("extract_core_pool_ids", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_arxiv_ids_preserves_markdown_order() -> None:
    module = _load_module()
    markdown = """# alphaXiv Papers

- Source mode: `core-pool`

1. `2010.11929`: Vision Transformer
2. `2006.11239`: Diffusion

notes without id
3. `2305.18290`: DPO
"""

    assert module.extract_arxiv_ids(markdown) == [
        "2010.11929",
        "2006.11239",
        "2305.18290",
    ]


def test_write_id_file_defaults_to_sibling_id_md(tmp_path: Path) -> None:
    module = _load_module()
    source_path = tmp_path / "latest.md"
    source_path.write_text(
        "1. `2010.11929`: Vision Transformer\n"
        "2. `2006.11239`: Diffusion\n",
        encoding="utf-8",
    )

    output_path = module.write_id_file(source_path)

    assert output_path == tmp_path / "id.md"
    assert output_path.read_text(encoding="utf-8") == "2010.11929\n2006.11239\n"
