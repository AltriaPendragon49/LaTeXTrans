# community-paper-translation-bridge Specification

## Purpose
TBD - created by archiving change add-community-day-04-paper-translation-preview-download. Update Purpose after archive.
## Requirements
### Requirement: Paper-owned translation entry reuses the translation contract
The system SHALL let an authenticated user start paper translation through a paper-owned route while reusing the existing translation request contract.

#### Scenario: Reuse active paper task
- **WHEN** a paper already has an active selected task in `queued` or `processing`
- **THEN** `POST /api/papers/{paper_id}/translate` SHALL return that existing task instead of creating a duplicate
- **AND** the response SHALL include a `processing_url` that points to the existing task-centric progress surface.

#### Scenario: Start translation from latest source asset
- **WHEN** a paper has a latest `source_archive` asset and no active selected task
- **THEN** `POST /api/papers/{paper_id}/translate` SHALL create a fresh task from that paper-owned source context
- **AND** the request body SHALL reuse the existing translation request schema used by task-based translation.

#### Scenario: Fall back to arXiv download bridge
- **WHEN** a paper has no reusable local source asset but still has `arxiv_id`
- **THEN** the system SHALL create a new arXiv-backed task and reuse the existing download-and-enqueue pattern
- **AND** the paper SHALL keep the new task as its selected task.

### Requirement: Public paper detail exposes filesystem-safe assets
The system SHALL expose public paper asset metadata needed by the community detail page without leaking raw storage paths.

#### Scenario: Return public asset map on detail
- **WHEN** a client requests a community paper detail payload
- **THEN** the payload SHALL include public-safe asset metadata keyed by asset type
- **AND** the payload SHALL prefer `preview_html` as the latest asset when it exists
- **AND** the payload SHALL NOT include raw `file_path` values.

### Requirement: Inline paper preview is backed by preview_html
The system SHALL provide a public preview read path for the translated reader surface using a generated HTML asset.

#### Scenario: Read generated preview asset
- **WHEN** a paper has a latest `preview_html` asset
- **THEN** `GET /api/papers/{paper_id}/preview` SHALL return `paper_id`, `task_id`, asset metadata, HTML content, and generation time
- **AND** the response SHALL be safe for the public community reader surface.

#### Scenario: Preview is unavailable
- **WHEN** a paper has no generated `preview_html` asset
- **THEN** `GET /api/papers/{paper_id}/preview` SHALL return `404`.

### Requirement: Successful translations sync translated and preview assets
The system SHALL attach translation outputs back to the owning paper through `paper_assets`.

#### Scenario: Sync translated outputs after completion
- **WHEN** a paper-owned task completes successfully
- **THEN** the system SHALL upsert the latest `translated_pdf` asset
- **AND** the system SHALL generate and upsert the latest `preview_html` asset when translated section maps are available
- **AND** the paper SHALL prefer `preview_html` as the selected asset, otherwise `translated_pdf`, otherwise `source_archive`.

### Requirement: Public paper downloads require short-lived signed authorization
The system SHALL guard public paper downloads with a short-lived signed token instead of exposing raw task download routes.

#### Scenario: Create signed download session
- **WHEN** a public paper has a translated PDF asset
- **THEN** `POST /api/papers/{paper_id}/download-session` SHALL return `paper_id`, `asset_id`, `download_url`, and `expires_at`
- **AND** the `download_url` SHALL contain a short-lived signed token.

#### Scenario: Reject invalid or expired download tokens
- **WHEN** a client requests `GET /api/papers/{paper_id}/download?token=...` with an invalid, mismatched, or expired token
- **THEN** the system SHALL reject the request
- **AND** the translated file SHALL NOT be streamed.

#### Scenario: Count only successful paper downloads
- **WHEN** a valid signed paper download succeeds
- **THEN** the system SHALL increment `download_count` for that paper
- **AND** unsigned session issuance SHALL NOT increment the counter.

