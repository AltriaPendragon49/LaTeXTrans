## ADDED Requirements
### Requirement: Minimum moderation loop
The system SHALL let admins review reports, apply minimum moderation actions, and ensure hidden content no longer remains visible to normal community users.

#### Scenario: Review the report queue
- **WHEN** an admin opens the moderation console
- **THEN** the system SHALL return a report queue with enough status and target metadata to decide on an action
- **AND** the queue SHALL support the minimum filtering needed for MVP handling.

#### Scenario: Resolve a report with a minimum action set
- **WHEN** an admin resolves a report
- **THEN** the system SHALL support ignoring the report, hiding a comment, hiding a paper, or recording a user-ban placeholder
- **AND** the resolution SHALL update both report state and moderation action history.

#### Scenario: Remove hidden content from user-facing surfaces
- **WHEN** a moderation action hides a paper or comment
- **THEN** the affected content SHALL stop appearing on normal community read surfaces
- **AND** the system SHALL preserve enough backend state to audit why the content disappeared.
