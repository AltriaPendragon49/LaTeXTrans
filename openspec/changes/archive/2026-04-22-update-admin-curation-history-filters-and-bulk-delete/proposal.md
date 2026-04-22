# Change: Fix admin curation history filters and add bulk delete

## Why
The admin curation history page currently treats the `all` filter value as a literal status, which makes the default history view appear empty even when records exist. The page also only supports one-by-one hard deletion, which makes large-scale cleanup slow for admins working through batches of retained completed and failed curation jobs.

## What Changes
- Normalize admin curation history filters so every visible filter option maps to the intended backend query semantics.
- Expand the `processing` history filter to include `processing`, `translating`, and `publishing` jobs.
- Add admin batch hard-delete support for selected curation jobs within the currently filtered history result set.
- Add frontend multi-select controls for history records, including current-result selection and a batch delete confirmation flow.

## Impact
- Affected specs: `community-admin-curation`, `web-api`, `web-ui`
- Affected code: `backend/app/api/routes/papers.py`, `backend/app/services/paper_service.py`, `backend/app/repositories/community_paper_repository.py`, `frontend/src/pages/CommunityAdminCurationTasks.tsx`, `frontend/src/lib/community-api.ts`, `frontend/src/types/community.ts`, related tests and locale files
