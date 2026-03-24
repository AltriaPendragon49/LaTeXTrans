## MODIFIED Requirements

### Requirement: Community launcher and conversation workspace support external search toggle
The web UI SHALL let users explicitly enable external network search for paper-agent requests from the launcher and conversation composer without persisting that preference across sessions or conversations.

#### Scenario: Homepage launcher forwards toggle state
- **WHEN** a user submits the homepage launcher with external search enabled
- **THEN** the UI SHALL forward `seedSkillToggles.external_search=true` into the dedicated conversation route state.

#### Scenario: Conversation composer forwards toggle on each run
- **WHEN** a user submits a conversation turn
- **THEN** the UI SHALL include `skill_toggles.external_search` in the agent run payload
- **AND** the toggle state SHALL apply only to that explicit submission path rather than being restored from saved conversation history.

### Requirement: Community conversation UI supports slot-formatted background sections
The conversation UI SHALL render formatter-generated structured sections including a background explanation / answer section.

#### Scenario: Formatter emits background section
- **WHEN** the backend formatter returns a section labeled `Background / Answer` or `鑳屾櫙瑙ｉ噴/鍥炵瓟`
- **THEN** the conversation UI SHALL parse and render that section as part of the structured assistant response.

#### Scenario: Agent run remains visibly in progress
- **WHEN** a conversation turn is submitted and the agent run has not completed yet
- **THEN** the UI SHALL show a visible in-flight progress state without requiring the user to manually scroll to the bottom
- **AND** the workspace SHALL keep the newest pending or completed content in view so the run does not appear stuck.

### Requirement: Community conversation history is authenticated, persistent, and manageable
The web UI SHALL require sign-in before starting community-agent conversations, persist authenticated conversation history by user, and let the user delete saved conversations.

#### Scenario: Guest opens the agent workspace
- **WHEN** a signed-out visitor opens the conversation workspace or tries to submit an agent prompt
- **THEN** the UI SHALL block the run
- **AND** it SHALL present a sign-in affordance instead of silently saving guest-only local history.

#### Scenario: Signed-in user deletes a saved conversation
- **WHEN** an authenticated user deletes a saved conversation from the conversation list
- **THEN** the UI SHALL remove that conversation from the visible list
- **AND** it SHALL keep the persisted history store in sync so the deleted conversation does not reappear after reload.

### Requirement: Paper preview workspace preserves scholarly context and isolated scrolling
The web UI SHALL keep title/author metadata and figure references readable in the preview workspace and SHALL confine scroll behavior to the reading viewport on wide-screen reader layouts.

#### Scenario: Preview shows paper metadata and figures
- **WHEN** the paper detail workspace opens a preview-ready paper
- **THEN** the reading workspace SHALL render the paper title, author information, and figure/caption content as part of the preview reading experience
- **AND** broken figure references SHALL not degrade into a metadata-less reading view.

#### Scenario: Reader workspace owns the scroll container
- **WHEN** a user reads a long preview on the paper detail page
- **THEN** the scrollable region SHALL be the reader viewport itself
- **AND** the entire page SHALL not become the primary reading scroll container on the desktop split layout.
