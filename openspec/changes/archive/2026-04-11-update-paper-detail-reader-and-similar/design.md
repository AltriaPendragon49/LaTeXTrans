## Context
The existing paper detail shell already provides the correct reader-first page architecture. This change is intentionally constrained to local content and control substitutions inside the current layout. The page must keep its overall theme, left/right hierarchy, and general proportions.

## Goals
- Keep the current paper-detail shell and theme intact.
- Update reader mode ordering and default behavior with minimal UI movement.
- Remove redundant HTML header duplication from rendered article content.
- Simplify the right-side pane to reading-support functions only.
- Introduce similar-paper recommendations by retrieving both station-local and arXiv candidates, then reranking the merged set with BM25 while preserving community-aware link routing for duplicates.

## Non-Goals
- No global redesign of the paper detail page.
- No changes to the overall page split architecture or sidebar placement.
- No vector-based semantic-similarity recommendation engine in this iteration.
- No end-user editing or authoring changes for insight modules.

## Decisions
- Use a separate `GET /api/papers/{paper_id}/similar` endpoint instead of inflating the main paper detail response. This keeps detail-page bootstrap risk low and allows lazy loading when the `Similar` tab is opened.
- Source recommendation candidates from both the local public community library and arXiv official search/query results, then merge and rerank the combined pool with one shared BM25 pass over normalized metadata. Treat any candidate as usable only when it survives stopword filtering and a meaningful lexical-overlap gate, so unrelated papers are not surfaced from weak term collisions.
- Add a new frontend reader mode for bilingual PDF compare while keeping the compare view inside the existing reader area instead of changing the whole page layout.
- Keep insight rendering in the current accordion style but remove the introductory summary card and default all sections to collapsed.
- Sanitize rendered source HTML by removing an initial repeated title/author block only when it mirrors the page metadata, limiting scope to the leading duplicated section.

## Risks / Trade-offs
- Lightweight BM25 over merged local and arXiv metadata is weaker than a dedicated semantic retrieval stack, but it matches the approved scope and avoids the operational cost of vector indexing.
- arXiv retrieval quality may still vary by paper, so the combined ranking depends on the quality of the initial candidate pool that arXiv search returns.
- Removing repeated header content from HTML requires careful heuristics so we do not trim real body text. The implementation should stay conservative and only remove obvious leading duplication.
- Defaulting to translated PDF changes first-open behavior. Fallback logic must remain explicit when translated PDF is unavailable.

## Migration Plan
1. Add spec deltas and implementation plan.
2. Add failing tests for frontend mode behavior, sidebar reduction, default collapsed insights, and similar API contract.
3. Implement backend similar endpoint and frontend integration.
4. Run focused frontend and backend verification.

## Open Questions
- None for this approved scope.
