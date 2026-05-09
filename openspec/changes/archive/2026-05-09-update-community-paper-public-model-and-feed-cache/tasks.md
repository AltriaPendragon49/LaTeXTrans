## 1. Public Model Cleanup
- [x] 1.1 Remove public backend ordering rules that prioritize `community_status`, and align `latest`, `views`, and `likes` tie-break behavior to the publication-first rule.
- [x] 1.2 Remove public API, frontend types, frontend sorting helpers, and UI rendering assumptions that require users to understand `official` vs `user_fallback`.
- [x] 1.3 Remove or rewrite public copy, badges, hints, and detail metadata labels that communicate an official-first hierarchy.

## 2. Shared Feed Cache And Ranking Indexes
- [x] 2.1 Replace process-local `_PUBLIC_FEED_CACHE` with Redis-backed shared caching for public non-search community feed requests.
- [x] 2.2 Add Redis-backed ranking/index management for `latest`, `views`, and `likes`, while keeping search (`q`) on the canonical database path and keeping the list-hydration assembly layer extensible enough to add a future per-paper Redis metadata cache.
- [x] 2.3 Keep viewer-specific favorite/like state out of shared cache entries and assemble it from backend persistence per request.
- [x] 2.4 Ensure like/view count changes refresh or invalidate only the affected ranking/cache state instead of relying on process restart or whole-list in-memory invalidation; prefer single-entry Redis updates such as `ZINCRBY feed:index:likes 1 <paper_id>` or a canonical-count `ZADD` for the affected paper when applicable.

## 3. Operational Safety
- [x] 3.1 Add or document the shared Redis deployment contract for public community feed state.
- [x] 3.2 Ensure any scheduled Redis index rebuild/repair path runs in a dedicated worker or under a distributed singleton lock.
- [x] 3.3 Add a periodic worker-side Redis index rebuild/repair loop that rebuilds into temporary keys and atomically swaps them into the live feed indexes.

## 4. Verification
- [x] 4.1 Add or update tests for public feed ordering, search bypass behavior, viewer-state hydration, and stale-state regression coverage.
- [x] 4.2 Verify multi-instance consistency and refresh correctness for `latest`, `views`, and `likes` under authenticated and anonymous access.
