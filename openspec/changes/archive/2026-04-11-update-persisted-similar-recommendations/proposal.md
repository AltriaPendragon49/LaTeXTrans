# Change: Persist Similar Recommendations During Admin Curation

## Why
The current paper-detail `Similar` panel depends on live arXiv retrieval, so recommendation quality and availability can fluctuate with external network conditions. This makes the reading experience unstable and causes recommendation results to change even when the underlying curated paper has not changed.

## What Changes
- Persist similar-paper recommendations as part of the admin curation completion pipeline, alongside the existing five-module structured insight generation flow.
- Keep the existing recommendation ranking logic unchanged: retrieve station-local and arXiv candidates, merge duplicates, rerank with the current BM25-based scoring, and store the final top 10 results.
- Update the paper-detail similar API to return persisted recommendations for curated papers instead of re-running live search on every request.
- Update the paper-detail Similar UI so each recommendation shows the title by default and reveals the abstract only when the user expands that item.
- Keep community deep-linking and arXiv fallback jump behavior unchanged.
- Do not backfill existing community papers in this change.

## Impact
- Affected specs: `community-admin-curation`, `community-paper-library-storage`, `community-paper-discovery-ui`, `web-api`
- Affected code: `backend/app/services/paper_service.py`, `backend/app/repositories/community_paper_repository.py`, `backend/migrations_mysql/*`, `backend/app/api/routes/papers.py`, `frontend/src/components/community/PaperDetailWorkspace.tsx`, related tests
