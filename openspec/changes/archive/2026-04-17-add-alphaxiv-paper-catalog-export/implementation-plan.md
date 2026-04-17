# alphaXiv Paper Catalog Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a standalone script that expands the alphaXiv public sitemap index, extracts paper titles and arXiv IDs, and writes a Markdown catalog under `alphaxiv/`.

**Architecture:** Keep the implementation as one standalone Python script under `scripts/` with pure helper functions for sitemap parsing, title extraction, and Markdown rendering. Cover the pure helpers with focused pytest tests, then run the script once against the live site to generate the initial export artifact.

**Tech Stack:** Python stdlib, pytest

---

### Task 1: Lock down parser behavior with tests

**Files:**
- Create: `backend/tests/unit/test_alphaxiv_catalog_export.py`
- Create: `scripts/export_alphaxiv_catalog.py`

- [ ] **Step 1: Write the failing test for sitemap index parsing**

```python
def test_parse_sitemap_index_filters_paper_sitemaps() -> None:
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/test_alphaxiv_catalog_export.py -k sitemap_index -v`
Expected: FAIL because `scripts/export_alphaxiv_catalog.py` or `parse_sitemap_index` does not exist yet.

- [ ] **Step 3: Write the failing tests for title extraction and Markdown output**

```python
def test_extract_title_prefers_og_title_and_strips_suffix() -> None:
    html = """
    <html><head>
      <meta property="og:title" content="Paper Title"/>
      <title>Paper Title | alphaXiv</title>
    </head></html>
    """

    assert module.extract_title_from_html(html) == "Paper Title"


def test_write_markdown_writes_title_id_pairs(tmp_path: Path) -> None:
    output_path = tmp_path / "papers.md"
    records = [module.PaperRecord(arxiv_id="2604.08377", title="SkillClaw", url="https://www.alphaxiv.org/abs/2604.08377")]

    module.write_markdown(records, output_path)

    assert "`2604.08377`: SkillClaw" in output_path.read_text(encoding="utf-8")
```

- [ ] **Step 4: Run the test file to verify the new tests also fail**

Run: `pytest backend/tests/unit/test_alphaxiv_catalog_export.py -v`
Expected: FAIL because the implementation still does not exist.

### Task 2: Implement the standalone export script

**Files:**
- Create: `scripts/export_alphaxiv_catalog.py`

- [ ] **Step 1: Add the minimal implementation for sitemap parsing, title extraction, and Markdown rendering**

```python
def parse_sitemap_index(xml_text: str) -> list[str]:
    ...


def extract_title_from_html(html_text: str) -> str:
    ...


def write_markdown(records: Sequence[PaperRecord], output_path: Path) -> None:
    ...
```

- [ ] **Step 2: Run the targeted test file to verify it passes**

Run: `pytest backend/tests/unit/test_alphaxiv_catalog_export.py -v`
Expected: PASS

- [ ] **Step 3: Add live fetching, retries, concurrency, CLI arguments, and progress logging**

```python
def fetch_text(url: str, *, timeout: int = 20, retries: int = 3) -> str:
    ...


def collect_paper_urls(index_url: str) -> list[str]:
    ...


def collect_paper_records(paper_urls: Sequence[str], workers: int) -> tuple[list[PaperRecord], list[str]]:
    ...
```

- [ ] **Step 4: Re-run the targeted test file**

Run: `pytest backend/tests/unit/test_alphaxiv_catalog_export.py -v`
Expected: PASS

### Task 3: Generate the initial export artifact

**Files:**
- Modify: `alphaxiv/papers.md`
- Modify: `openspec/changes/add-alphaxiv-paper-catalog-export/tasks.md`

- [ ] **Step 1: Run the export script against alphaXiv**

Run: `python scripts/export_alphaxiv_catalog.py`
Expected: progress logs for sitemap expansion and paper page processing, followed by a generated Markdown file under `alphaxiv/`.

- [ ] **Step 2: Verify the output contains title and arXiv ID pairs**

Run: `Get-Content -TotalCount 20 alphaxiv\\papers.md`
Expected: Markdown header plus lines in the form ``- `arxiv_id`: title``.

- [ ] **Step 3: Mark the OpenSpec task checklist complete**

```markdown
- [x] 1.1 Add a standalone script that expands the alphaXiv sitemap index into paper detail URLs
- [x] 1.2 Parse each paper title and arXiv ID and emit a Markdown export under `alphaxiv/`
- [x] 1.3 Add basic retry, timeout, and progress logging for long runs
- [x] 1.4 Run the script once and verify the generated Markdown contains title and ID pairs
```
