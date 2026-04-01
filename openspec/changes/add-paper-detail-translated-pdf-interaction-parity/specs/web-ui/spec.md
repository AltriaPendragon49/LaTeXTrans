## ADDED Requirements
### Requirement: Paper detail translated-PDF mode supports interactive selection context
The web UI SHALL provide translated-PDF reader interactions that support user text selection and copilot context grounding inside paper detail.

#### Scenario: User selects translated-PDF text and sends Ask AI
- **WHEN** the user is in translated-PDF mode and selects readable text
- **THEN** the UI SHALL capture selection context and allow sending it to the paper-detail copilot as `reader_selection`
- **AND** the right-pane conversation SHALL continue in-place without route changes.

#### Scenario: Selection context remains visible until user clears it
- **WHEN** translated-PDF selection context is active and the user focuses the copilot composer
- **THEN** the selected location SHALL remain visibly marked in the reader
- **AND** clearing selection context SHALL remove that visual mark.

### Requirement: Paper detail translated-PDF mode supports highlight and notes parity
The web UI SHALL support highlight create/remove and note association for translated-PDF selections with behavior aligned to paper-detail HTML mode.

#### Scenario: User creates and removes translated-PDF highlight
- **WHEN** the user applies a highlight color to a translated-PDF selection
- **THEN** the UI SHALL create a stable highlight/note entry that can be removed later
- **AND** removing the highlight SHALL immediately update both reader overlay and notes list.

#### Scenario: Notes panel focuses translated-PDF location
- **WHEN** the user clicks a translated-PDF note/highlight entry in `My Notes`
- **THEN** the reader SHALL navigate to the linked translated-PDF location
- **AND** the linked location SHALL receive visible focus feedback.

### Requirement: Paper detail translated-PDF navigation degrades gracefully
The web UI SHALL provide deterministic fallback behavior when translated-PDF locator resolution is unavailable.

#### Scenario: Citation anchor cannot resolve to translated-PDF location
- **WHEN** the user opens a citation targeting the current paper but no translated-PDF locator is resolvable
- **THEN** the UI SHALL automatically switch to translated HTML mode for that paper detail session
- **AND** it SHALL preserve current conversation state while navigating to the resolved anchor in translated HTML.

### Requirement: Translated-PDF interaction parity is desktop-first in first release
The web UI SHALL deliver translated-PDF interaction parity on desktop viewports first, with mobile-safe fallback behavior in the initial release.

#### Scenario: Desktop viewport uses translated-PDF interactive parity
- **WHEN** the user opens paper detail on a desktop-width viewport in translated-PDF mode
- **THEN** the UI SHALL provide translated-PDF interactive selection, highlight, notes, and copilot grounding behavior as specified.

#### Scenario: Mobile viewport uses initial fallback behavior
- **WHEN** the user opens paper detail on a narrow/mobile viewport in translated-PDF mode during the first release
- **THEN** the UI SHALL fall back to compatible non-parity behavior without breaking reading or copilot usage
- **AND** it SHALL avoid claiming full translated-PDF interaction parity on mobile in that release.
