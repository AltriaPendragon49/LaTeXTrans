## Context
The current public community-paper experience mixes two different concerns:

1. Internal admission history, where `community_status` still exists in storage and older code paths.
2. Public discovery semantics, where users now expect one clean library of published community papers ranked by time, views, or likes.

That mismatch leaks into backend SQL ordering, frontend sorting, public copy, and card/status presentation. It also blocks a clean Redis rollout because the current `_PUBLIC_FEED_CACHE` is process-local and because the old public ranking model assumes an `official-first` hierarchy that the product no longer wants.

## Goals
- Define one clean public model for community papers: a published paper is a peer published paper.
- Remove public dependency on `community_status` without forcing a risky storage-column removal in the same rollout.
- Replace process-local feed caching with shared Redis-backed caching.
- Add Redis-backed ranking indexes for public non-search `latest`, `views`, and `likes` feed requests.
- Keep viewer-specific state (`liked`, `favorited`, folder membership summaries) request-scoped and backend-persisted.
- Keep MySQL as the source of truth for metadata, counts, and engagement writes.

## Non-Goals
- Removing `community_status` from the physical schema in this change.
- Rewriting public search onto Redis or a search engine.
- Turning likes or views into eventually consistent queue-driven writes in this change.
- Redesigning admin curation semantics beyond removing obsolete public `official-first` assumptions.

## Decisions
### 1. Public product semantics stop distinguishing official vs fallback
Public discovery, detail metadata, copy, and ranking SHALL stop communicating `official` vs `user_fallback` as a user-facing concept. All published community papers are peers in the public library.

`community_status` may remain in storage temporarily for compatibility, historical interpretation, or staged cleanup, but public API contracts and UI behavior must not depend on it.

### 2. Public feed ordering becomes publication-first, not status-first
The public feed order is defined as:

- `latest`: `arxiv_published_at` descending
- Fallback when `arxiv_published_at` is missing: `official_published_at` descending, then `created_at` descending
- `views`: `view_count` descending, tie-break with the same `latest` rule
- `likes`: `like_count` descending, tie-break with the same `latest` rule

This keeps the product aligned with “only sort by time/counts” while remaining safe during backfill and older-record coexistence.

### 3. Redis only owns shared public indexes and cacheable list state
Redis is introduced for shared public feed infrastructure, not as a replacement for canonical storage.

Redis responsibilities:
- Shared cache for public non-search feed list responses or feed list building blocks
- Ranking indexes for `latest`, `views`, and `likes`
- An optional extension point for short-lived per-paper metadata hydration helpers if future traffic justifies it

Redis does not own:
- Canonical paper metadata
- Canonical like or favorite state
- Canonical per-user viewer state
- Search result generation

### 4. Search bypasses Redis ranking indexes
Requests with `q` are not a simple slice of one global ranking and should not be forced through ZSET indexes. Search continues to use the canonical database-backed query path, with the same published-paper visibility rules.

### 5. Viewer state stays request-scoped
Shared Redis cache entries must remain public and viewer-agnostic. After the backend selects the paper ids for a public list response, it SHALL assemble per-viewer fields from canonical persistence for the current request.

That includes:
- Whether the viewer liked the paper
- Whether the paper is in at least one favorite folder
- Any folder-specific selection state needed by the picker

This avoids leaking user-specific state into shared cache keys and keeps engagement correctness after refresh, relogin, cross-device use, and multi-instance reads.

### 6. Likes stay strongly consistent
Likes remain synchronous MySQL writes with one-user-one-like enforcement. After the canonical write succeeds, the system should update or invalidate only the affected ranking entry/cache slice rather than relying on process restart or whole-cache deletion.

### 7. Views keep the current deduplicated DB baseline for now
The current view-count path already includes authenticated daily dedupe and anonymous local-principal dedupe. This change does not require a queue-based or Redis-based async rewrite for views. If later load justifies it, a separate change can introduce Redis-assisted dedupe buffering without changing this public model again.

### 8. Background index maintenance must be singleton-safe
If the system uses scheduled rebuilds, repairs, or backfills for Redis public indexes, those jobs must not run independently in every web process. They need either:

- a dedicated worker role, or
- a distributed lock such as Redis `SETNX`

This avoids duplicate rebuild races and keeps public ordering deterministic across instances.

## Read Path
For `GET /api/papers` without `q`:

1. Resolve the requested public sort mode.
2. Read ordered paper ids from Redis ranking indexes and/or a shared response cache.
3. Hydrate canonical paper metadata from MySQL or existing canonical read helpers.
4. Keep the hydration step behind a read-path assembly seam so the system can later insert a per-paper Redis HASH metadata cache before falling back to MySQL, without changing caller behavior or the response contract.
5. Assemble viewer-specific engagement state for the current request.
6. Return one stable response shape that does not require public status-tier interpretation.

For `GET /api/papers` with `q`:

1. Use the canonical database-backed search path.
2. Apply the same published-paper visibility rules.
3. Assemble viewer-specific state after canonical result selection.

## Ranking Index Notes
The implementation may encode deterministic ordering either by:
- maintaining composite sortable scores in Redis, or
- using Redis for the primary metric and a canonical tie-break pass during hydration

The chosen implementation must preserve the product rule that `views` and `likes` fall back to the `latest` ordering rule when counts tie.

For engagement-driven partial updates, the implementation should prefer single-entry Redis mutations over full-index rebuilds whenever correctness can be preserved. For example:
- a like increment may use `ZINCRBY feed:index:likes 1 <paper_id>` when the Redis score model is a safe monotonic mirror of the canonical count
- otherwise, the system may re-read the canonical count for that `paper_id` and apply a single-entry `ZADD`

This keeps steady-state updates on the hot path at `O(log N)` while preserving room for a later rebuild/repair job to correct drift if needed.

## Risks And Mitigations
- Risk: Old frontend or API consumers still read `community_status`.
  - Mitigation: Treat cleanup of stale public consumers as part of this change, not as follow-up debt.
- Risk: Redis outage makes ranking unavailable.
  - Mitigation: Fall back to the canonical DB path rather than serving divergent process-local rankings.
- Risk: Viewer state leaks into shared cache.
  - Mitigation: Keep shared cache viewer-agnostic and assemble per-user state after id selection.
- Risk: Partial rollout leaves old official-first copy in the product.
  - Mitigation: Include locale copy, badges, detail metadata, and sort helpers in the same implementation checklist.

## Migration Plan
1. Remove public ranking and UI dependence on `community_status`.
2. Align backend sort helpers and API contracts with the publication-first public model.
3. Introduce Redis-backed shared public feed cache/indexes.
4. Add singleton-safe refresh/backfill mechanics for Redis indexes if scheduled refresh is required.
5. Validate that public `latest`, `views`, and `likes` ordering remains stable across refreshes, relogin, and multi-instance reads.

## Open Questions
- None for proposal approval. The remaining implementation choices are operational details within the approved architecture.
