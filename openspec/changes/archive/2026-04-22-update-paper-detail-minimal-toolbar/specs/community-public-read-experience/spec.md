## ADDED Requirements
### Requirement: Paper detail toolbar stays minimal and reader-first
The public paper detail route SHALL present a thin single-row toolbar that preserves reader controls and core actions without keeping title, author, status, and other metadata blocks permanently visible above the reading surface.

#### Scenario: Reader opens with a minimal toolbar
- **WHEN** a user opens a paper detail page
- **THEN** the sticky toolbar SHALL keep the back action pinned to the far left edge of the row
- **AND** the reader mode switch SHALL remain available in a lightweight rectangular control near the center of the row
- **AND** the route SHALL not render the previous expandable metadata banner, title block, category chips, status pills, or inline publication row above the reader.

#### Scenario: Toolbar actions stay independent and compact
- **WHEN** the toolbar renders its paper actions
- **THEN** it SHALL display four independent icon actions in this order: favorite, translated-PDF download, paper info, and share
- **AND** those actions SHALL not be wrapped inside a larger rounded capsule container
- **AND** the download action SHALL continue downloading the translated PDF when that asset is available.

#### Scenario: Paper metadata is available on demand
- **WHEN** the user activates the info action
- **THEN** the page SHALL reveal a card-style metadata panel for the current paper
- **AND** that panel SHALL surface core paper information such as title, authors, publication time, categories, and external identifiers or links when available
- **AND** closing the panel SHALL return the user to the unchanged reading layout.

#### Scenario: Share copies the current paper detail URL
- **WHEN** the user activates the share action
- **THEN** the page SHALL copy the current paper detail URL to the clipboard
- **AND** it SHALL provide lightweight feedback without navigating away from the paper.
