## Context
The current admin curation flow already persists `community_curation_jobs`, but it still treats failed runs as disposable execution attempts. On failure it deletes the retained `translation_tasks` row and removes failed artifacts, leaving only a shallow curation-job error string. That behavior conflicts with the operator need to inspect failed inputs and partial outputs later.

The current admin UI also centers on one submission page plus batch polling for the latest submitted batch. That is insufficient once admins paste hundreds or thousands of arXiv IDs and need to manage the full lifecycle of queued, completed, and failed curation work.

## Goals
- Preserve failed admin curation runs for later diagnosis without exposing them on the public paper homepage.
- Support large newline-delimited admin arXiv intake while keeping existing bounded-concurrency execution.
- Make `community_curation_jobs` the durable history source for admin curation management.
- Provide a dedicated admin task records page with simple filtering and hard-delete management.
- Keep completed-record deletion aligned with the existing admin paper hard-delete flow.

## Non-Goals
- Do not redesign ordinary user translation history.
- Do not introduce unbounded execution concurrency.
- Do not create a second independent admin audit system outside the existing curation-job model.
- Do not surface failed curation items on public community feed surfaces.

## Decisions

### Decision: Treat `community_curation_jobs` as the admin curation system of record
Each admin intake item remains one durable curation-job row. The admin task history page reads from `community_curation_jobs` rather than trying to reconstruct history from `papers` plus `translation_tasks`.

Implications:
- The list view can show queued, processing, completed, and failed jobs even when no public paper exists.
- Public paper visibility stays driven by `papers`, not by curation-job presence.
- Repeated curation for the same canonical paper can create multiple job-history entries while still reusing one canonical paper identity on successful publication.

### Decision: Failed admin curation runs are retained, not self-cleaned
When an admin curation run reaches a terminal failure (`failed`, `failed_compilation`, or `structure_invalid`), the system keeps:
- the `community_curation_jobs` row
- the `translation_tasks` row
- the failed task artifacts under the configured `failed_tasks/` namespace

The curation job records both the user-facing curation status (`failed`) and the underlying translation terminal status (`terminal_task_status`).

The system still cleans up a private `curating` placeholder paper that was created only for the failed run, but it must never delete an already-published canonical paper that predated the failed attempt.

### Decision: Failed artifact retention uses the configured failed-task namespace
Failed artifacts continue to use the existing failed-task quarantine concept, but the retained location becomes storage-backend aware:
- local-disk mode: `data/failed_tasks/{task_id}`
- object-storage admin-retention mode: `failed_tasks/{task_id}`

Only task-output artifacts move into this namespace. Shared upload caches and `terms/{task_id}` remain outside the move/delete scope.

`community_curation_jobs` records the durable failed artifact reference rather than a transient signed URL.

### Decision: Large admin arXiv intake is "unbounded submission, bounded execution"
The admin page accepts newline-delimited arXiv IDs with no product-level item cap. The frontend parses one non-empty line into one ID and removes duplicates before submission.

The backend persists one curation-job row per parsed ID before execution starts. Execution remains bounded by the existing admin curation concurrency setting, so large batches queue safely instead of fanning out without limit.

### Decision: Admin task records management is separate from public paper browsing
Add an admin-only curation task records page (for example `/admin/curation/tasks`) with:
- filters for `queued`, `processing`, `completed`, `failed`
- simple search by `arxiv_id` or `batch_id`
- task metadata including `job_id`, `task_id`, `paper_id`, timestamps, and error

The public homepage continues to show only published public papers, so failed jobs remain invisible outside the admin surface.

### Decision: Delete semantics depend on curation outcome but are always hard delete
From the admin task records page:
- deleting a failed curation record hard-deletes the curation-job row, retained translation-task row, failed artifacts under `failed_tasks/`, and any run-specific residual rows/assets
- deleting a completed curation record reuses the existing admin hard-delete paper flow, then also removes the linked curation-job history row

No soft-delete or archive state is introduced for this history page.

## Data Model
Add retention-oriented fields to `community_curation_jobs`:
- `terminal_task_status`: underlying translation terminal status
- `failed_artifact_path`: durable failed artifact namespace reference
- `artifact_storage_backend`: `local_disk` or `object_storage`
- `published_paper_id`: explicit reference to the successfully published canonical paper when available

Existing `task_id` remains the bridge to `translation_tasks`.

## API Shape
Keep admin submission write APIs, but extend the admin curation surface with:
- job-history list API with filter/search support
- job delete API for hard deletion by curation-job id

The admin page still submits arXiv jobs as `arxiv_ids: string[]`; newline parsing remains a frontend concern.

## Risks / Trade-offs
- Retaining failed translation-task rows increases stored metadata, but the operator benefit outweighs the extra storage.
- Hard deletion from the history page becomes more powerful and must remain admin-only with clear destructive UI copy.
- Reusing existing paper hard-delete behavior for completed records reduces duplicated logic, but the implementation must also remove the linked curation-job history row to satisfy the "leave no trace" requirement.

## Migration Plan
1. Add MySQL migration for the new curation-job retention fields and supporting indexes if needed.
2. Update admin failure handling so it records retained failed-artifact references instead of deleting translation-task rows.
3. Add history list/delete APIs.
4. Add the admin task records page and navigation entry.
5. Verify that failed jobs remain absent from public paper list endpoints.

## Open Questions
- None for this proposal. The current product decisions for failed/completed delete semantics and admin-only scope are already resolved.
