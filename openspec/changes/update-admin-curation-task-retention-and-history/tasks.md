## 1. Data model and retention
- [x] 1.1 Add a MySQL migration for admin curation retention fields such as `terminal_task_status`, `failed_artifact_path`, `artifact_storage_backend`, and `published_paper_id`.
- [x] 1.2 Update admin curation failure handling so failed runs keep their `translation_tasks` rows and store durable failed artifact references instead of deleting them.
- [x] 1.3 Preserve failed admin curation artifacts under the configured `failed_tasks/{task_id}` namespace while keeping shared upload caches out of the move/delete scope.

## 2. Admin curation APIs and orchestration
- [x] 2.1 Keep large newline-delimited arXiv submissions as one persisted curation job per parsed line before scheduling execution.
- [x] 2.2 Add admin curation job history listing/filtering API support for queued, processing, completed, and failed jobs.
- [x] 2.3 Add admin curation job hard-delete API behavior for failed and completed curation records, reusing the existing published-paper hard-delete flow for completed jobs.

## 3. Frontend admin surfaces
- [x] 3.1 Update the admin curation page to parse one arXiv ID per line, de-duplicate parsed IDs, and show the parsed count before submission.
- [x] 3.2 Add an admin-only curation task records page with status filters, simple search, and core job metadata.
- [x] 3.3 Add destructive delete actions with clear "permanent delete" copy for failed and completed curation records.

## 4. Verification
- [x] 4.1 Add backend tests for failed retention, history listing, and hard-delete behavior.
- [x] 4.2 Add frontend tests for newline parsing, admin routing/navigation, and curation task history management.
- [x] 4.3 Run `openspec validate update-admin-curation-task-retention-and-history --strict --no-interactive`.
