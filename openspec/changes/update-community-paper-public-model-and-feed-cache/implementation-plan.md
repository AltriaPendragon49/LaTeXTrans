# Community Paper Public Model And Feed Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the process-local public feed cache with Redis-backed shared feed state, remove public official-vs-fallback semantics from list behavior, and keep viewer engagement hydration request-scoped.

**Architecture:** The backend will keep MySQL as the canonical source of paper metadata and engagement counts, while Redis stores shared sorted indexes plus cacheable anonymous feed payloads for non-search requests. The frontend will stop locally re-imposing official-first semantics and will treat backend order as canonical, with copy and metadata aligned to one public published-paper surface.

**Tech Stack:** FastAPI, Python service/repository layer, optional Redis client, React, Vitest, pytest

---

### Task 1: Backend feed ordering and Redis infrastructure

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/services/paper_service.py`
- Modify: `backend/app/repositories/community_paper_repository.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/unit/test_papers_list_detail_contract.py`

- [ ] Add Redis config and a lightweight feed-cache/index adapter with DB fallback.
- [ ] Remove official-first ordering from repository/service read paths and keep latest/views/likes tie-breaks publication-first.
- [ ] Replace `_PUBLIC_FEED_CACHE` usage with Redis-backed anonymous feed caching for non-search requests.
- [ ] Add hydration-seam coverage and partial ranking refresh coverage in backend tests.

### Task 2: Engagement-triggered partial refresh

**Files:**
- Modify: `backend/app/services/paper_service.py`
- Test: `backend/tests/unit/test_papers_list_detail_contract.py`
- Test: `backend/tests/unit/test_papers_engagement_api.py`

- [ ] Update like/view writes to refresh only affected Redis ranking/cache entries when possible.
- [ ] Keep viewer-specific liked/favorited state out of shared feed cache payloads.
- [ ] Add regression tests for single-paper ranking refresh and cache invalidation behavior.

### Task 3: Frontend public model cleanup

**Files:**
- Modify: `frontend/src/types/community.ts`
- Modify: `frontend/src/features/community-paper/hooks/useCommunityPapers.ts`
- Modify: `frontend/src/features/community-paper/components/PaperStatusBadge.tsx`
- Modify: `frontend/src/features/community-paper/components/PaperDetailHeader.tsx`
- Modify: `frontend/src/pages/home/components/HomeFeedSection.tsx`
- Modify: `frontend/src/lib/community-api.ts`
- Modify: locale files under `frontend/src/locales/*/common.json`
- Test: `frontend/src/features/community-paper/hooks/useCommunityPapers.test.tsx`
- Test: `frontend/src/hooks/use-paper-detail.test.tsx`
- Test: `frontend/src/pages/PaperDetail.test.tsx`

- [ ] Stop frontend types and sorting helpers from depending on public `community_status` semantics.
- [ ] Treat backend order as canonical for list rendering and live engagement reordering.
- [ ] Remove official-first copy and official-published wording from public surfaces.
- [ ] Update tests to reflect the new public model and response contract.

### Task 4: Verification

**Files:**
- Modify: `backend/file.md` if backend file responsibilities change materially

- [ ] Run focused backend pytest coverage for feed ordering, cache behavior, and engagement refresh.
- [ ] Run focused frontend Vitest coverage for hook sorting and public copy changes.
- [ ] Update OpenSpec `tasks.md` checkboxes only after implementation and verification are actually complete.
