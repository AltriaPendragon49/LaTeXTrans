## 1. Specification
- [x] 1.1 Add OpenSpec proposal, design record, tasks, and spec deltas for persisted similar recommendations generated during admin curation.
- [x] 1.2 Validate the OpenSpec change with strict non-interactive validation.

## 2. Backend Persistence
- [x] 2.1 Add MySQL storage for persisted paper similar recommendations.
- [x] 2.2 Add repository methods to replace and list persisted similar recommendations for one paper.
- [x] 2.3 Generate and persist the final top-10 similar recommendations during admin curation after structured insights succeed and before publication completes.
- [x] 2.4 Update `/api/papers/{paper_id}/similar` to read persisted recommendations for curated papers instead of recomputing live search on each request.
- [x] 2.5 Add backend tests covering persistence, no-backfill legacy behavior, and preserved community/arXiv link routing.

## 3. Frontend Similar Pane
- [x] 3.1 Add failing frontend tests for title-first similar rows with collapsed-by-default abstracts.
- [x] 3.2 Update the Similar panel to render recommendation titles by default and expand abstracts only when the user opens a row.
- [x] 3.3 Keep existing community deep links and arXiv jump behavior unchanged.

## 4. Verification
- [x] 4.1 Run strict OpenSpec validation for this change.
- [x] 4.2 Run focused backend and frontend test commands covering persisted recommendation generation and collapsed abstract display.
- [x] 4.3 Perform an end-to-end verification on a newly curated paper to confirm persisted recommendations are generated before publication and rendered without live-search dependence.
