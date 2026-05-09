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

#### Scenario: Canonical translated PDF delivery stays trimmed before publish
- **WHEN** the system persists a translated PDF into the canonical community store
- **THEN** it SHALL apply mandatory leading-blank-page trimming before the asset becomes the latest public translated PDF
- **AND** the latest translated PDF asset SHALL represent the final public delivery file rather than a request-time derived artifact.

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

### Requirement: Existing Community Assets Migrate To Object Storage
The system SHALL support migrating existing local-disk community paper assets into the canonical object-storage namespace while preserving existing paper and asset identities.

#### Scenario: Local-disk paper assets are migrated in place
- **WHEN** a community paper has latest `preview_html`, `source_archive`, or `translated_pdf` assets recorded with `storage_backend=local_disk`
- **THEN** the migration SHALL upload each referenced local file to COS under the canonical community asset key
- **AND** the corresponding `paper_assets` row SHALL be updated to `storage_backend=object_storage` with a COS-resolvable `file_path`
- **AND** paper-level latest asset pointers SHALL continue to identify the same latest asset rows.

#### Scenario: Missing local asset blocks row migration
- **WHEN** a local-disk community asset row points to a file that does not exist
- **THEN** the migration SHALL report the row as blocked
- **AND** it SHALL not update that row to object storage until the asset is recovered or explicitly excluded.

#### Scenario: COS orphan community assets are excluded from current papers
- **WHEN** COS contains `data/community_papers/...` objects that are not referenced by the current asset manifest
- **THEN** those objects SHALL be reported as orphan candidates
- **AND** they SHALL only be deleted through the guarded COS cleanup phase.

### Requirement: Core-pool complete assets can sync into local arXiv-ID reading directories
The system SHALL provide an operator script that treats backend asset records as the source of truth for completed core-pool assets, syncs recorded assets into a local arXiv-ID-based reading directory layout, and updates `backend/arxiv_id/core_pool/complete.md` as a human-readable completion report.

#### Scenario: Sync completed arXiv papers discovered from backend records
- **WHEN** an operator runs the sync script without explicit arXiv filters
- **THEN** the script SHALL query backend paper and asset records for latest object-storage assets
- **AND** it SHALL download each non-conflicting asset set that contains `source_archive`, `preview_html`, and `translated_pdf` assets into `data/community_papers/<arxiv_id>/...`.

#### Scenario: Sync updates the completion report from backend records
- **WHEN** a non-dry-run sync discovers complete arXiv IDs from backend asset records
- **THEN** the script SHALL write those discovered IDs to `backend/arxiv_id/core_pool/complete.md`
- **AND** the markdown file SHALL represent completed assets observed in backend records rather than a prerequisite input list.

#### Scenario: Sync finds multiple conflicting recorded asset sets for one arXiv ID
- **WHEN** the sync script finds more than one complete recorded asset set for the same `arXiv ID`
- **THEN** the script SHALL mark that paper as conflicted
- **AND** it SHALL skip downloading that paper until an operator resolves the ambiguity.

#### Scenario: Local operator pulls completed server assets and cleans remote copies
- **WHEN** an operator runs the sync script in remote pull-and-clean mode
- **THEN** the script SHALL SSH to the production server and run the same backend-record sync inside the backend runtime
- **AND** it SHALL archive the synced `data/community_papers/<arxiv_id>/...` directories, download and safely extract them into the local destination root, and update local `complete.md`
- **AND** after a successful local extraction it SHALL delete only the remote arXiv-ID output directories included in that archive plus the temporary archive file.

