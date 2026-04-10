# Processing Page Balance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebalance the translation processing page so the desktop layout feels stable, with a stronger left status column and a dominant but integrated live-log panel.

**Architecture:** Keep all task state and copy logic in the existing processing page. Limit code changes to the page layout, the log viewer sizing hooks, and one focused regression test that locks in the new workbench structure.

**Tech Stack:** React 19, TypeScript, Tailwind CSS, Vitest, Testing Library

---

### Task 1: Lock In The New Structure With A Failing Test

**Files:**
- Modify: `frontend/src/pages/Processing.test.tsx`
- Test: `frontend/src/pages/Processing.test.tsx`

- [x] **Step 1: Add a regression test for the workbench structure**
- [x] **Step 2: Run the focused processing page test and confirm failure**

### Task 2: Rebalance The Processing Page Layout

**Files:**
- Modify: `frontend/src/pages/Processing.tsx`

- [x] **Step 1: Widen the page container and rebalance the desktop grid**
- [x] **Step 2: Strengthen the left summary column while preserving existing copy and states**
- [x] **Step 3: Rework the log card sizing so it stays visually dominant without becoming a narrow pillar**

### Task 3: Make The Log Viewer Fit The New Workbench

**Files:**
- Modify: `frontend/src/components/log-viewer.tsx`

- [x] **Step 1: Add optional className support to the log viewer**
- [x] **Step 2: Let the processing page control log viewport height responsively**

### Task 4: Verify The Change

**Files:**
- Test: `frontend/src/pages/Processing.test.tsx`
- Test: `frontend/package.json`

- [x] **Step 1: Re-run the focused processing page test and confirm pass**
- [x] **Step 2: Run `npm run build` in `frontend/` and confirm the page compiles cleanly**

## Self Review
- Spec coverage: layout balance, stronger status column, dominant integrated log panel, and verification are all covered
- Placeholder scan: no TODO or TBD markers remain
- Type consistency: planned changes stay within existing component boundaries and prop shapes
