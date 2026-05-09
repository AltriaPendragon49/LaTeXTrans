# 项目文档汇总: update-community-paper-public-model-and-feed-cache

> 说明：
> 1. 已忽略汇总文件自身 `all_docs_combined.md` 及包含 `backup/test` 等关键词的文件。
> 2. 为避免 Markdown 语法冲突，源码使用了 4 个反引号进行代码块包裹。

## 1. 文档文件结构

```text
📦 update-community-paper-public-model-and-feed-cache
├── design.md
├── proposal.md
├── specs
│   ├── community-paper-discovery-ui
│   │   └── spec.md
│   ├── community-paper-intake-api
│   │   └── spec.md
│   └── deployment-infra
│       └── spec.md
└── tasks.md
```

---

## 2. 详细文档内容

### 📄 design.md

````markdown
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
````

---

### 📄 proposal.md

````markdown
# Change: Update Community-Paper Public Model And Feed Cache

## Why
The public community-paper product still carries an obsolete `official` vs `user_fallback` model even though non-official papers are no longer admitted into the public community library. At the same time, the current process-local `_PUBLIC_FEED_CACHE` cannot provide consistent multi-instance ordering or a clean foundation for `latest`, `views`, and `likes` ranking.

## What Changes
- Remove public-ranking, public-copy, and public-UI dependence on `official` / `user_fallback` semantics for community papers.
- Define the public community library as one peer set of published community papers, with `latest`, `views`, and `likes` as the only feed sort modes.
- Replace the in-process public feed cache with Redis-backed shared caching and Redis ranking indexes for public non-search feed requests.
- Keep the read-path hydration layer canonical-DB first, but shape it so a future per-paper Redis metadata cache can be inserted without changing the API contract.
- Keep MySQL as the source of truth for paper metadata, counts, and viewer engagement state.
- Keep `community_status` in storage temporarily for compatibility and migration safety, but treat it as internal-only and no longer part of public product semantics.
- Keep engagement-triggered ranking refreshes narrowly scoped to the affected paper or cache slice, using single-entry Redis updates where possible.
- Make the stale official-first cleanup part of the implementation scope for this change, including frontend copy, status affordances, API assumptions, and backend ordering logic.

## Impact
- Affected specs: `community-paper-intake-api`, `community-paper-discovery-ui`, `deployment-infra`
- Affected code: public paper API routes, community paper repository/service sorting logic, Redis integration/config, public feed cache/index management, frontend community feed hooks/components/locales, paper detail metadata presentation
````

---

### 📄 specs\community-paper-discovery-ui\spec.md

````markdown
## MODIFIED Requirements
### Requirement: Feed sort and browse shell
The community homepage SHALL provide the browse controls needed to inspect published community papers using the production sort semantics, without communicating an official-vs-fallback hierarchy.

#### Scenario: Switch feed views
- **WHEN** a user changes between `latest`, `views`, and `likes`
- **THEN** the system SHALL request the matching community paper list from the backend API
- **AND** the feed SHALL render loading, empty, and error states without falling back to local mock data.

#### Scenario: Sort values fall back to the latest rule
- **WHEN** multiple community papers share the same `view_count` or `like_count`
- **THEN** the UI SHALL treat the backend order as canonical
- **AND** that canonical order SHALL break ties using original arXiv publication time descending
- **AND** it SHALL continue falling back to `official_published_at` and then `created_at` when original publication time is unavailable.

#### Scenario: Public feed copy treats published papers as peer entries
- **WHEN** the feed homepage renders
- **THEN** the page SHALL present the community library as one published-paper surface
- **AND** it SHALL NOT communicate that official papers are prioritized over fallback papers
- **AND** it SHALL NOT explain feed ranking through `community_status` tiers.

### Requirement: Paper card content contract
Each feed result SHALL render as a dense paper discovery card that helps the viewer decide whether to inspect the paper in detail without relying on public status-tier badges.

#### Scenario: Render a paper card
- **WHEN** the feed receives a community paper item
- **THEN** the card SHALL show translation status, title, author summary, category summary, publication timing, counters, engagement affordances, and selected asset summary
- **AND** it SHALL NOT require an official-vs-fallback badge or priority styling to explain why the paper appears where it does.
````

---

### 📄 specs\community-paper-intake-api\spec.md

````markdown
## MODIFIED Requirements
### Requirement: Community feed list contract
The system SHALL expose a stable paper-centric list model for public community feed surfaces without encoding an official-vs-fallback hierarchy.

#### Scenario: Public list returns published community papers for the requested sort
- **WHEN** the frontend requests `GET /api/papers`
- **THEN** the system SHALL only return community-visible published papers
- **AND** it SHALL order `latest` by original `arxiv_published_at` descending
- **AND** it SHALL fall back to `official_published_at` descending and then `created_at` descending when original arXiv publication time is unavailable.

#### Scenario: Count-based sorts fall back to the latest rule
- **WHEN** the frontend requests `GET /api/papers?sort=views` or `GET /api/papers?sort=likes`
- **THEN** the system SHALL order papers by the requested persistent count descending
- **AND** it SHALL break ties using the same publication-first rule defined for `latest`
- **AND** public ordering SHALL NOT depend on `community_status`.

