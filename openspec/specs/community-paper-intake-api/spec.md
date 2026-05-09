# community-paper-intake-api Specification

## Purpose
TBD - created by archiving change add-community-day-02-paper-intake-and-feed-api. Update Purpose after archive.
## Requirements
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

### Requirement: Community paper detail contract
The community paper detail contract SHALL distinguish readable English-source state from translated-reader state and SHALL not equate compile failure with total translated unreadability.

#### Scenario: Detail contract exposes best available readable mode
- **WHEN** a public community paper has English HTML, English PDF, translated HTML, or translated PDF artifacts in any healthy or degraded combination
- **THEN** the detail contract SHALL expose the best available readable mode and its fallback options
- **AND** the frontend SHALL not need to infer that state from raw paper status alone.

#### Scenario: Failed task still yields readable artifacts
- **WHEN** a terminal translation task still produced translated preview or translated PDF artifacts
- **THEN** the detail contract SHALL surface those artifacts as readable output
- **AND** the paper SHALL not be represented as fully untranslated just because compile validation failed.

### Requirement: Community paper view tracking
The system SHALL support a dedicated paper view write path without introducing a new analytics table.

#### Scenario: Track paper views without breaking the main read path
- **WHEN** a paper detail page is opened
- **THEN** the system SHALL support `POST /api/papers/{paper_id}/view`
- **AND** it SHALL update the paper view count while keeping feed and detail reads available.

### Requirement: Background content pool admission reuses the same canonical paper rules
The community paper intake layer SHALL allow the background content pool to admit or reuse papers using the same canonical paper model that interactive imports already use.

#### Scenario: Background pool admits a new paper
- **WHEN** the content pool decides to warm a paper that does not yet exist in the community database
- **THEN** the intake layer SHALL create one canonical paper record for that `arxiv_id`
- **AND** later interactive imports SHALL reuse that same paper instead of creating a second record.

#### Scenario: Background pool encounters an existing paper
- **WHEN** the content pool decides to warm a paper that already exists in the community database
- **THEN** the intake layer SHALL reuse the existing canonical paper
- **AND** the content pool SHALL enrich that paper’s assets and readiness state rather than creating a duplicate admission path.

### Requirement: Community admission is admin-curated and complete-only
The system SHALL admit newly visible community papers only through the admin curation flow, and those papers SHALL become publicly visible only after the full curation pipeline succeeds.

#### Scenario: Admin curation run succeeds fully
- **WHEN** an authenticated admin submits a paper through the admin curation flow
- **AND** intake, metadata preparation, translation, and structured insight generation all succeed
- **THEN** the system SHALL create or reuse one canonical community paper record
- **AND** it SHALL publish that paper as visible community content only after that full success state is reached.

#### Scenario: Repeated admin arXiv curation resets old traces before a new run
- **WHEN** an authenticated admin submits an `arXiv ID` that already has a canonical community paper or prior admin curation history
- **THEN** the system SHALL hard-delete the prior paper record, related assets, structured insights, similar recommendations, curation jobs, translation tasks, retained failed artifacts, and run-scoped local artifacts for that `arXiv ID`
- **AND** it SHALL create the replacement admin curation item only after that reset succeeds
- **AND** the replacement run SHALL start with a fresh `paper_id`.

#### Scenario: Ordinary tool translation succeeds
- **WHEN** a non-admin user completes a translation through the direct tools workflow
- **THEN** the system SHALL keep that result outside the visible community feed by default
- **AND** it SHALL not create a new public community paper solely because the tool translation succeeded.

#### Scenario: Curation pipeline is incomplete or fails
- **WHEN** a curation run has not yet completed all required stages or ends in failure
- **THEN** the corresponding paper SHALL remain absent from the public community feed
- **AND** users SHALL not see a half-finished public community paper card for that run.

### Requirement: Canonical community paper identity is stable across repeated curation
The system SHALL keep a canonical community paper identity stable across later updates, except for the explicit duplicate admin `arXiv ID` reset path that deletes the old paper before recreating it.

