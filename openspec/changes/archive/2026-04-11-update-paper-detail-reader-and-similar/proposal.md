# Change: Update Paper Detail Reader Modes and Similar Recommendations

## Why
The current community paper detail page exposes redundant title and author content inside the HTML reading body, uses an outdated reader-mode order and default, keeps low-value sidebar chrome that reduces reading clarity, and does not yet provide the requested similar-paper recommendations workflow.

## What Changes
- Update the paper detail reader controls to use `英文 -> 译文 PDF -> 译文 HTML -> 中英双栏对照` in that order.
- Make translated PDF the default detail-page reader mode whenever it is available, while preserving safe fallback behavior.
- Add a bilingual side-by-side compare mode that shows source PDF on the left and translated PDF on the right inside the existing reader area.
- Strip repeated paper title and author blocks from the top of rendered source HTML body content.
- Reduce the right-side pane to only `Insights` and `Similar`.
- Remove the low-value structured-reading summary card above the insight modules.
- Render the five insight modules collapsed by default.
- Add similar-paper recommendations that retrieve both station-local and arXiv candidates, merge them into one candidate pool, and rerank the combined set with BM25 so the final top results are chosen by score rather than source priority.

## Impact
- Affected specs: `community-public-read-experience`, `community-paper-discovery-ui`, `web-api`
- Affected code: `frontend/src/pages/PaperDetail.tsx`, `frontend/src/components/community/PaperDetailWorkspace.tsx`, `frontend/src/types/community.ts`, `frontend/src/hooks/use-paper-detail.ts`, `frontend/src/lib/community-api.ts`, `backend/app/api/routes/papers.py`, `backend/app/services/paper_service.py`, related tests
