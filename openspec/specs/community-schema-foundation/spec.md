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
The system SHALL define the baseline constraints and indexes needed for the community schema, including the ownership and authorization access paths required after removing database RLS.

#### Scenario: Protect paper identity and feed lookup paths
- **WHEN** the `papers` table is created
- **THEN** the schema SHALL define constrained state fields for source, visibility, publication status, and translation status
- **AND** it SHALL define indexes for public feed sorting, translation-state filtering, creator filtering, and non-null `arxiv_id` uniqueness.

#### Scenario: Protect foreign-key and ownership access paths
- **WHEN** related community tables are created
- **THEN** the schema SHALL define indexes on foreign-key or ownership columns used by joins, cascades, or application-layer authorization filters
- **AND** the schema SHALL use explicit primary keys or composite primary keys for unique interaction records.

### Requirement: Community page boundaries are frozen for Days 2-10
The community page-boundary contract SHALL allow the shared shell to prioritize the community flow while moving translation-oriented tool pages behind a secondary tools hub.

#### Scenario: Shared shell prioritizes community over tools
- **WHEN** the frontend shared shell is rendered for this phase
- **THEN** the primary navigation SHALL be allowed to foreground the community homepage as the main first-level destination
- **AND** translation-centric tools MAY move behind a secondary tools entry without violating the community page-boundary contract.

### Requirement: Community authorization boundaries are frozen
The system SHALL define baseline application-layer authorization boundaries for end users, admins, and service-level maintenance flows after removing Supabase RLS.

#### Scenario: Normal users write only self-owned interaction records
- **WHEN** an authenticated end user performs a community write
- **THEN** the user SHALL only be able to create, view, update, or delete records that are explicitly self-owned for interaction tables
- **AND** protected objects such as `papers`, `paper_assets`, `moderation_actions`, and `user_bans` SHALL remain reserved to admin or service-level execution.

#### Scenario: Admin checks use local role authority
- **WHEN** an admin or moderator accesses a protected community table through an authenticated client
- **THEN** the application SHALL determine admin authority from local user-role state
- **AND** it SHALL NOT depend on Supabase helper functions or service-role metadata for that authorization decision.

#### Scenario: Public reads are limited to visible community content
- **WHEN** an anonymous or authenticated client reads community content
- **THEN** the client SHALL be able to read only `papers` rows marked public and comments attached to readable papers with visible comment status
- **AND** notifications, user bans, and moderation actions SHALL not be publicly readable.

