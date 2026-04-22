# Change: Retain failed admin curation tasks and add admin task history

## Why
The current admin curation flow deletes failed task rows and failed artifacts, which blocks later diagnosis and repair. The admin curation UI also does not provide a durable history surface for managing queued, completed, and failed intake work at scale.

## What Changes
- Retain failed admin curation task records instead of deleting their translation-task rows during failure handling.
- Preserve failed admin curation artifacts under the configured `failed_tasks/` storage namespace, including object-storage-backed retention for COS deployments.
- Expand admin arXiv intake to support large newline-delimited ID batches while still executing through bounded concurrency.
- Add an admin-only curation task records page for queued, processing, completed, and failed curation jobs.
- Add admin APIs for curation-job history listing/filtering and hard deletion of failed or completed curation records.
- Reuse existing hard-delete behavior for published papers when deleting completed admin curation records.

## Impact
- Affected specs: `community-admin-curation`, `community-paper-intake-api`, `file-management`, `web-api`
- Affected code: admin curation orchestration in `backend/app/services/paper_service.py`, task retention/quarantine flow in `backend/app/services/task_manager.py`, MySQL curation schema/migrations, admin curation routes in `backend/app/api/routes/papers.py`, admin UI routing/sidebar/pages under `frontend/src/`