#### Scenario: Feed results include stable card metadata without public status tiers
- **WHEN** the frontend requests the papers list
- **THEN** the response SHALL include the metadata needed to render public paper cards, including translation state, counts, stable publication timestamps, and latest asset summary
- **AND** the response SHALL NOT require public consumers to interpret `community_status` in order to rank or explain feed items.

## ADDED Requirements
### Requirement: Public community feed uses shared Redis-backed indexes and cache
The public community-paper list API SHALL use shared Redis-backed indexes and cache for non-search feed requests while keeping viewer state request-scoped.

#### Scenario: Non-search public feed requests use shared indexes
- **WHEN** the frontend requests `GET /api/papers` without a search query and with sort `latest`, `views`, or `likes`
- **THEN** the backend SHALL resolve the public paper order from shared Redis-backed feed indexes or shared Redis-backed feed cache
- **AND** the response SHALL NOT depend on process-local `_PUBLIC_FEED_CACHE` state for steady-state correctness.

#### Scenario: Search requests bypass Redis ranking indexes
- **WHEN** the frontend requests `GET /api/papers` with `q`
- **THEN** the backend SHALL bypass Redis public ranking indexes
- **AND** it SHALL resolve the result set from the canonical database-backed search path using the same published-paper visibility rules.

#### Scenario: Viewer state is assembled after public list selection
- **WHEN** the backend prepares a public feed response for an authenticated or anonymous viewer
- **THEN** it SHALL assemble per-viewer like and favorite state after selecting the public paper ids
- **AND** it SHALL keep viewer-specific state out of shared Redis cache entries.

### Requirement: Public ranking indexes remain aligned with persistent engagement counts
The system SHALL keep Redis-backed public ranking state aligned with persistent like and view counts without relying on process restart.

#### Scenario: Like or view counts change for a paper
- **WHEN** a persistent `like_count` or `view_count` changes for a public community paper
- **THEN** the system SHALL refresh or invalidate the affected public ranking/index state for that paper
- **AND** later `views` or `likes` feed reads SHALL observe the updated persistent order within the configured freshness window.
````

---

### 📄 specs\deployment-infra\spec.md

````markdown
## ADDED Requirements
### Requirement: Shared Redis service backs public community-paper discovery state
Production deployment SHALL provide a shared Redis service for public community-paper feed cache and ranking state.

#### Scenario: Multiple backend instances serve one public feed state
- **WHEN** multiple backend processes or hosts serve public `GET /api/papers` requests
- **THEN** they SHALL read and write the same Redis-backed public feed cache and ranking indexes
- **AND** steady-state correctness SHALL NOT depend on process-local public feed memory.

#### Scenario: Redis outage falls back to canonical reads
- **WHEN** the shared Redis service is unavailable or unhealthy
- **THEN** the backend SHALL fall back to the canonical database-backed public read path
- **AND** it SHALL NOT reintroduce divergent process-local feed caches as the production durability mechanism.

### Requirement: Public feed index maintenance is singleton-safe
Any scheduled rebuild, repair, or backfill path for Redis-backed public community-paper indexes SHALL run under singleton-safe execution.

#### Scenario: Scheduled index maintenance runs in production
- **WHEN** the system rebuilds or repairs the Redis-backed `latest`, `views`, or `likes` indexes
- **THEN** that work SHALL run in a dedicated worker role or under a distributed singleton lock
- **AND** multiple web instances SHALL NOT race to rebuild the same public index set concurrently.
````

---

### 📄 tasks.md

````markdown
## 1. Public Model Cleanup
- [ ] 1.1 Remove public backend ordering rules that prioritize `community_status`, and align `latest`, `views`, and `likes` tie-break behavior to the publication-first rule.
- [ ] 1.2 Remove public API, frontend types, frontend sorting helpers, and UI rendering assumptions that require users to understand `official` vs `user_fallback`.
- [ ] 1.3 Remove or rewrite public copy, badges, hints, and detail metadata labels that communicate an official-first hierarchy.

## 2. Shared Feed Cache And Ranking Indexes
- [ ] 2.1 Replace process-local `_PUBLIC_FEED_CACHE` with Redis-backed shared caching for public non-search community feed requests.
- [ ] 2.2 Add Redis-backed ranking/index management for `latest`, `views`, and `likes`, while keeping search (`q`) on the canonical database path and keeping the list-hydration assembly layer extensible enough to add a future per-paper Redis metadata cache.
- [ ] 2.3 Keep viewer-specific favorite/like state out of shared cache entries and assemble it from backend persistence per request.
- [ ] 2.4 Ensure like/view count changes refresh or invalidate only the affected ranking/cache state instead of relying on process restart or whole-list in-memory invalidation; prefer single-entry Redis updates such as `ZINCRBY feed:index:likes 1 <paper_id>` or a canonical-count `ZADD` for the affected paper when applicable.

## 3. Operational Safety
- [ ] 3.1 Add or document the shared Redis deployment contract for public community feed state.
- [ ] 3.2 Ensure any scheduled Redis index rebuild/repair path runs in a dedicated worker or under a distributed singleton lock.

## 4. Verification
- [ ] 4.1 Add or update tests for public feed ordering, search bypass behavior, viewer-state hydration, and stale-state regression coverage.
- [ ] 4.2 Verify multi-instance consistency and refresh correctness for `latest`, `views`, and `likes` under authenticated and anonymous access.
````

---

