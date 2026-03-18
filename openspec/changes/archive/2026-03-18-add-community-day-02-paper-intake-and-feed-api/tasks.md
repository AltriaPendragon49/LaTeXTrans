## 1. OpenSpec And Schema Refinement
- [x] 1.1 Update Day 2 proposal/spec/tasks to reflect the official-first, user-fallback community model.
- [x] 1.2 Add `design.md` describing community admission, official override, and the Day 2 schema refinement.
- [x] 1.3 Add an additive migration for `papers.community_status`, community-selected references, and official publication timestamps.

## 2. Backend Implementation
- [x] 2.1 Add `papers.py` route handlers for submit, list, detail, and view APIs.
- [x] 2.2 Add a service layer that reuses existing upload/arXiv capabilities while enforcing community admission rules.
- [x] 2.3 Implement official override behavior for same-`arxiv_id` fallback papers.
- [x] 2.4 Implement list/detail/view queries with official-first ordering and viewer-state enrichment.

## 3. Tests And Validation
- [x] 3.1 Add migration contract coverage for the Day 2 `papers` refinement.
- [x] 3.2 Add submit, override, list/detail, and view tests for the new paper APIs and service logic.
- [x] 3.3 Run the Day 2 test suite.
- [x] 3.4 Run `openspec validate add-community-day-02-paper-intake-and-feed-api --strict --no-interactive`.

## 4. Supabase MCP Application
- [x] 4.1 Apply the Day 2 additive `papers` refinement migration to the main Supabase project.
- [x] 4.2 Verify remote `papers` columns and indexes through Supabase MCP.

## 5. Status Sync
- [x] 5.1 Mark every completed task in this checklist.
- [x] 5.2 Update the Day 2 status in `texts/社区打造十天OpenSpec执行索引.md` after all checklist items are done.
