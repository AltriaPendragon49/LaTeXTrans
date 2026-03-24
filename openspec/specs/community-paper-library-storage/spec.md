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

### Requirement: Completed authenticated translation tasks auto-publish to the community library
The system SHALL let successful authenticated translation tasks become community papers without requiring a separate manual publish step.

#### Scenario: Publish a completed task as a fallback community paper
- **WHEN** an authenticated translation task completes successfully
- **AND** no stronger official community paper already owns the same paper identity
- **THEN** the system SHALL create or reuse a community paper record
- **AND** it SHALL sync the task outputs into that paper's community library assets.

#### Scenario: Reuse an existing community paper for the same arXiv identity
- **WHEN** a completed authenticated task has an `arxiv_id`
- **AND** a community paper already exists for that `arxiv_id`
- **THEN** the system SHALL reuse that existing paper record rather than creating a duplicate row.

### Requirement: Normal translation start schedules community publish watching
The system SHALL watch authenticated task-based translations for successful community publishing after the task enters the normal translation engine.

#### Scenario: Start a normal authenticated translation
- **WHEN** an authenticated user starts `POST /translate/{task_id}`
- **THEN** the system SHALL schedule a background community publish watch for that task
- **AND** it SHALL NOT block the normal task processing flow.

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

