## Context
- Admin curation now reuses existing translation task ids and fails terminally instead of auto-retrying.
- Failed curation can still leave behind translation task rows, failed-task quarantine directories, task configs, and sometimes a private `curating` paper created during publish.
- Structured insights are already being normalized at read time for UI stability, but that runtime contract has not been captured in OpenSpec.
- The backend currently defaults to a higher LLM concurrency than desired for quality-sensitive translation.

## Goals
- Preserve one authoritative change record for all unsaved conversation-driven runtime changes.
- Ensure failed or timed-out admin curation jobs clean up partial artifacts automatically.
- Keep the failed curation job row visible so operators can see the failure and choose whether to retry manually.
- Reduce default LLM concurrency to `3` without removing explicit lower-value overrides.

## Non-Goals
- Do not add automatic curation retry loops.
- Do not change database schema.
- Do not delete shared source directories such as `uploads/arxiv_<id>` that may be reused by other tasks.

## Decisions
- Decision: failed admin curation remains a terminal `failed` job state.
  - Why: operators explicitly want manual retry control and no hidden requeue loops.
- Decision: cleanup targets task-specific artifacts plus only papers that were created as private `curating` placeholders.
  - Why: this removes partial state without risking deletion of existing published canonical papers reused by repeat curation.
- Decision: structured insight normalization remains a deterministic read-time contract rather than a schema change.
  - Why: the frontend can rely on stable fields immediately without backfilling stored rows.
- Decision: admin curation waits up to 900 seconds before timing out.
  - Why: long-running translations need a wider but still bounded window.
- Decision: the backend default and parity-safe task ceiling for LLM concurrency both move to `3`.
  - Why: translation quality is more important than maximizing parallel request throughput.

## Risks / Trade-offs
- Cancelling and cleaning up a timed-out task may race with task shutdown if the worker is still unwinding.
  - Mitigation: issue cancellation first, then delete task artifacts and task rows, and log cleanup failures explicitly.
- Upload-source cleanup must not delete shared `arxiv_*` directories.
  - Mitigation: only delete upload source directories when the path is task-scoped under `uploads/<task_id>`.

## Migration Plan
1. Add tests for terminal failure cleanup, timeout budget, and concurrency defaults.
2. Implement cleanup helpers in `paper_service.py`.
3. Lower config defaults and update examples.
4. Validate targeted tests and the OpenSpec change.

## Open Questions
- None.
