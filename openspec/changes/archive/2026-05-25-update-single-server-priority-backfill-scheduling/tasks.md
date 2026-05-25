## 1. Phase-1 Token Pool
- [x] 1.1 Implement a system-managed token pool that models five independent endpoint-credential members across two configured `base_url` groups.
- [x] 1.2 Add fast failover when one pool member encounters consecutive `429` or consecutive `503` responses, with only a short request-local retry window measured in seconds.
- [x] 1.3 Preserve current single-credential behavior for request-supplied and user-stored custom API credentials.
- [x] 1.4 Keep all-members-exhausted behavior stable: continue retrying on the current member instead of blind rotation.
- [x] 1.5 Route post-translation system-managed structured insight generation through the shared pool helper instead of a direct single-member HTTP call.

## 2. Phase-1 Verification
- [x] 2.1 Add runtime observability needed to confirm which system-managed pool member served a request and when failover occurred.
- [x] 2.2 Add automated coverage for system-pool selection, consecutive `429` failover, consecutive `503` failover, all-members-exhausted retry behavior, structured-insight pool reuse, and custom-key bypass behavior.
- [x] 2.3 Validate the OpenSpec change with `openspec validate update-single-server-priority-backfill-scheduling --strict --no-interactive`.

## 3. Deferred Later Phases
- [x] 3.1 Introduce a dual-lane single-server scheduler with `interactive` priority and opportunistic `backfill` capacity borrowing.
- [x] 3.4 Removed from this change scope per 2026-05-09 direction; terminology-table generation and success-only compilation diagnostics stay on the existing inline path.

## 4. Single-Server Web/Worker Isolation
- [x] 4.1 Add `all|web|worker` runtime-role config and keep legacy single-process behavior available.
- [x] 4.2 Make admin curation/delete execution worker-owned, with polling instead of web-process in-memory scheduling.
- [x] 4.3 Add frontend-pressure-aware backfill admission plus worker process de-prioritization.

## 5. Public Feed Responsiveness
- [x] 5.1 Change community paper list reads to paginated API responses with `has_more` / `next_offset`.
- [x] 5.2 Cache the first public latest-feed page and invalidate it on public paper mutations.
- [x] 5.3 Update the frontend community feed hook/page to use incremental loading instead of whole-list fetches.

## 6. Thumbnail Warm Cache
- [x] 6.1 Extract shared PDF thumbnail cache generation into a reusable backend service.
- [x] 6.2 Prewarm public source/translated thumbnails when a paper becomes publicly readable.

## 7. Task-State Consistency And Exception Containment
- [x] 7.1 Add attempt-scoped task update guards so same-attempt terminal states cannot regress back to `queued` / `processing` through stale progress callbacks.
- [x] 7.2 Clear stale `completed_at` markers only when a fresh control-plane retry or new execution attempt legitimately reactivates a task.
- [x] 7.3 Reconcile impossible persistent task rows (`completed_at` set while status is non-terminal) into explicit terminal failures during recovery/wait paths.
- [x] 7.4 Make admin curation terminal waits fall back to durable `translation_tasks` state instead of depending only on in-memory task snapshots.
- [x] 7.5 Ensure unexpected queue-level exceptions that escape the translation coroutine still force a terminal failure write and paper-status sync.
- [x] 7.6 Add automated coverage for terminal regression rejection, retry reactivation clearing, persistent-state reconciliation, durable wait fallback, and unexpected worker exception handling.
