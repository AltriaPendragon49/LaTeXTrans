# Change: Migrate production assets to COS

## Why
Production is currently operating from local disk even though the intended deployment model is COS-backed storage. The server root filesystem is full, current community assets and task artifacts are recorded as local-disk paths, and the COS bucket contains only a small set of historical objects that are not authoritative.

## What Changes
- Add an operator migration path that treats the current production MySQL records plus existing local files as the source of truth.
- Produce a dry-run manifest for COS orphan objects, local files to upload, database rows to update, and same-key object conflicts before any destructive action.
- Delete only COS objects that are absent from the final migration manifest and not referenced by current production records.
- Upload durable local assets to COS under stable keys:
  - community paper assets under `latextrans-prod/data/community_papers/...`
  - ordinary task sources under `latextrans-prod/data/uploads/...`
  - ordinary task outputs under `latextrans-prod/data/outputs/...`
  - retained failed artifacts under `latextrans-prod/failed_tasks/...`
- Backfill ordinary-task output manifests so COS-mode preview and download endpoints can resolve historical PDFs, source archives, terminology files, and logs.
- Update MySQL storage pointers after successful upload verification:
  - `paper_assets.storage_backend/file_path`
  - `translation_tasks.source_path/output_path`
  - retained failed curation artifact fields where applicable
- Switch production backend and worker configuration to COS mode and verify public asset delivery before deleting local asset directories.

## Impact
- Affected specs: `deployment-infra`, `community-paper-library-storage`, `file-management`
- Affected code: likely a new operator script under `backend/scripts/`, related tests, backend file index entry, and production environment configuration.
- Production impact: requires a maintenance window because writes must be paused while local assets, MySQL pointers, and runtime configuration are cut over together.

## Current Audit Baseline
- Production disk: `/dev/vda2` is 50G with about 308M free and reports 100% usage.
- Runtime mode: `STORAGE_BACKEND_MODE=local_disk`; COS env is not present in production `.env`.
- `paper_assets`: 1055 rows, all `local_disk`, all referenced local files exist.
- `translation_tasks`: 367 rows; all source paths are local upload paths, all output paths are local output paths; 354 output directories exist, 13 terminal-failure outputs have moved/missing output roots.
- Local asset directories: `community_papers` about 11G, `outputs` about 9.4G, `uploads` about 6.5G, `failed_tasks` about 167M.
- COS under `latextrans-prod/`: 800 objects, about 0.57 GiB. No current `paper_assets` row exactly overlaps COS. Existing COS `community_papers` and `outputs` objects are orphaned relative to the current DB; 161 COS `uploads` objects match local files by path and size.
