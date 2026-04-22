## MODIFIED Requirements
### Requirement: Document Feed Dual Thumbnails
The community document feed (homepage) SHALL render document cards emphasizing dual visual preview of documents.

#### Scenario: Rendering document cards
- **WHEN** the community feed loads document items
- **THEN** each item SHALL display side-by-side thumbnails showing the original PDF on the left and the translated PDF on the right.

#### Scenario: First page fits within thumbnail frame
- **WHEN** a card renders either original or translated PDF preview
- **THEN** the first page SHALL be scaled to fit inside the thumbnail frame while preserving aspect ratio
- **AND** the preview SHALL avoid clipping key page content at top or bottom.

#### Scenario: Hover enlarges the original card instead of opening a magnifier
- **WHEN** the user hovers a homepage PDF preview card
- **THEN** the same preview card SHALL visually enlarge in place with a static full-page preview
- **AND** the UI SHALL NOT render a separate magnifier or inspector overlay
- **AND** the preview SHALL NOT track mouse position for partial-page zooming.
