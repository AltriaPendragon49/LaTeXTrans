# community-public-read-experience Specification

## Purpose
TBD - created by archiving change add-community-public-read-experience-foundation. Update Purpose after archive.
## Requirements
### Requirement: Public paper reading is preview-ready before normal reader access
The system SHALL make normal public paper reading rely on pre-materialized preview assets instead of synchronously generating preview HTML during the first reader request.

#### Scenario: Completed public paper becomes reader-ready
- **WHEN** a paper gains a community-readable translated result suitable for the public reader
- **THEN** the system SHALL materialize or schedule materialization of the latest `preview_html` before treating that paper as reader-ready
- **AND** the normal public read path SHALL resolve stored preview assets rather than generating them inline during the reader request.

#### Scenario: Missing or stale preview enters recovery instead of opaque blocking generation
- **WHEN** a public paper preview asset is missing, stale, or invalid
- **THEN** the system SHALL expose a clear unavailable or warming state for the public reader
- **AND** any repair or regeneration flow SHALL run as an explicit recovery path rather than as the default synchronous reader experience.

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
The system SHALL present the HTML reader as the dominant detail-page surface and keep scholarly reading fidelity improving even when exact PDF layout cannot be reproduced.

#### Scenario: Open a reader-ready paper on a wide desktop viewport
- **WHEN** a user opens a preview-ready paper detail route on a wide screen
- **THEN** the translated HTML reader SHALL occupy the primary portion of the page layout
- **AND** auxiliary workspace or metadata surfaces SHALL remain secondary to the reading surface rather than shrinking it into a small utility pane.

#### Scenario: Render scholarly prose whose source used multi-column layout
- **WHEN** a preview-ready paper contains source content that was originally laid out in two or more columns
- **THEN** the HTML reader SHALL prefer a readable scholarly multi-column approximation where feasible
- **AND** wide elements such as figures, tables, math blocks, and algorithms SHALL remain readable even when exact source-page reproduction is not possible.

#### Scenario: Wide reader content contains tables or figures with local overflow
- **WHEN** a preview-ready paper includes a table, figure, or other wide scholarly block that cannot fit inside the current reader column width
- **THEN** the HTML reader SHALL confine any horizontal overflow to that local block
- **AND** the overall reader viewport SHALL not expose a second global horizontal scrollbar that competes with figure or table interaction.

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
The system SHALL support operator-managed baseline community content so a newly deployed or recently reset environment is not forced to present an empty public homepage.

#### Scenario: Provision a new environment with no organic community submissions
- **WHEN** operators initialize a community environment that has no user-submitted public papers yet
- **THEN** the system SHALL provide a supported way to provision a baseline official featured set
- **AND** the homepage SHALL be able to surface that baseline set through the normal discovery route.

#### Scenario: Baseline content remains distinguishable from later discovery sources
- **WHEN** the homepage displays operator-provisioned baseline content
- **THEN** the system SHALL preserve normal community paper metadata and status semantics
- **AND** the baseline set SHALL not bypass the public paper contract or become an undocumented hardcoded frontend mock.

### Requirement: Public-read performance is measurable and cache-aware
The system SHALL expose enough operational signals and cache behavior to verify that public reading readiness is improving.

#### Scenario: Measure homepage and paper read readiness
- **WHEN** the system serves public homepage, detail, or preview traffic
- **THEN** operators SHALL have measurable readiness signals for first-screen discovery and preview-read availability
- **AND** the implementation SHALL document the intended cache behavior for those public-read paths.

