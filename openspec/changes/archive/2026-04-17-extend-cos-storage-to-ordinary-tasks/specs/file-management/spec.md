## MODIFIED Requirements
### Requirement: File Upload Handling
The system SHALL accept LaTeX source files via HTTP upload for translation processing.  
When ordinary-task object storage mode is enabled, the uploaded source SHALL be durably persisted to COS while local upload directories remain temporary runtime cache only.

#### Scenario: Upload single .tex file
- **WHEN** user uploads a `.tex` file via `POST /upload`
- **THEN** the system generates a unique task ID, stores the file in `data/uploads/{task_id}/`, and returns `{task_id, status: "pending"}`

#### Scenario: Upload .zip archive
- **WHEN** user uploads a `.zip` file containing LaTeX source
- **THEN** the system extracts the archive to `data/uploads/{task_id}/`, validates the presence of `.tex` files, and returns the task ID

#### Scenario: Invalid file type rejected
- **WHEN** user uploads a file with unsupported extension (not `.tex` or `.zip`)
- **THEN** the system returns HTTP 400 with error message "Unsupported file type"

#### Scenario: File size limit enforcement
- **WHEN** user uploads a file larger than 50MB
- **THEN** the system returns HTTP 413 with error message "File too large (max 50MB)"

#### Scenario: Ordinary-task upload is durably persisted to COS
- **WHEN** `STORAGE_BACKEND_MODE=cos` and an ordinary-task upload passes LaTeX validation
- **THEN** the source tree SHALL be durably written to COS under the logical `data/uploads/...` task location
- **AND** the task record SHALL keep a storage-resolvable `source_path`
- **AND** the local upload directory MAY be deleted after durable persistence succeeds

### Requirement: arXiv Source Retrieval
The system SHALL download LaTeX source files from arXiv when provided with a valid arXiv ID.  
When ordinary-task object storage mode is enabled, the downloaded source SHALL be durably persisted to COS and treated as the authoritative source copy.

#### Scenario: Valid arXiv ID provided
- **WHEN** user submits arXiv ID (e.g., "2508.18791") via `POST /arxiv`
- **THEN** the system downloads the `.tar.gz` source, extracts it to `data/uploads/{task_id}/`, and returns the task ID

#### Scenario: Invalid arXiv ID rejected
- **WHEN** user submits malformed arXiv ID (e.g., "invalid-id")
- **THEN** the system returns HTTP 400 with error message "Invalid arXiv ID format"

#### Scenario: arXiv download failure
- **WHEN** arXiv API is unreachable or paper ID doesn't exist
- **THEN** the system returns HTTP 502 with error message "Failed to download from arXiv: {reason}"

#### Scenario: Ordinary-task arXiv source is durably persisted to COS
- **WHEN** `STORAGE_BACKEND_MODE=cos` and an arXiv ordinary task finishes source download successfully
- **THEN** the source tree SHALL be durably written to COS under the logical `data/uploads/...` location
- **AND** later translation runs SHALL be able to rehydrate the source from COS even if no long-lived local copy remains

## ADDED Requirements
### Requirement: Ordinary Task Durable Output Persistence
When ordinary-task object storage mode is enabled, the system SHALL persist translation outputs to COS as the durable source of truth and SHALL keep local output directories only as temporary runtime cache.

#### Scenario: Successful translation output is durably persisted
- **WHEN** an ordinary task reaches `completed` or `completed_with_warnings` in COS mode
- **THEN** the output tree SHALL be durably written to COS under the logical `data/outputs/{task_id}` location
- **AND** the system SHALL persist an output manifest that identifies translated PDF, translated-source archive, terminology CSV, and available log files for later retrieval
- **AND** the local runtime output directory MAY be deleted after durable persistence succeeds

#### Scenario: Failed translation output still preserves durable artifacts
- **WHEN** an ordinary task reaches a terminal failure state in COS mode and output artifacts exist
- **THEN** the available output files SHALL be durably written to COS under the logical `data/outputs/{task_id}` location before local cache cleanup
- **AND** later log retrieval SHALL NOT require a pre-existing long-lived local output directory

#### Scenario: Ordinary task rehydrates source from COS for runtime execution
- **WHEN** an ordinary task in COS mode starts translation without a reusable local source directory
- **THEN** the backend SHALL materialize the source tree from COS into a temporary local runtime directory
- **AND** the translation runtime SHALL use that hydrated local directory without changing the durable `source_path`
