## MODIFIED Requirements
### Requirement: Reader exposes explicit source and translated mode control
The public reader SHALL let users intentionally switch between English-source and Chinese-translated reading whenever both modes are available, and it SHALL expose the paper-detail mode controls in the order `英文`, `译文 PDF`, `译文 HTML`, `中英双栏对照`.

#### Scenario: Both English and Chinese readers exist
- **WHEN** a paper has both source-readable and translated-readable modes
- **THEN** the detail page SHALL expose explicit mode switches for `英文`, `译文 PDF`, `译文 HTML`, and `中英双栏对照` in that order whenever the underlying assets for those modes are available
- **AND** changing modes SHALL preserve the existing reader-first shell instead of leaving the paper detail workflow.

#### Scenario: Translated PDF is available on first open
- **WHEN** the detail page opens for a paper whose translated PDF mode is available
- **THEN** the page SHALL default the reader to translated PDF
- **AND** it SHALL only fall back to another available mode when translated PDF is not available.

#### Scenario: User opens bilingual compare mode
- **WHEN** both source PDF and translated PDF are available and the user selects `中英双栏对照`
- **THEN** the existing main reader area SHALL render the source PDF on the left and the translated PDF on the right
- **AND** the page SHALL keep the overall detail-page layout unchanged outside that reader area.

## ADDED Requirements
### Requirement: Source HTML reading avoids duplicated paper header content
The public paper detail reader SHALL avoid repeating the paper title and author list inside the rendered source HTML body when that content is already presented in the page chrome.

#### Scenario: Render source HTML with a repeated title/author lead block
- **WHEN** the source HTML body begins with a title-and-author block that duplicates the visible paper metadata already shown by the page shell
- **THEN** the reader SHALL remove that leading duplicated block from the rendered HTML body
- **AND** it SHALL preserve the remaining article content structure.
