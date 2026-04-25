## 1. Implementation
- [x] 1.1 Add admin task history UI coverage proving completed jobs expose a direct read link while incomplete jobs do not.
- [x] 1.2 Add backend script tests for parsing `complete.md`, syncing one matched COS asset set into `data/community_papers/<arxiv_id>/...`, and rejecting conflicting matches.
- [x] 1.3 Implement the completed-task read action in the admin curation history page.
- [x] 1.4 Implement the COS sync script under `backend/scripts/` with arXiv-ID-based local output, dry-run support, and conflict-safe reporting.
- [x] 1.5 Update `backend/file.md` for the new backend script responsibility.
- [x] 1.6 Run targeted frontend and backend tests for the new behavior.
