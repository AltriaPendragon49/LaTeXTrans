# community-schema-foundation Specification

## Purpose
TBD - created by archiving change add-community-day-01-schema-rls-foundation. Update Purpose after archive.
## Requirements
### Requirement: Community schema entities are frozen
The community schema SHALL reserve room for source-readable and translated-readable paper states without requiring a second object model for English vs Chinese paper pages.

#### Scenario: Paper assets support English-readable and Chinese-readable states
- **WHEN** the community stores paper assets
- **THEN** the schema SHALL support asset semantics that distinguish readable English-source artifacts from readable translated artifacts
- **AND** the product SHALL continue to treat those as states of the same `paper` object rather than separate papers.

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
The community page-boundary contract SHALL allow the shared shell to prioritize the community flow while moving translation-oriented tool pages behind a secondary tools hub.

#### Scenario: Shared shell prioritizes community over tools
- **WHEN** the frontend shared shell is rendered for this phase
- **THEN** the primary navigation SHALL be allowed to foreground the community homepage as the main first-level destination
- **AND** translation-centric tools MAY move behind a secondary tools entry without violating the community page-boundary contract.

