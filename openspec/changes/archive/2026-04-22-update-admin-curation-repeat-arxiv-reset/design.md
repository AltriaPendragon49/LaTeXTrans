## Context
Admin curation currently treats repeated arXiv intake as an in-place refresh of the existing canonical paper. The service layer resolves the existing paper up front, stores that `paper_id` on the new job, and later publishes onto the same record. That behavior conflicts with the operator requirement for a clean history: repeated intake should start from zero instead of overwriting the previous paper lineage.

The repository already has durable hard-delete behavior for completed curation records and separate cleanup behavior for failed runs. Reusing those paths is safer than building a third deletion system, but the current delete entrypoint is job-centric and manual. The new flow needs an arXiv-centric orchestration step that can clear every old trace before a new job is inserted.

## Goals / Non-Goals
- Goals:
  - Make repeated admin arXiv intake deterministic: delete first, then create a fresh job and fresh `paper_id`.
  - Reuse existing hard-delete semantics for published papers and retained failed jobs where possible.
  - Prevent deleted in-flight curation workers from continuing to publish after the reset.
- Non-Goals:
  - Do not change archive-upload duplicate handling in this change.
  - Do not alter ordinary non-admin paper import or community feed identity rules outside admin repeat arXiv curation.

## Decisions
### Decision: Duplicate detection happens before the new curation job is inserted
`submit_admin_arxiv_curation_batch` will treat each normalized `arXiv ID` independently. Before inserting the new job, it will load any existing canonical paper and any curation jobs tied to that `arXiv ID`. If nothing exists, submission behaves as it does today. If prior state exists, the service runs a pre-delete reset and only inserts the replacement job if that reset succeeds.

### Decision: Pre-delete reset is arXiv-centric and composes existing delete behavior
The new reset helper will:
- cancel any active in-memory curation task for matching curation jobs
- hard-delete the published paper if one exists
- remove retained failed artifacts and translation-task rows for failed or partial jobs
- delete matching curation-job rows after their assets and task records are removed

This keeps one orchestration path in `paper_service` while continuing to rely on `_hard_delete_paper_records`, `_delete_retained_failed_artifact`, `_delete_placeholder_curation_paper_if_present`, and `task_manager.delete_task_full`.

### Decision: Reset failure blocks the new submission
If any required deletion step fails, the new admin curation item is not created. This avoids half-deleted duplicate states and preserves the operator expectation that “delete old traces first” is mandatory, not best effort.

## Risks / Trade-offs
- Cancelling in-flight curation work can surface more cancellation paths in the current worker implementation, so the reset helper must cancel and await worker tasks carefully.
- Repeated deletion across paper rows plus job rows increases the chance of partial cleanup if repository calls fail; blocking the new submission is the chosen safety trade-off.
- Existing specs that describe stable repeated-canonical identity must be narrowed so they still apply outside this admin repeat-arXiv path.

## Migration Plan
1. Update OpenSpec requirements for repeated admin arXiv curation.
2. Add repository lookup support for listing curation jobs by `arXiv ID`.
3. Add service-layer pre-delete reset orchestration and wire it into admin arXiv submission.
4. Cover the new behavior with lifecycle tests for duplicate completed and failed history.

## Open Questions
- None. The user-approved behavior is to create a brand-new `paper_id` after a full reset for repeated admin arXiv intake.
