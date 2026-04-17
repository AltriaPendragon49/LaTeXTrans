# community-paper-library-storage Specification

## Purpose
TBD - created by archiving change add-community-day-04b-paper-library-storage-and-publish-flow. Update Purpose after archive.
## Requirements
### Requirement: Community papers own library-copied assets
The system SHALL persist community-readable paper assets under one canonical community-owned storage namespace instead of treating task working directories as the long-term paper asset source.

#### Scenario: Copy translated assets into the canonical community store
- **WHEN** a community paper syncs a successful task result
- **THEN** the system SHALL copy `source_archive`, `translated_pdf`, and `preview_html` into a paper-owned canonical asset namespace
- **AND** production SHALL persist those assets in object storage while local development MAY persist them on local disk
- **AND** the corresponding `paper_assets` rows SHALL record the active storage backend together with the canonical storage reference.

### Requirement: Community preview and download resolve library-relative paths
The system SHALL resolve public preview and download reads from canonical asset references without assuming that published community assets live permanently on local disk.

#### Scenario: Read preview HTML from an object-storage-backed asset
- **WHEN** a community paper preview asset stores an object-storage reference
- **THEN** the preview read path SHALL resolve that asset through the configured object-storage delivery flow
- **AND** it SHALL return or expose reader-safe preview content without exposing internal server filesystem paths.

#### Scenario: Read translated PDF from a local-disk-backed asset
- **WHEN** a community paper translated PDF asset stores a local-disk reference in local development or fallback mode
- **THEN** the existing file-serving path SHALL continue to stream the PDF successfully
- **AND** callers SHALL not need a different API contract for local-disk versus object-storage assets.

### Requirement: Completed admin curation runs publish into the community library
The system SHALL let successful admin curation runs become community-library papers only after the full curation pipeline succeeds.

#### Scenario: Publish a fully successful admin curation run
- **WHEN** an admin curation run completes intake, metadata preparation, translation, and structured insight generation successfully
- **THEN** the system SHALL create or reuse the canonical community paper record
- **AND** it SHALL copy the selected community assets into that paper's community library directory.

### Requirement: Community hard delete removes library assets completely
The system SHALL remove a hard-deleted community paper from both persistent records and its canonical asset store.

#### Scenario: Admin hard deletes an object-storage-backed community paper
- **WHEN** an authorized admin performs a hard delete for a community paper whose canonical assets live in object storage
- **THEN** the system SHALL delete the corresponding object-storage asset prefix and related stored asset rows
- **AND** the corresponding paper SHALL no longer resolve through normal community preview, detail, or download flows.

#### Scenario: Admin hard deletes a local-disk-backed community paper
- **WHEN** an authorized admin performs a hard delete in a local-disk storage mode
- **THEN** the system SHALL continue deleting the paper-owned local asset directory and related stored asset rows
- **AND** the same paper SHALL no longer resolve through normal community preview, detail, or download flows.

### Requirement: Curated papers persist their final similar-recommendation package locally
The community paper library SHALL persist the final similar-paper recommendation package for newly curated public papers.

#### Scenario: Curation stores similar recommendations
- **WHEN** a newly curated paper completes recommendation generation during admin curation
- **THEN** the system SHALL store the final top-10 similar recommendation items locally under that paper
- **AND** each stored item SHALL preserve its display order, title, abstract, `arxiv_id`, `arxiv_url`, `community_paper_id`, and link type.

#### Scenario: Paper deletion removes persisted recommendations
- **WHEN** a community paper is hard-deleted
- **THEN** the system SHALL delete its persisted similar recommendation rows together with the rest of the paper-owned local records.

