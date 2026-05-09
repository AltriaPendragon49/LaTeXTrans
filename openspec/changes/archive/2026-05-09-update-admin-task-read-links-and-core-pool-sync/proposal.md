# Change: Admin task read links and core-pool COS sync

## Why
Admins need a direct way to jump from completed curation-task history into the paper reading experience. Operators also need a local script that can pull `core_pool/complete.md` assets from COS into a local arXiv-ID-based reading directory for offline or local verification.

## What Changes
- Add a direct read action for completed admin curation history records.
- Add a backend script that reads `backend/arxiv_id/core_pool/complete.md` and syncs matching COS assets into `data/community_papers/<arxiv_id>/...`.
- Keep the sync script arXiv-ID-based and conflict-safe instead of depending on `paper_id`.

## Impact
- Affected specs: `community-admin-curation`, `community-paper-library-storage`
- Affected code: `frontend/src/features/admin-curation/components/AdminCurationTasksWorkspace.tsx`, `frontend/src/pages/CommunityAdminCurationTasks.test.tsx`, `backend/scripts/`, `backend/tests/unit/`, `backend/file.md`
