# community-schema-foundation Specification

## Purpose
TBD - created by archiving change add-community-day-01-schema-rls-foundation. Update Purpose after archive.
## Requirements
### Requirement: Community schema entities are frozen
The system SHALL establish a single paper-first schema contract before any daily implementation change starts.

#### Scenario: Define the Day 1 entity inventory
- **WHEN** Day 1 is applied
- **THEN** the change SHALL define the MVP entity set for `papers`, `paper_assets`, `paper_likes`, `paper_favorites`, `comments`, `reports`, `moderation_actions`, `notifications`, `user_roles`, and `user_bans`
- **AND** later daily changes SHALL treat this entity set as the authoritative baseline unless they explicitly extend it.

#### Scenario: Preserve existing translation tables
- **WHEN** Day 1 community schema is applied
- **THEN** the change SHALL add only new community tables
- **AND** it SHALL not alter `public.translation_tasks` or `public.user_settings`.

### Requirement: Community indexes and integrity constraints are frozen
The system SHALL define the baseline constraints and indexes needed for the Day 1 community schema.

#### Scenario: Protect paper identity and feed lookup paths
- **WHEN** the `papers` table is created
- **THEN** the change SHALL define constrained state fields for source, visibility, publication status, and translation status
- **AND** it SHALL define indexes for public feed sorting, translation-state filtering, creator filtering, and non-null `arxiv_id` uniqueness.

#### Scenario: Protect foreign-key access paths
- **WHEN** related community tables are created
- **THEN** the change SHALL define indexes on foreign-key or ownership columns used by joins, cascades, or RLS filters
- **AND** the schema SHALL use explicit primary keys or composite primary keys for unique interaction records.

### Requirement: Community RLS boundaries and helper functions are frozen
The system SHALL define baseline RLS boundaries for end users, admins, and service role writes.

#### Scenario: Normal users write only self-owned interaction records
- **WHEN** an authenticated end user performs a Day 1 community write
- **THEN** the user SHALL only be able to create, view, update, or delete records that are explicitly self-owned for interaction tables
- **AND** protected objects such as `papers`, `paper_assets`, `moderation_actions`, and `user_bans` SHALL remain reserved to admin or service-role execution.

#### Scenario: Admin checks use helper functions
- **WHEN** an admin or moderator accesses a protected Day 1 table through an authenticated client
- **THEN** the RLS policies SHALL rely on helper functions to determine admin authority
- **AND** those helper functions SHALL be defined in the `public` schema with `security definer` semantics.

#### Scenario: Public reads are limited to visible community content
- **WHEN** an anonymous or authenticated client reads community content
- **THEN** the client SHALL be able to read only `papers` rows marked public and comments attached to readable papers with visible comment status
- **AND** notifications, user bans, and moderation actions SHALL not be publicly readable.

### Requirement: Community page boundaries are frozen for Days 2-10
The system SHALL define `/`, `/paper/:paperId`, `/submit`, and `/admin/moderation` as the canonical community MVP surfaces.

#### Scenario: Freeze feed and detail surfaces
- **WHEN** frontend pages are scoped for the 10-day rollout
- **THEN** `/` SHALL remain the feed surface for latest, translated, and hot paper discovery
- **AND** `/paper/:paperId` SHALL remain the paper-centric detail surface for metadata, translation status, assets, and interaction entry points.

#### Scenario: Freeze submit and moderation surfaces
- **WHEN** frontend pages are scoped for the 10-day rollout
- **THEN** `/submit` SHALL remain the entry point for upload or arXiv-based paper intake
- **AND** `/admin/moderation` SHALL remain the minimum moderation console for report review and moderation actions.

