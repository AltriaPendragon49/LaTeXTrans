## ADDED Requirements
### Requirement: Minimal notifications and report entry
The system SHALL provide a simple notifications list and a user-facing report submission path before the moderation console is introduced.

#### Scenario: Show a minimal notifications list
- **WHEN** a user opens the notification entry surface
- **THEN** the system SHALL return a basic list of in-site notifications relevant to that user
- **AND** the MVP SHALL not require real-time push delivery to satisfy this requirement.

#### Scenario: Submit a report from a community surface
- **WHEN** a user reports a paper or comment
- **THEN** the system SHALL accept the report through a dedicated report submission path
- **AND** it SHALL persist the reported target type, target identifier, reporter, and reason needed for moderation follow-up.

#### Scenario: Write eligible events to notifications
- **WHEN** an MVP interaction or moderation event qualifies for user feedback
- **THEN** the system SHALL be able to write a corresponding notification record
- **AND** the write model SHALL remain simple enough to coexist with non-real-time delivery.
