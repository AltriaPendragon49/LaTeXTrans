## ADDED Requirements
### Requirement: Conversation agent requests use conversation-scoped paper context only
The conversation UI SHALL derive `paper_id` context only from the active conversation thread and SHALL NOT leak paper identifiers from other saved conversations.

#### Scenario: Active conversation carries a known paper thread
- **WHEN** the active conversation already contains assistant metadata (action/citation) with a valid `paper_id`
- **THEN** the next run request SHALL include that `paper_id`
- **AND** the request SHALL keep using the current conversation id/history as the scope boundary.

#### Scenario: Other conversation records have different paper ids
- **WHEN** the user has multiple saved conversations and inactive conversations contain different `paper_id` values
- **THEN** the next run request for the active conversation SHALL ignore those inactive conversation paper ids
- **AND** only the active conversation context may influence the outgoing `paper_id`.

#### Scenario: Active conversation has no paper context yet
- **WHEN** the active conversation has no assistant action/citation carrying `paper_id`
- **THEN** the UI SHALL omit `paper_id` from the outgoing run request
- **AND** backend runtime bridging logic may resolve paper context independently.
