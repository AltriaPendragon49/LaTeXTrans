## MODIFIED Requirements
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
