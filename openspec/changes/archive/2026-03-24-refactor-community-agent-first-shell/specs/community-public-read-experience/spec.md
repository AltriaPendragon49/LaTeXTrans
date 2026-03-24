## MODIFIED Requirements

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

### Requirement: Public community deployments support a cold-start content floor
The system SHALL continue to support seeded or newly imported English-readable papers before Chinese output is ready.

#### Scenario: Imported English papers remain readable before translation
- **WHEN** a public paper only has English-readable artifacts
- **THEN** the detail page SHALL keep that English reading path usable
- **AND** translation status SHALL not remove English readability while Chinese output is still missing or degraded.

## ADDED Requirements

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
