from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_module():
    module_path = Path(__file__).resolve().parents[3] / "scripts" / "export_alphaxiv_catalog.py"
    spec = importlib.util.spec_from_file_location("export_alphaxiv_catalog", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_sitemap_index_filters_paper_sitemaps() -> None:
    module = _load_module()
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://www.alphaxiv.org/sitemaps/global/1.xml</loc></sitemap>
      <sitemap><loc>https://www.alphaxiv.org/sitemaps/papers/1.xml</loc></sitemap>
      <sitemap><loc>https://www.alphaxiv.org/sitemaps/papers/2.xml</loc></sitemap>
    </sitemapindex>
    """

    assert module.parse_sitemap_index(xml_text) == [
        "https://www.alphaxiv.org/sitemaps/papers/1.xml",
        "https://www.alphaxiv.org/sitemaps/papers/2.xml",
    ]


def test_extract_title_prefers_og_title_and_strips_suffix() -> None:
    module = _load_module()
    html = """
    <html><head>
      <meta property="og:title" content="Paper Title"/>
      <title>Paper Title | alphaXiv</title>
    </head></html>
    """

    assert module.extract_title_from_html(html) == "Paper Title"


def test_parse_paper_sitemap_tolerates_unescaped_ampersands() -> None:
    module = _load_module()
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url>
        <loc>https://www.alphaxiv.org/abs/2502.08235?utm_source=pytorchkr&ref=pytorchkr</loc>
      </url>
    </urlset>
    """

    assert module.parse_paper_sitemap(xml_text) == [
        "https://www.alphaxiv.org/abs/2502.08235?utm_source=pytorchkr&ref=pytorchkr"
    ]


def test_parse_paper_sitemap_skips_non_primary_abs_routes() -> None:
    module = _load_module()
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://www.alphaxiv.org/abs/2604.08377</loc></url>
      <url><loc>https://www.alphaxiv.org/abs/2604.08377/metadata</loc></url>
    </urlset>
    """

    assert module.parse_paper_sitemap(xml_text) == [
        "https://www.alphaxiv.org/abs/2604.08377"
    ]


def test_write_markdown_writes_title_id_pairs(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "papers.md"
    records = [
        module.PaperRecord(
            arxiv_id="2604.08377",
            title="SkillClaw",
            url="https://www.alphaxiv.org/abs/2604.08377",
        )
    ]

    module.write_markdown(records, output_path)

    written = output_path.read_text(encoding="utf-8")
    assert "# alphaXiv Papers" in written
    assert "`2604.08377`: SkillClaw" in written


def test_write_markdown_can_emit_ids_without_titles(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "paper_ids.md"
    records = [
        module.PaperRecord(
            arxiv_id="2604.08377",
            title=None,
            url="https://www.alphaxiv.org/abs/2604.08377",
        )
    ]

    module.write_markdown(records, output_path)

    written = output_path.read_text(encoding="utf-8")
    assert "- `2604.08377`" in written
    assert "- `2604.08377`: None" not in written
