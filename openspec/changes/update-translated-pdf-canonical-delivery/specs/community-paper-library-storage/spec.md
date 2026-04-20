## MODIFIED Requirements
### Requirement: Community papers own library-copied assets
The system SHALL persist community-readable paper assets under one canonical community-owned storage namespace instead of treating task working directories as the long-term paper asset source.

#### Scenario: Copy translated assets into the canonical community store
- **WHEN** a community paper syncs a successful task result
- **THEN** the system SHALL copy `source_archive`, `translated_pdf`, and `preview_html` into a paper-owned canonical asset namespace
- **AND** production SHALL persist those assets in object storage while local development MAY persist them on local disk
- **AND** the corresponding `paper_assets` rows SHALL record the active storage backend together with the canonical storage reference.

#### Scenario: Canonical translated PDF delivery stays trimmed before publish
- **WHEN** the system persists a translated PDF into the canonical community store
- **THEN** it SHALL apply mandatory leading-blank-page trimming before the asset becomes the latest public translated PDF
- **AND** the latest translated PDF asset SHALL represent the final public delivery file rather than a request-time derived artifact.

## ADDED Requirements
### Requirement: Existing community translated PDFs can be upgraded in place
The system SHALL provide an operator backfill path that upgrades existing community translated PDF assets to the canonical trimmed delivery format without requiring full re-curation.

#### Scenario: Backfill upgrades an existing translated PDF asset
- **WHEN** an operator runs the translated PDF delivery backfill for a paper whose current translated PDF asset is still recoverable
- **THEN** the system SHALL generate the canonical trimmed delivery PDF from the current asset
- **AND** it SHALL upsert that result as the latest translated PDF asset for the same paper.

#### Scenario: Backfill skips an unrecoverable translated PDF asset
- **WHEN** an operator runs the translated PDF delivery backfill for a paper whose translated PDF cannot be recovered
- **THEN** the system SHALL leave the current paper record unchanged
- **AND** it SHALL report the paper as skipped instead of requiring an immediate full re-curation.
