## ADDED Requirements
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
