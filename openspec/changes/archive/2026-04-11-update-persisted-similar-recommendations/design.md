## Context
The current Similar panel calculates recommendations at read time. That makes result stability depend on arXiv availability and on whatever candidate pool arXiv returns at the moment the reader opens the tab. The admin curation pipeline already performs a staged publish gate with structured insights, so it is the natural place to generate and persist the final recommendation package once per newly curated paper.

## Goals
- Generate similar-paper recommendations during admin curation before publication completes.
- Persist the final top 10 recommendations locally and serve them directly on paper detail reads.
- Preserve the current ranking logic and deep-link behavior.
- Reduce reading pressure in the Similar pane by hiding abstracts behind per-item expand controls.

## Non-Goals
- No backfill for existing already-published community papers.
- No change to the current BM25 ranking formula or candidate-merging strategy.
- No redesign of the paper-detail layout or sidebar structure.
- No inline editing or admin override UI for persisted recommendations in this change.

## Decisions
- Add a new local storage table for persisted similar recommendations keyed by `paper_id` plus recommendation rank or recommendation identity.
- Generate recommendations after structured insights succeed and before the curation pipeline marks the paper publish-ready.
- Store the final reranked payload, including `arxiv_id`, title, abstract, `arxiv_url`, `community_paper_id`, `link_type`, and stable display order.
- Return persisted recommendations from `/api/papers/{paper_id}/similar` when they exist; for newly curated papers in scope, this becomes the normal path instead of live retrieval.
- Keep old papers out of scope for backfill. If a legacy paper has no persisted recommendations yet, the product may show the existing empty or unavailable state rather than silently reintroducing live search.
- Render Similar items as accordion-like rows: title always visible, abstract revealed only when the user expands a row, while links remain available from the row content.

## Risks / Trade-offs
- Recommendation freshness is reduced because results are frozen at curation time, but that is acceptable because stability is the primary goal here.
- Persisting abstracts increases local storage footprint, but the payload is small and bounded to 10 items per paper.
- Leaving old papers without backfill means recommendation behavior will differ between legacy and newly curated papers until a future backfill change is introduced.

## Migration Plan
1. Add a MySQL migration for persisted similar recommendations.
2. Add repository read/write methods for the new table.
3. Add a curation-stage write step that computes and stores recommendations after structured insights complete.
4. Update the similar API to read persisted results.
5. Update the Similar panel UI to use expandable abstracts.

## Open Questions
- None for this approved scope.
