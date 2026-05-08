## Context
After the production asset migration, COS is the durable source of truth for community assets and ordinary task artifacts. However, the original English source PDF is not currently a durable community asset. The source PDF endpoints can fall back to live arXiv PDF retrieval, which is slower and less reliable than COS delivery.

Local disk should still be available for active task runtime materialization, source PDF compilation/cache, delivery temp files, logs, and operator reports. The risk to eliminate is long-lived durable-asset residue under directories that should now be temporary in COS mode.

## Goals
- Store original arXiv PDFs as canonical community assets in COS for curated arXiv papers.
- Prefer COS-backed `source_pdf` reads before live arXiv fallback.
- Keep LaTeX source archive behavior separate from original PDF behavior.
- Add a guarded cleanup/audit path for stale local residue in COS mode.
- Provide production verification using `2407.12818` and `2407.01489`.

## Non-Goals
- Removing arXiv fallback entirely.
- Changing public API route paths.
- Reworking translation kernel behavior.
- Cleaning database backups, migration reports, logs, Docker images, or arbitrary files outside approved runtime-cache roots.

## Decisions

### Asset Type
Use `paper_assets.asset_type='source_pdf'` for the original arXiv PDF. This keeps it distinct from:
- `source_archive`: LaTeX source archive/source tree used by translation and source recovery.
- `translated_pdf`: Chinese translated delivery PDF.
- `preview_html`: translated reader preview.

### COS Key Convention
For community papers, `source_pdf` uses the existing community canonical namespace and stores the full COS key in `paper_assets.file_path`, consistent with migrated community assets:

`latextrans-prod/data/community_papers/<paper_id>/source_pdf/<arxiv_id>.pdf`

The row records:
- `storage_backend='object_storage'`
- `asset_type='source_pdf'`
- `mime_type='application/pdf'`
- `file_name='<arxiv_id>.pdf'`
- `is_latest=true`

### Publish-Time Persistence
When an admin curation run publishes an arXiv paper, the publish flow should attempt original PDF persistence after the paper ID is known. It should:
1. Check whether latest `source_pdf` already exists.
2. Download the arXiv PDF to a temp path.
3. Validate that it looks like a PDF and has non-zero size.
4. Upload to COS through the existing storage backend.
5. Upsert the `source_pdf` paper asset.
6. Delete the temp file.

If source PDF persistence fails while translated publish succeeds, the curation job should not lose the translated paper. It should record a warning and allow a later backfill to recover `source_pdf`.

### Read Resolution
`resolve_paper_source_pdf_preview()` should resolve in this order:
1. Latest `source_pdf` asset from COS or local-disk dev mode.
2. Existing source archive/local source directory PDF discovery.
3. arXiv fallback by `arxiv_id`.
4. Legacy task fallback.

For object storage `source_pdf`, source preview/download should use a signed COS URL or controlled proxy path consistent with translated PDF delivery. Range requests should remain supported for PDF viewer behavior where the route streams/proxies content.

### Backfill
Add a dry-run-first script for existing published arXiv community papers without `source_pdf`. The script should list candidates, skip papers with existing `source_pdf`, download/upload one PDF at a time, and emit a JSON report. It should require `--execute` before writing DB/COS.

### Cleanup Task
Add a dry-run-first local residue cleanup script for COS mode. It should:
- Refuse to run destructive cleanup unless `STORAGE_BACKEND_MODE=cos`.
- Restrict cleanup to configured safe roots such as `data/uploads`, `data/outputs`, `data/community_papers`, `data/failed_tasks`, and `data/tmp_storage`.
- Delete only entries older than a configurable age threshold.
- Report candidates, deleted paths, skipped paths, and errors in JSON.
- Avoid `task_configs`, `terms`, backups, migration reports, logs, and any path outside `backend/data`.

Production scheduling may be a systemd timer or cron entry after a dry-run report is reviewed. The implementation should make the script safe and idempotent first; scheduling can be enabled only after verification.

## Verification
- Unit tests for source PDF asset path/key generation, read priority, and cleanup path guards.
- Script dry-run tests for source PDF backfill and residue cleanup.
- Local targeted pytest for new tests.
- OpenSpec strict validation.
- Production deploy/restart health checks.
- Production admin curation test for `2407.12818` and `2407.01489` with admin credentials supplied operationally but not printed.
- Production DB/COS audit:
  - `source_pdf` rows exist for the two papers and are `object_storage`.
  - translated assets, preview assets, source archives, ordinary task artifacts remain COS-backed.
  - source PDF routes return 200 and resolve through COS, not live arXiv fallback.
  - local durable asset roots remain empty or within accepted small runtime residue limits after cleanup.

## Risks
- arXiv PDF download can still be slow during publish/backfill; this moves the delay out of reader hot paths but does not eliminate download risk.
- A `source_pdf` persistence failure should not corrupt or block a successful translated publish unless later policy chooses to make it mandatory.
- Cleanup misconfiguration could delete useful runtime material; strict root guards, age thresholds, dry-run reports, and COS-mode checks are required.
