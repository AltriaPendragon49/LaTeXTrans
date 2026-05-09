# Change: Core-pool database-authoritative COS sync

## Why
`backend/arxiv_id/core_pool/complete.md` can lag behind the completed paper assets already recorded by the backend. Operators need the local sync script to use the backend's stored asset records as the source of truth, sync those recorded assets whether they are local-disk or COS-backed, and use the markdown file as a readable completion report.

## What Changes
- Change the core-pool sync script so it reads completed paper asset sets from `papers` and `paper_assets` instead of using `complete.md` as the primary input.
- Download object-storage assets by their already-recorded object keys, avoiding object-store bucket listing.
- Copy local-disk assets by their already-recorded backend-relative paths when production records still use local storage.
- Keep optional `--arxiv-id` and `--limit` filters for targeted local runs.
- Add a local operator mode that SSHes to the production server, runs the same sync inside the backend container, archives the arXiv-ID directories, downloads and extracts them locally, then removes the remote arXiv-ID output directories and temporary archive.
- Update `complete.md` from complete arXiv IDs discovered in backend asset records after a non-dry-run sync.
- Preserve conflict-safe behavior when multiple complete recorded paper asset sets map to the same arXiv ID.

## Impact
- Affected specs: `community-paper-library-storage`
- Affected code: `backend/scripts/sync_core_pool_complete_from_cos.py`, `backend/tests/unit/test_sync_core_pool_complete_from_cos.py`, `backend/file.md`
