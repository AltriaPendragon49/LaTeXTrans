## RENAMED Requirements

- FROM: `### Requirement: Community RLS boundaries and helper functions are frozen`
- TO: `### Requirement: Community authorization boundaries are frozen`

## MODIFIED Requirements

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
