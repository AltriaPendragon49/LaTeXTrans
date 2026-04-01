## MODIFIED Requirements

### Requirement: Public paper detail exposes filesystem-safe assets
The system SHALL expose public paper asset metadata needed by the community detail page without leaking raw storage paths.

#### Scenario: Return public asset map on detail
- **WHEN** a client requests a community paper detail payload
- **THEN** the payload SHALL include public-safe asset metadata keyed by asset type
- **AND** the payload SHALL prefer `preview_html` as the latest readable asset when it exists, even if non-reader assets (for example `source_archive`) were updated later
- **AND** the payload SHALL NOT include raw `file_path` values.

### Requirement: Inline paper preview is backed by preview_html
The system SHALL provide a public preview read path for the translated reader surface using a generated HTML asset.

#### Scenario: Read generated preview asset
- **WHEN** a paper has a latest `preview_html` asset
- **THEN** `GET /api/papers/{paper_id}/preview` SHALL return `paper_id`, `task_id`, asset metadata, HTML content, and generation time
- **AND** the response SHALL be safe for the public community reader surface.

#### Scenario: Strict heuristics reject regeneration but readable preview exists
- **WHEN** freshness or untranslated-language heuristics reject normal preview payload generation
- **AND** an existing `preview_html` asset still contains readable article content
- **THEN** `GET /api/papers/{paper_id}/preview` SHALL return a sanitized fallback payload from that existing asset
- **AND** response HTML SHALL suppress legacy raw-source classes or command snippets that would leak TeX source.

#### Scenario: Preview is unavailable
- **WHEN** a paper has no generated `preview_html` asset and no readable fallback preview payload can be produced
- **THEN** `GET /api/papers/{paper_id}/preview` SHALL return `404`.
