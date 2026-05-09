## ADDED Requirements
### Requirement: arXiv raw downloads can use COS origin cache
When object storage mode and arXiv raw cache are enabled, the system SHALL prefer COS raw-cache objects for arXiv source archives and original PDFs before contacting arXiv directly.

#### Scenario: Source archive materializes through COS raw cache
- **WHEN** an arXiv translation task needs the e-print source archive
- **AND** `STORAGE_BACKEND_MODE=cos`
- **AND** `ARXIV_RAW_CACHE_ENABLED=true`
- **THEN** the backend SHALL first request the configured COS raw-cache `e-print/<arxiv_id>` object
- **AND** it SHALL materialize the returned bytes into the local runtime source directory for parsing and translation.

#### Scenario: COS raw cache failure falls back to direct arXiv
- **WHEN** the COS raw-cache source request fails because the object or mirror-origin rule is unavailable
- **THEN** the backend SHALL fall back to the existing direct arXiv source endpoints
- **AND** the task SHALL preserve the existing arXiv download error handling semantics.

#### Scenario: Original PDF materializes through COS raw cache
- **WHEN** the backend needs the original arXiv PDF for runtime cache, source PDF asset creation, or thumbnail generation
- **AND** raw cache is enabled
- **THEN** it SHALL prefer the configured COS raw-cache `pdf/<arxiv_id>` object before direct arXiv PDF retrieval
- **AND** signed responses SHALL still present a `.pdf` filename for browser download and preview behavior.

### Requirement: Local arXiv files remain runtime cache in COS mode
When object storage mode is active, locally materialized arXiv raw files SHALL be treated as temporary runtime cache rather than long-lived durable storage.

#### Scenario: Runtime materialization is separate from durable assets
- **WHEN** the backend downloads a COS raw-cache arXiv source archive or original PDF into a local work directory
- **THEN** the local file SHALL only be used for parsing, compiling, validation, thumbnail generation, or upload staging
- **AND** durable generated artifacts SHALL continue to be stored through the configured object storage backend.
