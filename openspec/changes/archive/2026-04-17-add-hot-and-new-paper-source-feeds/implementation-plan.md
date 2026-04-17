# Hot And New Paper Source Feeds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing paper export script so it can generate reusable `hot` and `new` source artifacts under `backend/arxiv_id/` for both human review and downstream automation.

**Architecture:** Keep the work in the existing `scripts/export_alphaxiv_catalog.py` entrypoint, but refactor it around a shared normalized record schema plus mode-specific fetchers for alphaXiv hot feeds and arXiv submitted-date queries. Cover the normalization, filtering, output-path resolution, and artifact-writing behavior with focused pytest tests before running live exports.

**Tech Stack:** Python stdlib, pytest

---

### Task 1: Lock down the new source-feed behavior with tests

**Files:**
- Modify: `backend/tests/unit/test_alphaxiv_catalog_export.py`
- Modify: `scripts/export_alphaxiv_catalog.py`

- [ ] **Step 1: Add a failing test for alphaXiv hot-feed normalization**

```python
def test_normalize_alphaxiv_feed_records_filters_invalid_ids_and_assigns_rank() -> None:
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
            },
        ],
        source_mode="hot-top-n",
    )

    assert [record.arxiv_id for record in records] == ["2604.08377"]
    assert records[0].source_rank == 1
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `pytest backend/tests/unit/test_alphaxiv_catalog_export.py -k normalize_alphaxiv -v`
Expected: FAIL because the normalization function and richer record shape do not exist yet.

- [ ] **Step 3: Add a failing test for output path resolution and dual artifact writing**

```python
def test_write_mode_artifacts_creates_json_and_markdown_outputs(tmp_path: Path) -> None:
    record = module.PaperRecord(...)
    paths = module.write_mode_artifacts([record], base_dir=tmp_path, source_mode="hot-top-n")

    assert paths["json"].exists()
    assert paths["markdown"].exists()
```

- [ ] **Step 4: Add a failing test for arXiv daily-new parsing**

```python
def test_parse_arxiv_feed_entries_normalizes_daily_new_records() -> None:
    xml_text = \"\"\"...\"\"\"
    records = module.parse_arxiv_feed_entries(xml_text, source_mode="new-24h")
    assert records[0].source_mode == "new-24h"
```

- [ ] **Step 5: Run the full targeted test file to verify the new tests fail for the expected reasons**

Run: `pytest backend/tests/unit/test_alphaxiv_catalog_export.py -v`
Expected: FAIL because the new behavior is not implemented yet.

### Task 2: Implement the reusable mode-based export workflow

**Files:**
- Modify: `scripts/export_alphaxiv_catalog.py`

- [ ] **Step 1: Add a shared normalized record schema and validation helpers**

```python
@dataclass(frozen=True, order=True)
class PaperRecord:
    arxiv_id: str
    title: str | None
    source_mode: str
    source_rank: int | None
    publication_date: str | None
    updated_at: str | None
    source_url: str
    exported_at: str
```

- [ ] **Step 2: Implement alphaXiv hot-feed normalization and arXiv daily-new parsing**

Run: `pytest backend/tests/unit/test_alphaxiv_catalog_export.py -k "normalize_alphaxiv or parse_arxiv" -v`
Expected: PASS

- [ ] **Step 3: Implement output-path resolution plus JSON and Markdown artifact writing under `backend/arxiv_id/`**

Run: `pytest backend/tests/unit/test_alphaxiv_catalog_export.py -k "write_mode_artifacts or markdown" -v`
Expected: PASS

- [ ] **Step 4: Wire the CLI to support `hot-top-n`, `hot-new-24h`, and `new-24h` modes**

Run: `pytest backend/tests/unit/test_alphaxiv_catalog_export.py -v`
Expected: PASS

### Task 3: Generate representative live artifacts

**Files:**
- Modify: `backend/arxiv_id/all_hot/`
- Modify: `backend/arxiv_id/daily_hot/`
- Modify: `backend/arxiv_id/daily_new/`
- Modify: `openspec/changes/add-hot-and-new-paper-source-feeds/tasks.md`

- [ ] **Step 1: Run a representative hot export**

Run: `python scripts/export_alphaxiv_catalog.py --mode hot-top-n --limit 10000`
Expected: JSON and Markdown artifacts under `backend/arxiv_id/all_hot/`

- [ ] **Step 2: Run a representative daily hot export**

Run: `python scripts/export_alphaxiv_catalog.py --mode hot-new-24h`
Expected: JSON and Markdown artifacts under `backend/arxiv_id/daily_hot/`

- [ ] **Step 3: Run a representative daily new export**

Run: `python scripts/export_alphaxiv_catalog.py --mode new-24h`
Expected: JSON and Markdown artifacts under `backend/arxiv_id/daily_new/`

- [ ] **Step 4: Verify the generated artifacts**

Run: `Get-ChildItem backend\\arxiv_id\\all_hot,backend\\arxiv_id\\daily_hot,backend\\arxiv_id\\daily_new`
Expected: fresh Markdown and JSON files in each target directory

- [ ] **Step 5: Mark the OpenSpec checklist complete**

```markdown
- [x] 1.1 Add reusable source modes for `hot-top-n`, `hot-new-24h`, and `new-24h` to the export script
- [x] 1.2 Normalize alphaXiv and arXiv records into one shared schema keyed by `arxiv_id`
- [x] 1.3 Write Markdown and JSON outputs under `backend/arxiv_id/all_hot`, `backend/arxiv_id/daily_hot`, and `backend/arxiv_id/daily_new`, creating missing directories automatically
- [x] 1.4 Filter malformed IDs and de-duplicate records within each export run
- [x] 1.5 Encode source-priority metadata so downstream workflows can prefer `hot` and reuse already translated `new` papers without re-translation
- [x] 1.6 Run the script for representative hot and new modes and verify the generated artifacts
```
