## MODIFIED Requirements
### Requirement: Shared shell supports persistent day and dark themes
The frontend SHALL provide a shared theme preference for the application shell so users can switch between a bright daytime interface and the existing dark presentation. The color palette MUST use the "Lumina Blue" theme (primary #0037b0) instead of the legacy red-based theme to avoid an Apache-style look.

#### Scenario: Default shell keeps the current dark presentation
- **WHEN** a user opens the frontend without a previously saved theme preference
- **THEN** the shared shell SHALL render with the current dark visual system by default
- **AND** the default SHALL preserve the existing dark-first information hierarchy using Lumina Blue dark colors.

#### Scenario: User switches the shell theme
- **WHEN** a user activates the shared theme toggle from the shell header
- **THEN** the frontend SHALL switch between `dark` and `light` themes without a full page reload
- **AND** the toggle copy and icon treatment SHALL remain accessible in both modes.

#### Scenario: Theme preference persists across navigation
- **WHEN** a user selects either day or dark mode
- **THEN** the frontend SHALL persist that preference for later visits
- **AND** navigating between `/`, `/paper/:paperId`, `/translate`, and other shared-shell routes SHALL keep the selected theme active.

## ADDED Requirements
### Requirement: Reading Area Focused Text view
The reading area of a paper detail view SHALL only display the textual content to maximize focus. Document metadata (title, author, interactions) MUST be separated into a distinct header layout according to the refined header hierarchy.

#### Scenario: User views a paper
- **WHEN** the paper detail page loads
- **THEN** the left pane SHALL only render the main body text
- **AND** the title, author details, and action buttons SHALL exist separate from the scrolling text.

### Requirement: Reading Area Highlight to Agent Action 
Users SHALL be able to select text in the reading area, highlight it, and send it to the agent via a context menu option.

#### Scenario: User highlights and asks a question
- **WHEN** a user selects text in the reading area and right-clicks
- **THEN** a context menu option displaying "对这些内容提问" appears
- **AND** clicking the option highlights the text in yellow and populates the right-side Agent context.

### Requirement: Agent Panel Default Suggestions
The Agent panel SHALL display default read-only suggestion prompts when empty.

#### Scenario: User opens a new paper chat
- **WHEN** the right Agent panel is empty
- **THEN** it SHALL display uneditable suggestion hints: "不知道如何提问？你可以尝试：1.总结这篇论文 2.勾画后询问“仔细解释这段” 3.这一篇论文的核心是什么？"

### Requirement: Document Feed Dual Thumbnails
The community document feed (homepage) SHALL render document cards emphasizing dual visual preview of documents.

#### Scenario: Rendering document cards
- **WHEN** the community feed loads document items
- **THEN** each item SHALL display side-by-side thumbnails showing the original PDF on the left and the translated PDF on the right.

#### Scenario: First page fits within thumbnail frame
- **WHEN** a card renders either original or translated PDF preview
- **THEN** the first page SHALL be scaled to fit inside the thumbnail frame while preserving aspect ratio
- **AND** the preview SHALL avoid clipping key page content at top or bottom.

### Requirement: Source preview prefers local cache before remote fetch
Source preview requests used by community feed cards SHALL prefer existing local source PDF assets in the community paper library before falling back to remote arXiv proxy retrieval.

#### Scenario: Cached source PDF exists for selected task
- **WHEN** a source preview request is made for a task that already has a matching local source PDF under `community_papers/<paper_id>/source/`
- **THEN** the backend SHALL return the local PDF directly
- **AND** the request SHALL NOT trigger a remote arXiv fetch for that preview.

#### Scenario: Remote fallback remains available when local source is missing
- **WHEN** no suitable local source PDF is found for the task
- **THEN** the backend SHALL proxy arXiv source PDF content
- **AND** Range requests SHALL be forwarded so clients can load source previews progressively.

### Requirement: UI Icon Rendering
The frontend SHALL correctly render Material Symbols icons in the community feed. This REQUIRES the `Material Symbols Outlined` font library to be loaded in the application shell.

#### Scenario: Visual icons render in feed
- **WHEN** a user views a document card or navigation bar
- **THEN** icons like `local_fire_department`, `schedule`, and `filter_list` SHALL render as graphical symbols
- **AND** NO raw icon character strings SHALL be visible to the user.

### Requirement: Abstract Language Toggle Label
The abstract translation toggle button SHALL use a clear label that identifies its role as a language switcher rather than an active translation trigger.

#### Scenario: User sees language toggle button
- **WHEN** a document card renders an available translated abstract
- **THEN** the toggle button SHALL display the label "切换语言(switch)"
- **AND** the label SHALL remain consistent regardless of whether the current view is showing the English or Chinese abstract.
