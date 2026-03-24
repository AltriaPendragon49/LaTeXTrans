# community-public-read-experience Specification

## Purpose
TBD - created by archiving change add-community-public-read-experience-foundation. Update Purpose after archive.
## Requirements
### Requirement: Public paper reading is preview-ready before normal reader access
The public paper reading experience SHALL continue trying to expose translated reading artifacts when translated section outputs or translated PDFs exist, even if compilation fails.

#### Scenario: Failed task still has translated section outputs
- **WHEN** a translation task ends in a compile-related terminal failure but translated section outputs remain available
- **THEN** the system SHALL still attempt to generate translated HTML preview from those outputs
- **AND** the detail page SHALL be allowed to surface that translated HTML as a readable state.

#### Scenario: Failed task still has a translated PDF
- **WHEN** a translation task fails but a translated PDF artifact exists
- **THEN** the system SHALL preserve that translated PDF as a readable fallback
- **AND** the detail page SHALL present it as a degraded translated mode rather than as total translated unavailability.

### Requirement: Public paper detail avoids a user-visible metadata-to-preview waterfall
The system SHALL provide a first-read contract that makes paper detail and reading content effectively single-phase for normal users.

#### Scenario: Open a paper detail page that has a ready preview
- **WHEN** a user navigates to a paper detail route for a preview-ready paper
- **THEN** the system SHALL deliver the metadata and reading bootstrap needed for normal reading without a user-visible multi-step waterfall
- **AND** the page SHALL not require the reader to wait through a separate visibly serialized metadata request and preview request chain before reading can begin.

#### Scenario: Navigate to a paper detail page whose reader is still warming
- **WHEN** a user opens a paper detail route for a paper whose preview is not yet reader-ready
- **THEN** the page SHALL communicate that the reader is warming or unavailable
- **AND** the non-reader metadata SHALL still render without pretending that full reading is immediately ready.

### Requirement: Public HTML reading prioritizes a paper-like reading surface
The public reading experience SHALL prefer a sanitized local reader presentation for English arXiv HTML before falling back to PDF or external source links.

#### Scenario: arXiv HTML is available
- **WHEN** the paper has an arXiv HTML source
- **THEN** the system SHALL prefer rendering sanitized article content inside the local reader shell
- **AND** it SHALL remove or demote non-reader chrome that does not help the community reading experience.

#### Scenario: English HTML is unavailable
- **WHEN** the paper does not have usable English HTML content
- **THEN** the detail page SHALL fall back to English source PDF before presenting an empty HTML-like state
- **AND** the reader SHALL keep the paper readable inside the community flow.

### Requirement: Public math and caption rendering avoids duplicate or malformed formula output
The system SHALL prefer a single readable math presentation and SHALL not leak broken inline-math fragments into prose or captions.

#### Scenario: Display math is already renderable in the HTML reader
- **WHEN** a block formula is rendered through the HTML reader math pipeline
- **THEN** the page SHALL show one readable formula presentation
- **AND** it SHALL not leave a second raw horizontal text transcription beside or below the rendered formula.

#### Scenario: A caption or prose fragment contains malformed inline math
- **WHEN** preview generation encounters an unmatched or truncated inline-math fragment such as a dangling `$...`
- **THEN** the reader SHALL repair or remove that malformed fragment from visible prose
- **AND** the page SHALL not expose visibly broken math like `$s_c^{2D`.

#### Scenario: Scholarly formulas or references were split by translation artifacts
- **WHEN** preview generation encounters a display equation, figure caption, or bibliography entry that still contains raw helper commands or is split into multiple broken textual fragments
- **THEN** the reader SHALL normalize those fragments into one readable scholarly presentation
- **AND** it SHALL not expose raw helpers such as `\textbf{}`, `\newblock`, `\natexlab`, or visibly duplicated formula text beside the rendered equation.

### Requirement: Public community deployments support a cold-start content floor
The system SHALL continue to support seeded or newly imported English-readable papers before Chinese output is ready.

#### Scenario: Imported English papers remain readable before translation
- **WHEN** a public paper only has English-readable artifacts
- **THEN** the detail page SHALL keep that English reading path usable
- **AND** translation status SHALL not remove English readability while Chinese output is still missing or degraded.

### Requirement: Public-read performance is measurable and cache-aware
The system SHALL expose enough operational signals and cache behavior to verify that public reading readiness is improving.

#### Scenario: Measure homepage and paper read readiness
- **WHEN** the system serves public homepage, detail, or preview traffic
- **THEN** operators SHALL have measurable readiness signals for first-screen discovery and preview-read availability
- **AND** the implementation SHALL document the intended cache behavior for those public-read paths.

### Requirement: Reader state upgrades use soft feedback instead of abrupt page replacement
The system SHALL surface completion and failure as soft experience feedback rather than abrupt hard refreshes or dead-end error pages whenever a readable fallback still exists.

#### Scenario: Chinese reader becomes ready while the user is on the detail page
- **WHEN** a user is viewing an English-readable paper and the Chinese reader becomes ready
- **THEN** the page SHALL surface a lightweight completion message
- **AND** the reader area SHALL present the change as a soft upgrade rather than a disorienting full-page replacement.

#### Scenario: Translation fails but readable output still exists
- **WHEN** Chinese generation fails but English or translated fallback reading still exists
- **THEN** the page SHALL explain that generation degraded
- **AND** it SHALL keep the best available readable mode visible instead of collapsing into a fatal error page.

### Requirement: Reader exposes explicit source and translated mode control
The public reader SHALL let users intentionally switch between English-source and Chinese-translated reading whenever both modes are available.

#### Scenario: Both English and Chinese readers exist
- **WHEN** a paper has both source-readable and translated-readable modes
- **THEN** the detail page SHALL expose an explicit mode switch for English and Chinese
- **AND** changing modes SHALL preserve the reader-first shell instead of leaving the paper detail workflow.

