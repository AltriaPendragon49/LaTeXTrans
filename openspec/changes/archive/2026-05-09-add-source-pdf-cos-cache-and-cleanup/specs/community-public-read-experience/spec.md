## MODIFIED Requirements
### Requirement: Public HTML reading prioritizes a paper-like reading surface
The system SHALL prefer a sanitized local reader presentation for English arXiv HTML before falling back to PDF or external source links. This layout will be governed directly by the Stitch Maximized Reader design paradigm.

#### Scenario: arXiv HTML is available
- **WHEN** the paper has an arXiv HTML source
- **THEN** the system SHALL prefer rendering sanitized article content inside the local reader shell shaped by the Maximized Reader constraints
- **AND** it SHALL remove or demote non-reader chrome that does not help the community reading experience.

#### Scenario: English HTML is unavailable
- **WHEN** the paper does not have usable English HTML content
- **THEN** the detail page SHALL fall back to a stored `source_pdf` asset before live arXiv PDF retrieval
- **AND** the reader SHALL keep the paper readable inside the community flow.

#### Scenario: Stored source PDF is available
- **WHEN** a public community paper has a latest `source_pdf` asset
- **THEN** source PDF preview and download routes SHALL resolve that asset through the configured storage backend
- **AND** normal reader access SHALL NOT depend on live arXiv PDF download for that paper.
