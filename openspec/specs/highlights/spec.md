# highlights Specification

## Purpose
TBD - created by archiving change add-paper-detail-interactive-highlights-v1. Update Purpose after archive.
## Requirements
### Requirement: Persistent Paper Highlights
The system SHALL provide persistent, color-coded highlights for selected text ranges in the paper reader that remain visible after mouse release.

#### Scenario: Highlighting text
- **WHEN** user selects text.
- **THEN** a floating toolbar appears and the current selection is visibly marked.

### Requirement: Highlight Color Selection
The system SHALL allow users to choose highlight colors from the toolbar and apply highlight immediately when a color is clicked.

#### Scenario: Applying highlight by selecting color
- **WHEN** user clicks a color circle in the toolbar.
- **THEN** a persisted highlight is created in that color without requiring an extra confirmation button.

### Requirement: Annotation Notes
The system SHALL support adding text notes to highlights, which are stored as part of the annotation.

#### Scenario: Writing a note
- **WHEN** user types in the toolbar note area and then applies highlight by color click.
- **THEN** the note is associated with that specific highlight.

### Requirement: Highlight Cancelation
The system SHALL provide an explicit action to remove persisted highlights for the current selected text.

#### Scenario: Canceling highlight for current selection
- **WHEN** user clicks `取消高亮` in the toolbar.
- **THEN** matching persisted highlight annotations are removed and current selection draft is cleared.

### Requirement: Toolbar Dismiss Behavior
The system SHALL allow dismissing the selection toolbar by clicking outside the reader selection context without deleting persisted highlights.

#### Scenario: Dismissing toolbar by outside click
- **WHEN** toolbar is open and user clicks outside toolbar and reader panel.
- **THEN** toolbar closes.
- **AND** previously persisted highlights remain.

### Requirement: AI Context Synchronization
The system SHALL populate the agent context with both the selected text and the user's note when "Ask AI" is triggered.

#### Scenario: Asking AI about selection
- **WHEN** user clicks "Ask AI".
- **THEN** the agent panel displays the selection and fills the input with the note.

### Requirement: Scroll-Stable Highlight Visibility
The system SHALL keep persisted highlights visually available after reader scrolling in both root and nested preview scroll containers unless user manually removes the highlight or leaves the task context.

#### Scenario: Highlight remains visible after nested preview scrolling
- **WHEN** user creates a highlight in translated preview mode and scrolls `paper-preview-viewport`.
- **THEN** highlight rendering is recomputed and remains visible for the highlighted content when revisiting that location.

