# Hot Explanation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add only the compact `Hot`-only explanation row approved in this change.

**Architecture:** Reuse the existing `CommunityFeedSurface` sort/filter area and i18n locale files. The explanation is conditional on `activeTab === "hot"` and sits below `FilterToolbar`, above the feed state container, with tight spacing.

**Tech Stack:** React, TypeScript, TailwindCSS, i18next, Vitest/Testing Library.

---

### Task 1: Hot Explanation Row

**Files:**
- Modify: `frontend/src/features/community-paper/components/CommunityFeedSurface.tsx`
- Modify: `frontend/src/locales/*/common.json`
- Test: `frontend/src/pages/CommunityFeed.test.tsx`

- [x] Step 1: Add semantic i18n key `community.feed.hotExplanation` to every locale.
- [x] Step 2: Render a compact pill-like row only when `activeTab === "hot"`.
- [x] Step 3: Keep the row vertically tight by using small margins (`mt-1` / no extra wrapper gap) and wrapping text safely.
- [x] Step 4: Add a frontend test that verifies the explanation appears on `Hot` and disappears after switching to another sort.
- [x] Step 5: Run `npm run i18n:check`, targeted community feed tests, and `npm run build` from `frontend/`.
- [x] Step 6: Run `scripts\deploy-frontend.ps1` from the repository root.
