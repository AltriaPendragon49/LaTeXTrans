## ADDED Requirements
### Requirement: Historical Ordinary Task Assets Backfill To COS
The system SHALL support backfilling historical ordinary-task sources and outputs from local disk to COS so completed tasks remain downloadable after local cleanup.

#### Scenario: Historical task sources migrate to COS
- **WHEN** an existing task has a local `source_path` under `data/uploads`
- **THEN** the migration SHALL upload that source tree to COS under the matching logical `data/uploads/...` prefix
- **AND** the task `source_path` SHALL be updated to the backend-relative logical path used for COS materialization.

#### Scenario: Historical task outputs migrate with manifests
- **WHEN** an existing task has a local `output_path` under `data/outputs`
- **THEN** the migration SHALL upload that output tree to COS under the matching logical `data/outputs/<task_id>` prefix
- **AND** it SHALL write a `storage_manifest.json` that lets COS-mode download and preview routes locate translated PDF, translated-source archive, terminology CSV, and logs.

#### Scenario: Retained failed artifacts migrate to COS
- **WHEN** a retained failed curation job has a local failed artifact reference
- **THEN** the migration SHALL upload that retained artifact to COS under the failed-task namespace
- **AND** the curation job SHALL record `artifact_storage_backend=object_storage` with a COS-resolvable failed artifact path.

#### Scenario: Local cleanup only deletes manifest-covered assets
- **WHEN** COS-mode verification has passed after migration
- **THEN** local cleanup SHALL delete only migrated paths covered by the final migration manifest
- **AND** it SHALL not delete unrelated caches or operator files as part of asset cleanup.
