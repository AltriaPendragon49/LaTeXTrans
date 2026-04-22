# Change: Add community-paper engagement and sorting

## Why
Community papers currently expose placeholder or incomplete engagement behavior: favorites are not folder-based, likes are not implemented as a persistent user interaction, view counts are incremented without the requested de-duplication rules, and the homepage sort model still reflects outdated `hot` / `translated` options. The product now needs authenticated, backend-persisted engagement that remains consistent across refreshes, re-login, and other viewers.

## What Changes
- Add authenticated, folder-based favorites for community papers only, including sidebar entry, favorites workspace, folder management, and multi-folder assignment from feed cards and paper detail.
- Add persistent one-user-one-like toggles for community-paper feed cards with clear active/inactive feedback and durable like counts.
- Replace the current placeholder view-count behavior with detail-entry-only counting plus per-day de-duplication for authenticated users and anonymous principals.
- Replace homepage sort options with `latest`, `views`, and `likes`, using original arXiv publication time as the shared tie-breaker.
- Extend backend contracts and schema constraints so engagement state and aggregate counters are served from persisted backend data rather than frontend-local state.

## Impact
- Affected specs: `community-paper-engagement` (new), `community-paper-discovery-ui`, `community-schema-foundation`
- Affected code: `backend/app/api/routes/papers.py`, `backend/app/services/paper_service.py`, `backend/app/repositories/community_paper_repository.py`, community-paper schema migrations, frontend community sidebar/feed/detail routes and components, community API client/types/i18n/tests, `backend/file.md`
