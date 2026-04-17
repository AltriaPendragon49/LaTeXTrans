from __future__ import annotations

import importlib.util
from datetime import datetime
import json
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
            source_mode="hot-top-n",
            source_rank=1,
            publication_date="2026-04-16T17:49:58.000Z",
            updated_at="2026-04-17T01:45:36.126Z",
            source_url="https://www.alphaxiv.org/abs/2604.08377",
            exported_at="2026-04-17T08:00:00Z",
        )
    ]

    module.write_markdown(records, output_path)

    written = output_path.read_text(encoding="utf-8")
    assert "# alphaXiv Papers" in written
    assert "`2604.08377`: SkillClaw" in written
    assert "`hot-top-n`" in written


def test_write_markdown_can_emit_ids_without_titles(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "paper_ids.md"
    records = [
        module.PaperRecord(
            arxiv_id="2604.08377",
            title=None,
            source_mode="new-24h",
            source_rank=None,
            publication_date="2026-04-16T17:49:58.000Z",
            updated_at="2026-04-17T01:45:36.126Z",
            source_url="https://arxiv.org/abs/2604.08377",
            exported_at="2026-04-17T08:00:00Z",
        )
    ]

    module.write_markdown(records, output_path)

    written = output_path.read_text(encoding="utf-8")
    assert "- `2604.08377`" in written
    assert "- `2604.08377`: None" not in written


def test_normalize_alphaxiv_feed_records_filters_invalid_ids_and_assigns_rank() -> None:
    module = _load_module()
    records = module.normalize_alphaxiv_feed_records(
        papers=[
            {
                "universal_paper_id": "2604.08377",
                "title": "SkillClaw",
                "publication_date": "2026-04-16T17:49:58.000Z",
                "updated_at": "2026-04-17T01:45:36.126Z",
            },
            {
                "universal_paper_id": "2604.08377/metadata",
                "title": "Bad route",
                "publication_date": "2026-04-16T17:49:58.000Z",
                "updated_at": "2026-04-17T01:45:36.126Z",
            },
            {
                "universal_paper_id": "2604.08377",
                "title": "Duplicate",
                "publication_date": "2026-04-16T17:49:58.000Z",
                "updated_at": "2026-04-17T01:45:36.126Z",
            },
        ],
        source_mode="hot-top-n",
        exported_at="2026-04-17T08:00:00Z",
    )

    assert [record.arxiv_id for record in records] == ["2604.08377"]
    assert records[0].source_rank == 1
    assert records[0].source_mode == "hot-top-n"
    assert records[0].source_url == "https://www.alphaxiv.org/abs/2604.08377"


def test_parse_arxiv_feed_entries_normalizes_daily_new_records() -> None:
    module = _load_module()
    xml_text = """<?xml version='1.0' encoding='UTF-8'?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2604.15313v1</id>
        <title>Gravitational-wave lensing beyond rays</title>
        <published>2026-04-16T17:59:59Z</published>
        <updated>2026-04-16T17:59:59Z</updated>
      </entry>
    </feed>
    """

    records = module.parse_arxiv_feed_entries(
        xml_text,
        source_mode="new-24h",
        exported_at="2026-04-17T08:00:00Z",
    )

    assert len(records) == 1
    assert records[0].arxiv_id == "2604.15313"
    assert records[0].source_mode == "new-24h"
    assert records[0].source_rank == 1
    assert records[0].source_url == "https://arxiv.org/abs/2604.15313"


def test_write_mode_artifacts_creates_json_and_markdown_outputs(tmp_path: Path) -> None:
    module = _load_module()
    records = [
        module.PaperRecord(
            arxiv_id="2604.08377",
            title="SkillClaw",
            source_mode="hot-top-n",
            source_rank=1,
            publication_date="2026-04-16T17:49:58.000Z",
            updated_at="2026-04-17T01:45:36.126Z",
            source_url="https://www.alphaxiv.org/abs/2604.08377",
            exported_at="2026-04-17T08:00:00Z",
        )
    ]

    paths = module.write_mode_artifacts(records, base_dir=tmp_path, source_mode="hot-top-n")

    assert paths["json"].exists()
    assert paths["markdown"].exists()
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["source_mode"] == "hot-top-n"
    assert payload["count"] == 1
    assert payload["records"][0]["arxiv_id"] == "2604.08377"


def test_default_hot_interval_is_all_time() -> None:
    module = _load_module()
    assert module.DEFAULT_HOT_INTERVAL == "All time"


def test_write_mode_artifacts_overwrites_latest_files(tmp_path: Path) -> None:
    module = _load_module()
    old_record = module.PaperRecord(
        arxiv_id="2604.00001",
        title="Old Paper",
        source_mode="hot-top-n",
        source_rank=1,
        publication_date="2026-04-10T00:00:00Z",
        updated_at="2026-04-10T00:00:00Z",
        source_url="https://www.alphaxiv.org/abs/2604.00001",
        exported_at="2026-04-17T08:00:00Z",
    )
    new_record = module.PaperRecord(
        arxiv_id="2604.00002",
        title="New Paper",
        source_mode="hot-top-n",
        source_rank=1,
        publication_date="2026-04-11T00:00:00Z",
        updated_at="2026-04-11T00:00:00Z",
        source_url="https://www.alphaxiv.org/abs/2604.00002",
        exported_at="2026-04-17T09:00:00Z",
    )

    first_paths = module.write_mode_artifacts([old_record], base_dir=tmp_path, source_mode="hot-top-n")
    second_paths = module.write_mode_artifacts([new_record], base_dir=tmp_path, source_mode="hot-top-n")

    markdown_text = second_paths["markdown"].read_text(encoding="utf-8")
    json_payload = json.loads(second_paths["json"].read_text(encoding="utf-8"))

    assert first_paths == second_paths
    assert "2604.00001" not in markdown_text
    assert "2604.00002" in markdown_text
    assert json_payload["count"] == 1
    assert json_payload["records"][0]["arxiv_id"] == "2604.00002"


def test_write_mode_artifacts_supports_core_pool_directory(tmp_path: Path) -> None:
    module = _load_module()
    record = module.PaperRecord(
        arxiv_id="1706.03762",
        title="Attention Is All You Need",
        source_mode="core-pool",
        source_rank=1,
        publication_date="2017-06-12T00:00:00Z",
        updated_at="2017-06-12T00:00:00Z",
        source_url="https://www.alphaxiv.org/abs/1706.03762",
        exported_at="2026-04-17T12:00:00Z",
        source_family="core",
        translation_priority=2,
        primary_category="cs",
        score=0.98,
        score_breakdown={"views": 0.4, "likes": 0.2, "comments": 0.1, "citations": 0.28},
        selection_bucket="quota:cs",
        selected_reason="high blended score within cs quota",
        citation_count=6525,
        views_count=321000,
        vote_count=4800,
        signal_ranks={"views": 5, "likes": 3, "comments": 2},
    )

    paths = module.write_mode_artifacts([record], base_dir=tmp_path, source_mode="core-pool")

    assert paths["json"].parent.name == "core_pool"
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["source_mode"] == "core-pool"
    assert payload["records"][0]["score_breakdown"]["citations"] == 0.28
    assert payload["records"][0]["views_count"] == 321000
    assert payload["records"][0]["vote_count"] == 4800
    assert payload["records"][0]["signal_ranks"]["likes"] == 3
    assert payload["selection_policy"]["lookback_years"] == module.DEFAULT_CORE_POOL_LOOKBACK_YEARS


def test_infer_submission_date_from_arxiv_id_recovers_2017_landmark_window() -> None:
    module = _load_module()

    assert module.infer_submission_date_from_arxiv_id("1706.03762") == "2017-06-01T00:00:00Z"
    assert module.infer_submission_date_from_arxiv_id("2404.19756") == "2024-04-01T00:00:00Z"


def test_core_pool_openalex_candidates_prefer_arxiv_submission_date_over_openalex_date() -> None:
    module = _load_module()

    assert module.core_pool_publication_date_for_openalex_work(
        "1706.03762",
        {"publication_date": "2025-08-23"},
    ) == "2017-06-01T00:00:00Z"


def test_allocate_category_quotas_enforces_floor_and_capacity() -> None:
    module = _load_module()

    quotas = module.allocate_category_quotas(
        baseline_counts={"cs": 900, "math": 80, "physics": 20},
        available_counts={"cs": 220, "math": 70, "physics": 90},
        target_size=220,
        min_floor=50,
    )

    assert sum(quotas.values()) == 220
    assert quotas["math"] >= 50
    assert quotas["physics"] >= 50
    assert quotas["cs"] <= 220
    assert quotas["math"] <= 70
    assert quotas["physics"] <= 90


def test_build_core_pool_records_excludes_recent_papers_and_exports_score_metadata() -> None:
    module = _load_module()
    candidates: list[object] = []
    for idx in range(120):
        candidates.append(
            module.CorePoolCandidate(
                arxiv_id=f"1801.{idx:05d}",
                title=f"CS Paper {idx}",
                publication_date="2018-01-15T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                source_url=f"https://www.alphaxiv.org/abs/1801.{idx:05d}",
                primary_category="cs",
                signal_ranks={"views": idx + 1, "likes": idx + 1, "comments": idx + 1},
                views_count=20000 - idx,
                vote_count=800 - idx,
                citation_count=1000 - idx,
            )
        )
    for idx in range(80):
        candidates.append(
            module.CorePoolCandidate(
                arxiv_id=f"1901.{idx:05d}",
                title=f"Math Paper {idx}",
                publication_date="2019-01-15T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                source_url=f"https://www.alphaxiv.org/abs/1901.{idx:05d}",
                primary_category="math",
                signal_ranks={"views": idx + 1, "likes": idx + 1},
                views_count=12000 - idx,
                vote_count=400 - idx,
                citation_count=600 - idx,
            )
        )
    for idx in range(90):
        candidates.append(
            module.CorePoolCandidate(
                arxiv_id=f"2001.{idx:05d}",
                title=f"Physics Paper {idx}",
                publication_date="2020-01-15T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                source_url=f"https://www.alphaxiv.org/abs/2001.{idx:05d}",
                primary_category="physics",
                signal_ranks={"views": idx + 1, "comments": idx + 1},
                views_count=9000 - idx,
                vote_count=250 - idx,
                citation_count=450 - idx,
            )
        )
    candidates.append(
        module.CorePoolCandidate(
            arxiv_id="2604.99999",
            title="Too Recent Paper",
            publication_date="2026-04-10T00:00:00Z",
            updated_at="2026-04-10T00:00:00Z",
            source_url="https://www.alphaxiv.org/abs/2604.99999",
            primary_category="cs",
            signal_ranks={"views": 1, "likes": 1, "comments": 1},
            views_count=999999,
            vote_count=9999,
            citation_count=9999,
        )
    )

    records = module.build_core_pool_records(
        candidates,
        baseline_counts={"cs": 900, "math": 80, "physics": 20},
        exported_at="2026-04-17T12:00:00Z",
        target_size=180,
        min_floor=50,
        recent_cutoff_days=90,
        now=datetime.fromisoformat("2026-04-17T12:00:00+00:00"),
    )

    assert len(records) == 180
    assert all(record.source_mode == "core-pool" for record in records)
    assert all(record.primary_category in {"cs", "math", "physics"} for record in records)
    assert all(record.score is not None for record in records)
    assert all(record.score_breakdown for record in records)
    assert all(record.selection_bucket for record in records)
    assert all(record.selected_reason for record in records)
    assert "2604.99999" not in {record.arxiv_id for record in records}
    assert all(record.views_count is not None for record in records)
    assert all(record.vote_count is not None for record in records)
    assert all(record.signal_ranks is not None for record in records)

    category_counts: dict[str, int] = {}
    for record in records:
        category_counts[record.primary_category] = category_counts.get(record.primary_category, 0) + 1

    assert category_counts["math"] >= 50
    assert category_counts["physics"] >= 50


def test_build_core_pool_records_keeps_citation_anchor_landmarks() -> None:
    module = _load_module()
    candidates: list[object] = []

    for idx in range(80):
        candidates.append(
            module.CorePoolCandidate(
                arxiv_id=f"2301.{idx:05d}",
                title=f"Recent CS Paper {idx}",
                publication_date="2023-01-15T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
                source_url=f"https://www.alphaxiv.org/abs/2301.{idx:05d}",
                primary_category="cs",
                signal_ranks={"views": idx + 1, "likes": idx + 1, "comments": idx + 1},
                views_count=50000 - idx,
                vote_count=2000 - idx,
                citation_count=50 - (idx // 2),
            )
        )

    candidates.append(
        module.CorePoolCandidate(
            arxiv_id="1706.03762",
            title="Attention Is All You Need",
            publication_date="2017-06-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            source_url="https://arxiv.org/abs/1706.03762",
            primary_category="cs",
            signal_ranks={"views": 999, "likes": 999, "comments": 999},
            views_count=200,
            vote_count=30,
            citation_count=6525,
        )
    )

    records = module.build_core_pool_records(
        candidates,
        baseline_counts={"cs": 1000},
        exported_at="2026-04-17T12:00:00Z",
        target_size=60,
        min_floor=10,
        recent_cutoff_days=90,
        now=datetime.fromisoformat("2026-04-17T12:00:00+00:00"),
    )

    landmark = next((record for record in records if record.arxiv_id == "1706.03762"), None)
    assert landmark is not None
    assert landmark.selection_bucket in {"citation-anchor:cs", "quota:cs"}
