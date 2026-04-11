# Paper Detail Reader And Similar Recommendations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the community paper detail page so it defaults to translated PDF, adds bilingual PDF compare and arXiv-backed similar recommendations, removes redundant right-pane chrome, and strips duplicated title/author content from HTML reading without changing the overall page layout.

**Architecture:** Keep the existing paper-detail shell intact and make localized changes in the current frontend page/component pair plus a small new backend recommendation endpoint. Add tests first for the new behaviors, then implement the smallest backend and frontend deltas needed to satisfy them.

**Tech Stack:** FastAPI, Python, React, TypeScript, Vitest, Testing Library, pytest

---

### Task 1: Document And Validate The Change

**Files:**
- Modify: `openspec/changes/update-paper-detail-reader-and-similar/proposal.md`
- Modify: `openspec/changes/update-paper-detail-reader-and-similar/design.md`
- Modify: `openspec/changes/update-paper-detail-reader-and-similar/tasks.md`
- Modify: `openspec/changes/update-paper-detail-reader-and-similar/specs/community-public-read-experience/spec.md`
- Modify: `openspec/changes/update-paper-detail-reader-and-similar/specs/community-paper-discovery-ui/spec.md`
- Modify: `openspec/changes/update-paper-detail-reader-and-similar/specs/web-api/spec.md`

- [ ] **Step 1: Validate the OpenSpec change**

Run: `openspec validate update-paper-detail-reader-and-similar --strict --no-interactive`
Expected: validation succeeds with no spec-format errors.

### Task 2: Add Backend Failing Tests For Similar Recommendations

**Files:**
- Modify: `backend/tests/unit/test_paper_service.py`
- Modify: `backend/app/services/paper_service.py`
- Modify: `backend/app/api/routes/papers.py`

- [ ] **Step 1: Write the failing backend tests**

Add tests that cover:
- recommendation item normalization to `arxiv_id`, `title`, `abstract`, `arxiv_url`
- current-paper self-filtering
- local `community_paper_id` enrichment when a public community paper shares the candidate `arxiv_id`
- empty-result fallback returning an empty `items` array instead of failing detail-page reads

- [ ] **Step 2: Run the backend tests to verify they fail**

Run: `pytest backend/tests/unit/test_paper_service.py -k similar -v`
Expected: FAIL because the similar-paper service and route do not exist yet.

- [ ] **Step 3: Implement the minimal backend support**

Add:
- a route handler in `backend/app/api/routes/papers.py`
- service helpers in `backend/app/services/paper_service.py`
- normalized response building and local match enrichment by `arxiv_id`

- [ ] **Step 4: Run the backend tests to verify they pass**

Run: `pytest backend/tests/unit/test_paper_service.py -k similar -v`
Expected: PASS for the new similar-paper tests.

### Task 3: Add Frontend Failing Tests For Reader And Sidebar Behavior

**Files:**
- Modify: `frontend/src/pages/PaperDetail.test.tsx`
- Modify: `frontend/src/pages/PaperDetail.reader-first.test.tsx`
- Modify: `frontend/src/components/community/PaperDetailWorkspace.tsx`
- Modify: `frontend/src/pages/PaperDetail.tsx`

- [ ] **Step 1: Write the failing frontend tests**

Add tests that cover:
- reader-mode order `English`, `Chinese translation (PDF)`, `Chinese translation (HTML)`, `Bilingual compare`
- default selection of translated PDF when available
- bilingual compare rendering inside the reader area
- only `Insights` and `Similar` tabs remaining
- all insight accordions collapsed by default
- duplicated HTML title/author lead block not appearing in the reader body

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `pnpm vitest run frontend/src/pages/PaperDetail.test.tsx frontend/src/pages/PaperDetail.reader-first.test.tsx`
Expected: FAIL because the current UI still uses the old mode order, old tabs, expanded insight default, and no bilingual compare mode.

- [ ] **Step 3: Implement the minimal frontend support**

Update:
- mode resolution and default selection in `frontend/src/pages/PaperDetail.tsx`
- sidebar tabs, collapsed insight behavior, similar loading state, and compare mode rendering in `frontend/src/components/community/PaperDetailWorkspace.tsx`
- any supporting types or API calls in `frontend/src/types/community.ts`, `frontend/src/hooks/use-paper-detail.ts`, and `frontend/src/lib/community-api.ts`

- [ ] **Step 4: Run the frontend tests to verify they pass**

Run: `pnpm vitest run frontend/src/pages/PaperDetail.test.tsx frontend/src/pages/PaperDetail.reader-first.test.tsx`
Expected: PASS for the new reader and sidebar behavior tests.

### Task 4: Verify The Focused Change

**Files:**
- Modify: `openspec/changes/update-paper-detail-reader-and-similar/tasks.md`

- [ ] **Step 1: Re-run strict OpenSpec validation**

Run: `openspec validate update-paper-detail-reader-and-similar --strict --no-interactive`
Expected: PASS.

- [ ] **Step 2: Re-run focused backend verification**

Run: `pytest backend/tests/unit/test_paper_service.py -k similar -v`
Expected: PASS.

- [ ] **Step 3: Re-run focused frontend verification**

Run: `pnpm vitest run frontend/src/pages/PaperDetail.test.tsx frontend/src/pages/PaperDetail.reader-first.test.tsx`
Expected: PASS.

- [ ] **Step 4: Mark the OpenSpec task checklist honestly**

Update `openspec/changes/update-paper-detail-reader-and-similar/tasks.md` so each completed item becomes `- [x]`.
