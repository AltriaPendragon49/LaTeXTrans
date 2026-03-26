## MODIFIED Requirements
### Requirement: Community conversation UI renders natural assistant chat output
The community conversation workspace SHALL render assistant runs as normal chat messages instead of reconstructing hard-coded summary cards from structured section headings, and it SHALL preserve that chat-bubble shape during live streaming.

#### Scenario: Assistant turn contains a natural-language reply
- **WHEN** the conversation page renders an assistant turn produced by the community agent
- **THEN** it SHALL display the run’s conversational message as the assistant content body
- **AND** it SHALL NOT require section headers such as “Conclusion/Current status” or “Core points” to render that turn.

#### Scenario: Citations, tool trace, and paper actions remain visible
- **WHEN** an assistant run includes citations, tool trace entries, or a paper navigation action
- **THEN** the conversation workspace SHALL continue to render those affordances alongside the conversational answer
- **AND** the UI SHALL keep the assistant answer in chat form rather than decomposing it into summary cards.

#### Scenario: Streaming answer keeps the same chat-body presentation
- **WHEN** the assistant answer is still arriving over the live stream
- **THEN** the UI SHALL keep rendering the partial answer inside the normal assistant chat bubble
- **AND** it SHALL NOT fall back to synthetic running summary cards.

## ADDED Requirements
### Requirement: Community conversation UI renders authenticated live streaming output
The community conversation workspace SHALL consume the authenticated live agent stream and incrementally render assistant output as the run progresses.

#### Scenario: Running assistant turn is updated incrementally
- **WHEN** the user submits a prompt in the conversation workspace
- **THEN** the UI SHALL create a running assistant turn immediately
- **AND** it SHALL append streamed text chunks into that turn without waiting for full completion.

### Requirement: Tool, citation, and action metadata hydrate during the stream
The community conversation workspace SHALL incrementally hydrate tool lifecycle, citations, and paper actions while the assistant answer is still streaming.

#### Scenario: Stream emits tool and citation events
- **WHEN** the runtime emits tool lifecycle, citation, or action events
- **THEN** the UI SHALL update the visible assistant turn metadata incrementally
- **AND** it SHALL preserve those artifacts in the final saved turn.

### Requirement: Background translation status stays inline with the answer
The community conversation workspace SHALL present translation startup as inline assistant metadata instead of replacing the answer body with a terminal placeholder.

#### Scenario: Translation is started during the answer
- **WHEN** the stream includes a translation handoff event or action
- **THEN** the UI SHALL surface it as inline assistant status or progress metadata
- **AND** it SHALL NOT replace the answer body with a terminal “translation started” placeholder.

### Requirement: Workspace sidebar is collapsed by default with an inline trigger
The application workspace SHALL set the sidebar to a collapsed state by default to maximize initial reading and conversation space, and the `SidebarTrigger` SHALL be located within the sidebar header instead of the global top navigation bar.

#### Scenario: User opens the workspace
- **WHEN** the user navigates to the community paper conversation or detail page
- **THEN** the sidebar SHALL be collapsed by default (`defaultOpen={false}`)
- **AND** the open/close trigger SHALL be visible at the top of the collapsed/expanded sidebar.

### Requirement: Inline paper reader provides maximized vertical space
The inline paper reader in the conversation workspace SHALL provide sufficient vertical space to ensure comfortable reading of complex HTML papers while allowing the overall page to remain scrollable.

#### Scenario: Reader panel height
- **WHEN** the community paper workspace renders the inline HTML reader
- **THEN** its height SHALL be optimized (e.g., `h-[calc(140dvh-160px)]`) to be larger than a single viewport, encouraging immersive reading without breaking overall page layout.
