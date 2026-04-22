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

#### Scenario: Hydration remains canonical while allowing a future metadata cache layer
- **WHEN** the backend assembles the public feed response after selecting paper ids from Redis-backed indexes
- **THEN** it SHALL hydrate canonical paper metadata from MySQL or canonical read helpers for the current response contract
- **AND** it SHALL keep that hydration behind a stable assembly seam so a future per-paper Redis HASH metadata cache can be added without changing the external API behavior.

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

#### Scenario: Ranking refreshes stay narrowly scoped on engagement writes
- **WHEN** a like write succeeds for a public community paper and no full rebuild is required
- **THEN** the system SHALL prefer a single-entry Redis ranking mutation for the affected `paper_id`, such as `ZINCRBY` or a single-entry `ZADD` with the canonical latest score
- **AND** it SHALL avoid whole-index or process-wide cache invalidation on the steady-state hot path unless correctness requires it.

#### Scenario: Periodic rebuild repairs Redis drift without changing the API contract
- **WHEN** the background worker performs a scheduled rebuild of the public `latest`, `views`, or `likes` indexes
- **THEN** later non-search `GET /api/papers` requests SHALL continue returning the same response contract and hydration behavior
- **AND** the rebuilt indexes SHALL reflect canonical MySQL counts and publication ordering after the repair completes.
