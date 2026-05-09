## Context
The codebase already supports COS-backed storage for future writes, but production is currently running in `local_disk` mode and all current public paper assets are stored locally. Switching only the environment variable would break reads because MySQL still contains local paths and historical ordinary-task outputs do not necessarily contain the COS-mode `storage_manifest.json` required by download and preview routes.

The migration must therefore be a data cutover, not just a config change.

## Goals
- Make COS the durable source of truth for production assets.
- Preserve current public community paper reads, previews, translated PDF downloads, source archive downloads, thumbnails, and task artifact downloads.
- Clean historical COS objects that are not part of the final target manifest.
- Free local disk only after COS delivery has been verified from a cold local-asset state.
- Keep rollback possible until after verification.

## Non-Goals
- Reworking translation kernel behavior.
- Migrating transient caches such as `tmp_storage`, `tiktoken-cache`, or runtime-only temporary files.
- Changing public API route paths.
- Keeping production online for writes during the cutover.

## Decisions

### Source Of Truth
The current production MySQL records and existing local files are authoritative for this migration. Existing COS objects are treated as reusable only when they match a final target key and size; otherwise they are orphan candidates.

### COS Key Convention
Community paper asset rows shall store object-storage keys the same way the existing community asset persistence path does: `paper_assets.file_path` uses keys prefixed by `latextrans-prod/data/community_papers/...`, and `paper_assets.storage_backend` becomes `object_storage`.

Ordinary task rows shall store backend-relative logical paths without the COS base prefix:
- `translation_tasks.source_path`: `data/uploads/...`
- `translation_tasks.output_path`: `data/outputs/...`

This matches `task_artifact_storage.materialize_task_directory()` and `build_task_output_download_url()`, which add the configured COS base prefix through the storage backend.

Retained failed curation artifact rows shall use:
- `artifact_storage_backend`: `object_storage`
- `failed_artifact_path`: `failed_tasks/<task_id>` or the stored failed artifact key without the COS base prefix.

### Output Manifest Backfill
Every migrated ordinary-task output directory that should be readable in COS mode must get `storage_manifest.json` before database cutover. The manifest must identify:
- translated PDF
- translated-source archive
- terminology CSV when present
- available log files

The translated-source archive may require generating a zip from `.tex`, `.bib`, `.cls`, `.sty`, and `.bst` files. Because the production disk is full, the migration script should generate and upload this archive one task at a time and delete the temporary archive immediately after upload.

### Maintenance Window
The cutover requires pausing writes. The safe production sequence is:
1. Stop or disable worker intake.
2. Stop backend write traffic or put the public backend into a maintenance window.
3. Run migration dry-run and capture manifests.
4. Run uploads and COS orphan cleanup.
5. Back up and update MySQL rows.
6. Set COS configuration in the production env.
7. Restart backend and worker only after verification gates pass.

### Disk Headroom
The current disk has too little free space for a safe cutover. Before execution, an approved headroom step must free enough space for logs, MySQL/Redis writes, manifest generation, and temporary per-task source archives. This step should be limited to clearly disposable material such as logs, Docker build cache, or already-verified temporary files.

### Cleanup
Local deletion is a final phase, not part of upload. It may delete only paths covered by the successful migration manifest:
- `backend/data/community_papers`
- `backend/data/outputs`
- `backend/data/uploads`
- `backend/data/failed_tasks`

The cleanup phase must run after routes have been verified in COS mode with local asset paths absent or emptied. Small runtime directories such as `task_configs`, `terms`, `tmp_storage`, and `tiktoken-cache` are handled separately according to operational need.

## Rollback
Before database updates, dump the affected MySQL tables:
- `paper_assets`
- `translation_tasks`
- `community_curation_jobs`
- `papers` if latest asset/task pointers are touched

Rollback before local cleanup is:
1. Restore the dumped tables.
2. Restore `STORAGE_BACKEND_MODE=local_disk` and remove COS runtime env if needed.
3. Restart backend and worker.

Rollback after local cleanup requires rehydrating local assets from COS using the migration manifest before switching back to local-disk mode.

## Verification
Verification must include:
- COS object existence and size checks for uploaded manifest entries.
- MySQL post-cutover counts showing expected `object_storage` rows.
- Backend health checks locally and publicly.
- Public paper list and paper detail reads.
- Preview HTML fetch for representative papers.
- Translated PDF preview and download for representative papers.
- Source archive download for representative papers.
- Ordinary task PDF/source/log/terminology routes for at least one completed historical task.
- Failed retained artifact reference resolution or delete-path dry-run for failed curation records.
- A post-cleanup repeat of read verification after local `community_papers`, `outputs`, `uploads`, and `failed_tasks` are absent or empty.

## Risks
- Disk pressure can interrupt uploads, DB updates, Redis writes, or SSH sessions.
- Existing COS objects may share keys with local files; same-size matches can be reused, but size mismatches must be reported and overwritten only after approval.
- Historical outputs without enough free space for translated-source archive generation may need a temp directory outside the root filesystem or a skip/partial-download policy.
- Any backend path still assuming local disk may only fail after local cleanup, so verification must include cold-local checks.
