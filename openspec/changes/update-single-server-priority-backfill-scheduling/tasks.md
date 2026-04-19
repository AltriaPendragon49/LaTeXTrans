## 1. Phase-1 Token Pool
- [ ] 1.1 Implement a system-managed token pool that models five independent endpoint-credential members across two configured `base_url` groups.
- [ ] 1.2 Add fast failover when one pool member encounters consecutive `429` or consecutive `503` responses, with only a short request-local retry window measured in seconds.
- [ ] 1.3 Preserve current single-credential behavior for request-supplied and user-stored custom API credentials.
- [ ] 1.4 Keep all-members-exhausted behavior stable: continue retrying on the current member instead of blind rotation.
- [x] 1.5 Route post-translation system-managed structured insight generation through the shared pool helper instead of a direct single-member HTTP call.

## 2. Phase-1 Verification
- [ ] 2.1 Add runtime observability needed to confirm which system-managed pool member served a request and when failover occurred.
- [x] 2.2 Add automated coverage for system-pool selection, consecutive `429` failover, consecutive `503` failover, all-members-exhausted retry behavior, structured-insight pool reuse, and custom-key bypass behavior.
- [x] 2.3 Validate the OpenSpec change with `openspec validate update-single-server-priority-backfill-scheduling --strict --no-interactive`.

## 3. Deferred Later Phases
- [x] 3.1 Introduce a dual-lane single-server scheduler with `interactive` priority and opportunistic `backfill` capacity borrowing.
- [ ] 3.2 Add cooperative yield requests plus durable resume checkpoints at approved orchestration boundaries.
- [ ] 3.3 Reduce wasteful backfill retry churn when the whole token pool is exhausted without penalizing interactive retries.
- [ ] 3.4 Move terminology-table generation and success-only compilation diagnostics behind resumable sidecar feature flags while keeping failure diagnostics synchronous.

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
