# Translated PDF Canonical Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move translated PDF trimming to canonical asset preparation and add an in-place backfill path for existing community papers.

**Architecture:** The backend will generate the final trimmed translated PDF before the asset becomes the latest public community asset. Public preview and download reads will only resolve the prepared asset. Existing papers will be upgraded by a backend backfill script that reuses the same canonicalization helper.

**Tech Stack:** Python, FastAPI, repository-backed paper asset storage, OpenSpec, pytest

---

### Task 1: Regression Tests For Canonical Delivery Preparation

**Files:**
- Modify: `backend/tests/test_paper_service.py`
- Modify: `backend/app/services/paper_service.py`

- [ ] **Step 1: Add a failing test for translated asset persistence**

Write a test that patches the translated-PDF trim helper and asserts `_resolve_translated_pdf_asset()` persists the trimmed output path rather than the raw PDF path.

- [ ] **Step 2: Run the targeted test and verify it fails**

Run: `pytest backend/tests/test_paper_service.py -k canonical_translated_pdf -v`

- [ ] **Step 3: Implement the minimal canonicalization helper changes**

Update the translated asset persistence path to canonicalize once and persist that canonical output as the latest translated asset.

- [ ] **Step 4: Re-run the targeted test and verify it passes**

Run: `pytest backend/tests/test_paper_service.py -k canonical_translated_pdf -v`

### Task 2: Regression Tests For Lightweight Public Reads

**Files:**
- Modify: `backend/tests/test_paper_service.py`
- Modify: `backend/app/services/paper_service.py`

- [ ] **Step 1: Add a failing test for read-time preview resolution**

Write a test that patches the trim helper to raise during `resolve_paper_translated_pdf_preview()` and asserts the preview path succeeds when the stored latest asset already points at the canonical delivery PDF.

- [ ] **Step 2: Run the targeted test and verify it fails**

Run: `pytest backend/tests/test_paper_service.py -k translated_pdf_preview_no_runtime_trim -v`

- [ ] **Step 3: Implement the minimal read-path change**

Update preview/download resolution so canonical translated assets are served directly without re-running trimming.

- [ ] **Step 4: Re-run the targeted test and verify it passes**

Run: `pytest backend/tests/test_paper_service.py -k translated_pdf_preview_no_runtime_trim -v`

### Task 3: Backfill Script For Existing Papers

**Files:**
- Create: `backend/scripts/backfill_translated_pdf_delivery.py`
- Modify: `backend/app/services/paper_service.py`
- Modify: `backend/file.md`

- [ ] **Step 1: Add a failing test for the backfill entry point if a script test pattern already exists, otherwise add a service-level helper test**

Use the existing backend test style to prove the backfill helper skips unrecoverable papers and upgrades recoverable ones in place.

- [ ] **Step 2: Run the targeted test and verify it fails**

Run: `pytest backend/tests/test_paper_service.py -k translated_pdf_backfill -v`

- [ ] **Step 3: Implement the shared backfill helper and CLI wrapper**

Create a script that iterates target papers, regenerates canonical translated assets in place, and reports upgraded versus skipped papers.

- [ ] **Step 4: Update the backend file index**

Add the new script to `backend/file.md` with a Chinese responsibility summary.

- [ ] **Step 5: Re-run the targeted tests and verify they pass**

Run: `pytest backend/tests/test_paper_service.py -k 'translated_pdf_backfill or canonical_translated_pdf or translated_pdf_preview_no_runtime_trim' -v`

### Task 4: Full Verification

**Files:**
- Modify: `openspec/changes/update-translated-pdf-canonical-delivery/tasks.md`

- [ ] **Step 1: Run OpenSpec validation**

Run: `openspec validate update-translated-pdf-canonical-delivery --strict --no-interactive`

- [ ] **Step 2: Run the targeted backend test file**

Run: `pytest backend/tests/test_paper_service.py -v`

- [ ] **Step 3: Mark the OpenSpec task checklist accurately**

Update `openspec/changes/update-translated-pdf-canonical-delivery/tasks.md` so completed items are checked and any incomplete follow-up work remains unchecked.
