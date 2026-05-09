## ADDED Requirements
### Requirement: Community papers retain original source PDFs in object storage
The system SHALL persist original arXiv PDFs as canonical community paper assets when publishing curated arXiv papers in object-storage-backed production.

#### Scenario: Admin curation stores original PDF in COS
- **WHEN** an admin curation run successfully publishes an arXiv paper
- **AND** object storage is configured as the durable backend
- **THEN** the system SHALL store the original arXiv PDF as a latest `source_pdf` asset under the community paper namespace
- **AND** the `paper_assets` row SHALL record `storage_backend=object_storage`, `mime_type=application/pdf`, and a COS-resolvable `file_path`.

#### Scenario: Source PDF persistence failure does not corrupt translated publish
- **WHEN** translated community assets publish successfully
- **AND** downloading or storing the original arXiv PDF fails
- **THEN** the system SHALL keep the translated paper publish result intact
- **AND** it SHALL record enough warning information for a later `source_pdf` backfill.

#### Scenario: Existing source archive remains distinct from original PDF
- **WHEN** a community paper has both `source_archive` and `source_pdf`
- **THEN** the system SHALL treat `source_archive` as the LaTeX source artifact
- **AND** it SHALL treat `source_pdf` as the original readable PDF artifact.

### Requirement: Existing community papers can backfill original source PDFs
The system SHALL provide an operator path to backfill `source_pdf` assets for existing published arXiv community papers.

#### Scenario: Backfill stores missing source PDF
- **WHEN** an operator runs the source-PDF backfill with execute mode
- **AND** a published arXiv community paper has no latest `source_pdf`
- **THEN** the script SHALL download the original arXiv PDF, persist it to object storage, and upsert the `source_pdf` asset row.

#### Scenario: Backfill dry-run does not write
- **WHEN** an operator runs the source-PDF backfill without execute mode
- **THEN** the script SHALL report candidate papers and target object keys
- **AND** it SHALL NOT write COS objects or update database rows.