#### Scenario: Archive intake later resolves to an existing canonical paper
- **WHEN** archive-based curation is determined to match an already-known canonical community paper
- **THEN** the system SHALL reuse the existing `paper_id`
- **AND** the latest successful curation output SHALL replace the prior published community-facing content for that same paper.

#### Scenario: Canonical paper id stays stable for non-reset updates
- **WHEN** a canonical community paper already exists and the new intake does not enter the duplicate admin arXiv reset path
- **THEN** its `paper_id` SHALL remain unchanged across later curation updates
- **AND** repeated curation SHALL update the paper in place instead of generating a new public identity.

### Requirement: Archive-based admin intake extracts feed metadata
The admin curation intake path SHALL extract enough metadata from TeX-containing archives to support the same paper-card presentation shape expected from arXiv-based curation.

#### Scenario: Admin uploads a TeX-containing archive
- **WHEN** an authenticated admin submits an archive intake that contains TeX sources
- **THEN** the intake pipeline SHALL extract or derive a title and abstract before publication
- **AND** the resulting community feed card SHALL be able to render those fields like an arXiv-curated paper.

### Requirement: Batch curation submission supports bounded concurrency
The admin curation intake path SHALL accept both arbitrarily large `arXiv ID` batches and multiple archive uploads and SHALL process them through a bounded-concurrency queue.

#### Scenario: Batch includes many arXiv ids
- **WHEN** an admin submits a large batch of `arXiv ID`s in one curation request
- **THEN** the system SHALL create one tracked curation item per submitted ID with per-item states
- **AND** it SHALL persist those items before execution starts
- **AND** it SHALL process items with configured bounded parallelism instead of unlimited fan-out.

#### Scenario: Batch includes multiple archive uploads
- **WHEN** an admin uploads multiple archive files in one curation batch
- **THEN** the system SHALL track each archive as its own curation item
- **AND** the system SHALL schedule those items through the same bounded-concurrency queue used for arXiv batches.

#### Scenario: One batch item fails while others continue
- **WHEN** one paper in a curation batch fails
- **THEN** the other batch items SHALL continue independently
- **AND** publication readiness SHALL still be decided per paper instead of treating the whole batch as failed.

### Requirement: Failed admin curation jobs are terminal and operator-retained
The admin curation intake pipeline SHALL treat failed or timed-out curation items as terminal failures, SHALL not automatically requeue them, and SHALL retain failed task evidence for later operator analysis.

#### Scenario: Translation task fails during admin curation
- **WHEN** an admin curation item reaches a failed terminal translation state
- **THEN** the curation job SHALL be marked `failed`
- **AND** the system SHALL not automatically restart or requeue that curation job
- **AND** the system SHALL preserve the related `translation_tasks` row
- **AND** the system SHALL retain failed task artifacts under the configured `failed_tasks/{task_id}` namespace
- **AND** the failed curation job row SHALL remain available so an admin can inspect the error and decide whether to delete it manually.

#### Scenario: Admin curation times out while waiting for translation
- **WHEN** the admin curation worker waits 15 minutes for a translation task and the task is still not terminal
- **THEN** the system SHALL mark the curation job `failed`
- **AND** it SHALL cancel that curation task before marking the retained failure when cancellation is still applicable
- **AND** it SHALL require a new operator action for any retry.

#### Scenario: Failed curation created only a private placeholder paper
- **WHEN** a failed curation run created a private `curating` paper and related rows during publication preparation
- **THEN** the system SHALL delete that placeholder paper and its paper-scoped local rows
- **AND** it SHALL not delete an already-published canonical paper that existed before the failed curation attempt.

### Requirement: Admin curation job history is independent from public paper visibility
The system SHALL keep admin curation job history queryable even when the corresponding paper is absent from public feed surfaces.

#### Scenario: Failed curation job has no public paper
- **WHEN** an admin curation item fails before public publication
- **THEN** the curation job SHALL remain queryable in admin history
- **AND** the failed item SHALL remain absent from the public community feed.

#### Scenario: Completed curation job publishes successfully
- **WHEN** an admin curation item completes publication successfully
- **THEN** the curation job SHALL remain queryable in admin history
- **AND** the public community feed SHALL still be driven by the published paper record rather than the history row itself.

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

