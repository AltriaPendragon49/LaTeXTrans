## ADDED Requirements
### Requirement: Production COS Asset Cutover
Production operations SHALL provide a guarded migration path that converts local-disk production assets to COS-backed durable storage without losing current public asset delivery.

#### Scenario: Dry-run manifest precedes destructive operations
- **WHEN** an operator prepares the production asset migration
- **THEN** the system SHALL produce a dry-run manifest listing COS orphan deletion candidates, local files to upload, database rows to update, same-key conflicts, and local cleanup candidates
- **AND** the operator SHALL be able to review this manifest before COS deletion, database updates, or local cleanup execute.

#### Scenario: Writes are paused during cutover
- **WHEN** production asset storage is being cut over from local disk to COS
- **THEN** production write paths SHALL be paused or placed into a maintenance window
- **AND** the migration SHALL not run while new translation outputs or community paper assets can be written to local disk.

#### Scenario: COS mode is verified before local cleanup
- **WHEN** local assets have been uploaded and database pointers have been switched to COS
- **THEN** backend and public API health checks SHALL pass in COS mode
- **AND** representative preview and download routes SHALL resolve assets from COS before migrated local asset directories are deleted.

#### Scenario: Final state reports storage authority
- **WHEN** the migration is complete
- **THEN** the operator report SHALL include final disk usage, COS object totals, MySQL storage-backend counts, and public health-check evidence.
