# community-paper-library-storage Specification

## Purpose
TBD - created by archiving change add-community-day-04b-paper-library-storage-and-publish-flow. Update Purpose after archive.
## Requirements
### Requirement: Community papers own library-copied assets
The system SHALL persist community-readable paper assets under a dedicated community library directory instead of treating task working directories as the long-term paper asset source.

#### Scenario: Copy translated assets into the community library
- **WHEN** a community paper syncs a successful task result
- **THEN** the system SHALL copy `source_archive`, `translated_pdf`, and `preview_html` into a paper-owned community library directory
- **AND** the corresponding `paper_assets.file_path` values SHALL be stored as relative paths.

### Requirement: Community preview and download resolve library-relative paths
The system SHALL resolve public preview and download reads from stored relative community library paths.

#### Scenario: Read preview HTML from a stored relative path
- **WHEN** a community paper preview asset stores a relative `file_path`
- **THEN** `GET /api/papers/{paper_id}/preview` SHALL resolve that relative path against backend storage configuration
- **AND** it SHALL return the preview content without exposing filesystem paths publicly.

#### Scenario: Download translated PDF from a stored relative path
- **WHEN** a community paper translated PDF asset stores a relative `file_path`
- **THEN** the signed community download gateway SHALL resolve and stream the file successfully
- **AND** successful downloads SHALL still increment `download_count`.

### Requirement: Completed admin curation runs publish into the community library
The system SHALL let successful admin curation runs become community-library papers only after the full curation pipeline succeeds.

#### Scenario: Publish a fully successful admin curation run
- **WHEN** an admin curation run completes intake, metadata preparation, translation, and structured insight generation successfully
- **THEN** the system SHALL create or reuse the canonical community paper record
- **AND** it SHALL copy the selected community assets into that paper's community library directory.

### Requirement: Community hard delete removes library assets completely
The system SHALL remove a hard-deleted community paper from both local database records and local community-library storage.

#### Scenario: Admin hard deletes a community paper
- **WHEN** an authorized admin performs a hard delete for a community paper
- **THEN** the system SHALL delete the paper's local `community_papers/<paper_id>` directory and related stored asset rows
- **AND** the corresponding paper SHALL no longer resolve through normal community preview, detail, or download flows.

### Requirement: Curated papers persist their final similar-recommendation package locally
The community paper library SHALL persist the final similar-paper recommendation package for newly curated public papers.

#### Scenario: Curation stores similar recommendations
- **WHEN** a newly curated paper completes recommendation generation during admin curation
- **THEN** the system SHALL store the final top-10 similar recommendation items locally under that paper
- **AND** each stored item SHALL preserve its display order, title, abstract, `arxiv_id`, `arxiv_url`, `community_paper_id`, and link type.

#### Scenario: Paper deletion removes persisted recommendations
- **WHEN** a community paper is hard-deleted
- **THEN** the system SHALL delete its persisted similar recommendation rows together with the rest of the paper-owned local records.

