## MODIFIED Requirements

### Requirement: Backend automatically cleans up stale tasks on startup
The backend SHALL automatically reconcile community-paper translation state during startup so interrupted work is deterministically failed/cleaned and eligible non-success artifacts are removed across the database and local filesystem before traffic is served.

#### Scenario: Startup cleanup runs before serving traffic
- **WHEN** the backend process starts with stale queued, processing, or failed community-paper tasks still present
- **THEN** it SHALL mark active interrupted `translation_tasks` as `failed` and clean local task artifacts
- **AND** it SHALL purge non-success community-paper records only for purge-eligible visibility/status scopes while keeping successful and public papers untouched
- **AND** subsequent API traffic SHALL observe the cleaned state without requiring a manual restart or cleanup call.

#### Scenario: Startup purge is explicitly disabled
- **WHEN** `ENABLE_STALE_PAPER_PURGE` is set to a disabled value
- **THEN** startup reconciliation SHALL skip non-success paper purge operations
- **AND** it SHALL continue to report cleanup execution status without deleting paper records.

### Requirement: Non-success community papers are deleted comprehensively
The backend SHALL remove purge-eligible non-success community papers from all related paper-facing Supabase tables and local task artifacts, not only from the primary `papers` row.

#### Scenario: Purge-eligible non-success paper has related moderation and reaction data
- **WHEN** a purge-eligible non-success community paper is purged during startup or admin cleanup
- **THEN** the backend SHALL delete related `comments`, `reports`, `moderation_actions`, `paper_assets`, `paper_likes`, `paper_favorites`, related `translation_tasks`, and the `papers` row
- **AND** it SHALL also delete the corresponding local task artifact directories and `community_papers/<paper_id>` folder.

#### Scenario: Public paper remains available after restart cleanup
- **WHEN** startup or admin cleanup runs
- **THEN** non-success papers that are currently public SHALL NOT be purged by default
- **AND** their reader assets and metadata SHALL remain queryable via normal paper APIs.

## ADDED Requirements

### Requirement: Community paper APIs retry transient database transport failures
Community paper service-layer API paths SHALL retry transient Supabase transport failures before returning an error.

#### Scenario: Transient timeout recovers within retry budget
- **WHEN** a Supabase operation fails with transient network/timeout transport exceptions
- **THEN** the API layer SHALL retry with bounded backoff
- **AND** it SHALL return success if a later retry succeeds within the configured retry budget.

#### Scenario: Transient timeout persists beyond retry budget
- **WHEN** retries are exhausted for transient network/timeout transport exceptions
- **THEN** the API layer SHALL surface the final failure
- **AND** it SHALL not loop indefinitely.
