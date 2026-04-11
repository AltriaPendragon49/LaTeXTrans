## 1. Specification And Planning
- [x] 1.1 Add OpenSpec proposal, design record, task checklist, and spec deltas for the updated paper-detail behavior.
- [x] 1.2 Validate the OpenSpec change with strict non-interactive validation.
- [x] 1.3 Write an implementation plan under this change for execution tracking.

## 2. Backend
- [x] 2.1 Add an authenticated public paper-detail similar-recommendations API under `/api/papers/{paper_id}/similar`.
- [x] 2.2 Retrieve both station-local and arXiv recommendation candidates, rerank the merged pool with one BM25 pass, and return the top 10 regardless of source origin.
- [x] 2.3 Add backend tests for merged recommendation payload shape, unified BM25 reranking, duplicate merging, and top-10 behavior.

## 3. Frontend Reader And Sidebar
- [x] 3.1 Add failing frontend tests for reader-mode order, translated-PDF default selection, bilingual compare mode, stripped duplicate HTML heading content, reduced sidebar tabs, and collapsed-by-default insights.
- [x] 3.2 Update the detail-page reader control logic to prefer translated PDF first and expose the new bilingual compare mode without changing the overall layout shell.
- [x] 3.3 Strip duplicated title/author content from rendered HTML body output using a conservative leading-duplication heuristic.
- [x] 3.4 Remove the right-pane summary card, keep only `Insights` and `Similar`, and default all insight modules to collapsed.
- [x] 3.5 Add lazy-loaded similar-paper rendering with community deep links and arXiv fallback links.

## 4. Verification
- [x] 4.1 Run strict OpenSpec validation for this change.
- [x] 4.2 Run focused backend and frontend test commands covering the new behaviors.
- [x] 4.3 Update this checklist to reflect the completed implementation state.
