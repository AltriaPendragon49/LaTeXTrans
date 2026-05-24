## ADDED Requirements
### Requirement: Shared raw-cache source PDFs can back community source PDF assets
For arXiv community papers in COS mode, the system SHALL allow the latest `source_pdf` asset to reference the shared COS raw-cache PDF object instead of forcing a duplicate paper-owned copy.

#### Scenario: Publish source PDF as raw-cache-backed asset
- **WHEN** an arXiv community paper publishes successfully
- **AND** COS raw cache is enabled
- **THEN** the system SHALL register the latest `source_pdf` asset with `storage_backend=object_storage`
- **AND** its storage reference SHALL resolve to the configured raw-cache PDF object for that arXiv ID.

#### Scenario: Raw-cache-backed source PDF survives paper deletion safely
- **WHEN** a paper whose `source_pdf` references the shared raw cache is hard-deleted
- **THEN** the paper asset rows SHALL be deleted with the paper
- **AND** the shared raw-cache object SHALL NOT be deleted as part of paper-owned prefix cleanup.

### Requirement: Generated paper thumbnails are durable object-storage assets
When object storage mode is active, generated paper PDF thumbnails SHALL be persisted to COS and served through signed object URLs.

#### Scenario: Thumbnail generated once and served from COS
- **WHEN** the backend generates a source or translated PDF thumbnail
- **THEN** it SHALL upload the generated PNG to COS under a deterministic thumbnail cache key
- **AND** browser thumbnail requests SHALL be redirected to a signed COS URL when the object exists.

#### Scenario: Local thumbnail fallback remains available
- **WHEN** object storage mode is not active
- **THEN** thumbnail routes SHALL continue to return the local generated PNG response without requiring COS.
