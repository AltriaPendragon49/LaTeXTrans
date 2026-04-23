## ADDED Requirements
### Requirement: Narrow-screen reading defaults to translated single-column mode
The public paper-reading experience SHALL default narrow/mobile viewports to a translated-first single-column reading presentation whenever translated reading assets are available.

#### Scenario: Mobile paper detail opens with translated reading available
- **WHEN** a user opens a paper detail page on a narrow/mobile viewport
- **AND** translated reading content is available
- **THEN** the reader SHALL default to a single-column translated presentation
- **AND** the UI SHALL not default to a side-by-side bilingual or dual-pane reading layout

#### Scenario: Mobile paper detail falls back when translated reading is unavailable
- **WHEN** a user opens a paper detail page on a narrow/mobile viewport
- **AND** translated reading content is not available
- **THEN** the page SHALL fall back to the best available readable source mode
- **AND** it SHALL keep the single-column mobile reading structure

### Requirement: Narrow-screen reading support uses explicit secondary surfaces
The public paper-reading experience SHALL move mobile secondary reading-support content into explicit toggles instead of keeping desktop-persistent support panes visible beside the reader.

#### Scenario: Mobile paper detail exposes support content
- **WHEN** a user needs insights, similar papers, paper metadata, or other reading-support content on a narrow/mobile viewport
- **THEN** the page SHALL expose that support content through explicit tabs, drawers, sheets, or collapsible regions
- **AND** those secondary surfaces SHALL not crowd the default single-column reader

#### Scenario: Mobile preview route opens on a narrow screen
- **WHEN** a user opens the preview route on a narrow/mobile viewport
- **THEN** the preview SHALL default to a single-document translated reading view
- **AND** alternate source or comparison views SHALL remain available through explicit user switching rather than simultaneous side-by-side rendering
