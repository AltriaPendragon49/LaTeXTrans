## ADDED Requirements
### Requirement: Community agent persistence stays compatible with MySQL-backed runtime storage
The community agent SHALL normalize persisted conversation, run, and event timestamps before writing them into the local business database so authenticated history remains compatible with MySQL-backed runtime storage.

#### Scenario: Conversation persistence receives ISO 8601 timestamps
- **WHEN** an authenticated community conversation payload includes `created_at` or `updated_at` values in ISO 8601 form with timezone offsets or `Z` suffixes
- **THEN** backend persistence SHALL normalize those timestamps into a local database-compatible datetime representation before insert or update
- **AND** the write SHALL NOT fail solely because the runtime database uses MySQL `DATETIME` columns

#### Scenario: Run persistence receives ISO 8601 event timestamps
- **WHEN** an authenticated community agent run or event payload includes ISO 8601 timestamps with timezone information
- **THEN** backend persistence SHALL normalize `created_at`, `updated_at`, `completed_at`, and event timestamp fields before writing local rows
- **AND** saved conversations and runs SHALL remain readable through the authenticated community workspace after the write completes
