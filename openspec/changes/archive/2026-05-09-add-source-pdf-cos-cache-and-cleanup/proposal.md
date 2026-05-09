# Change: Add source PDF COS cache and local residue cleanup

## Why
Production durable assets now live in COS, but public source-PDF preview/download still falls back to live arXiv PDF retrieval when no local source PDF exists. That makes original PDF reads slower and dependent on arXiv availability. Production also needs a routine cleanup guard so COS-mode local runtime residue cannot quietly grow until the server disk fills again.

## What Changes
- Add a canonical community `source_pdf` asset for original arXiv PDFs.
- During successful admin curation publish, download the original arXiv PDF once, persist it to COS, and record it in `paper_assets`.
- Make public source PDF preview/download prefer the `source_pdf` COS asset before falling back to existing source archive/local/arXiv behavior.
- Add a dry-run-first operator backfill path for existing published arXiv community papers missing `source_pdf`.
- Add a production-safe local residue cleanup/audit task that removes stale COS-mode runtime caches only after configured age and path guards.
- Validate with production admin curation for arXiv IDs `2407.12818` and `2407.01489` using the admin account `1593120349@qq.com`, confirming source PDF, translated assets, DB storage pointers, COS objects, public reads, and local disk residue.

## Impact
- Affected specs: `community-paper-library-storage`, `community-public-read-experience`, `file-management`, `deployment-infra`
- Affected code: likely `backend/app/services/paper_service.py`, `backend/app/api/routes/papers.py`, storage helpers, curation publish path, new/updated scripts under `backend/scripts/`, tests, and `backend/file.md`.
- Production impact: requires deploy/restart plus controlled admin curation test runs. The cleanup task must start in dry-run/report mode before destructive cleanup is enabled.

## Acceptance Criteria
- Newly curated arXiv community papers have `paper_assets.asset_type='source_pdf'`, `storage_backend='object_storage'`, and a COS key under `latextrans-prod/data/community_papers/...`.
- `/api/papers/{paper_id}/source-pdf` and `/api/papers/{paper_id}/source-download` return from COS for papers with `source_pdf`, without live arXiv download on the hot path.
- Existing source archive and translated asset behavior remains unchanged.
- Cleanup dry-run reports stale local residue and guarded execute removes only approved COS-mode runtime cache paths.
- Production validation for `2407.12818` and `2407.01489` succeeds and shows all durable assets in COS, local durable asset directories clean, and source PDF routes working.
