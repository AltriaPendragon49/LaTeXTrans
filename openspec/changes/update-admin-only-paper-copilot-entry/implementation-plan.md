# Admin-Only Paper Copilot Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the retained Paper Copilot UI only for admins, protect `/agent` routes for non-admin users, and moderately polish the conversation workspace visuals.

**Architecture:** Reuse the existing frontend admin-role helper as the single source of truth for sidebar visibility and route gating. Keep the current conversation workspace structure intact while refining visual treatment in the rail, header, thread, and composer components.

**Tech Stack:** React, React Router, Tailwind CSS, Vitest, Testing Library

---

### Task 1: Add admin-only Paper Copilot navigation and route protection

**Files:**
- Modify: `frontend/src/layout/AppSidebar.tsx`
- Modify: `frontend/src/pages/community-conversation/index.tsx`
- Test: `frontend/src/layout/AppSidebar.community-shell.test.tsx`
- Test: `frontend/src/pages/CommunityConversation.test.tsx`

- [ ] **Step 1: Write the failing sidebar and route-access tests**

Add assertions that admins see `Paper Copilot` below `Paper Tool`, non-admin users do not see it, guests navigating to `/agent/:conversationId` are redirected to login, and authenticated non-admin users are redirected to `/tools`.

- [ ] **Step 2: Run the targeted tests to verify the new expectations fail**

Run: `npm test -- AppSidebar.community-shell.test.tsx CommunityConversation.test.tsx`
Expected: FAIL because the current shell does not render the new admin-only entry and `/agent` is not admin-gated.

- [ ] **Step 3: Implement the minimal access-control changes**

Use `hasAdminRole(user?.roles)` in the sidebar to render the new nav item immediately after `Paper Tool`, then add page-level redirects in the conversation route entry so guests go to `/login` and authenticated non-admin users go to `/tools`.

- [ ] **Step 4: Re-run the targeted tests**

Run: `npm test -- AppSidebar.community-shell.test.tsx CommunityConversation.test.tsx`
Expected: PASS for navigation visibility and route-protection coverage.

### Task 2: Polish the retained Paper Copilot workspace

**Files:**
- Modify: `frontend/src/features/community-conversation/components/CommunityConversationWorkspace.tsx`
- Modify: `frontend/src/features/community-conversation/components/ConversationRail.tsx`
- Modify: `frontend/src/features/community-conversation/components/ConversationThread.tsx`
- Modify: `frontend/src/features/community-conversation/components/ConversationComposer.tsx`
- Test: `frontend/src/pages/CommunityConversation.test.tsx`

- [ ] **Step 1: Extend or adjust rendering tests for the refined workspace**

Add assertions around visible Paper Copilot labeling and preserved composer/chat affordances so the style refresh still preserves the current structure and actions.

- [ ] **Step 2: Run the conversation-page test slice before styling changes**

Run: `npm test -- CommunityConversation.test.tsx`
Expected: PASS for current behavior before the visual refresh.

- [ ] **Step 3: Apply the moderate visual refresh**

Keep the rail-plus-main-panel structure, but improve header hierarchy, metadata chips, chat-bubble framing, composer shell, and supporting gradients/borders to produce a more polished admin-facing workspace.

- [ ] **Step 4: Re-run the conversation-page tests**

Run: `npm test -- CommunityConversation.test.tsx`
Expected: PASS with unchanged behavior and preserved accessibility labels.

### Task 3: Final verification

**Files:**
- Modify: `openspec/changes/update-admin-only-paper-copilot-entry/tasks.md`

- [ ] **Step 1: Run the full targeted verification command**

Run: `npm test -- AppSidebar.community-shell.test.tsx CommunityConversation.test.tsx`
Expected: PASS with zero failing tests.

- [ ] **Step 2: Mark the OpenSpec tasks that are now complete**

Update `openspec/changes/update-admin-only-paper-copilot-entry/tasks.md` so completed implementation and verification items are checked truthfully after verification finishes.
