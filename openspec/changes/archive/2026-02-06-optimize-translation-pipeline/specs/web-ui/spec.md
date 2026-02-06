# web-ui Specification Delta

## ADDED Requirements

### Requirement: Session Continuity for Temporary Users

The system SHALL allow temporary users to create multiple translation tasks without page refresh.

#### Scenario: New translation after completion
- **WHEN** user clicks "New Translation" button after task completion
- **THEN** frontend resets all task-related state (taskId, status, progress)
- **AND** closes any active SSE connection
- **AND** returns to initial file upload view

#### Scenario: New translation after failure
- **WHEN** user clicks "New Translation" button after task failure
- **THEN** frontend performs same state reset as completion scenario
- **AND** user can immediately start new upload/arXiv download

### Requirement: SSE-based Status Subscription

The system SHALL use Server-Sent Events for real-time status updates.

#### Scenario: SSE connection for task monitoring
- **WHEN** user starts a translation task
- **THEN** frontend establishes SSE connection to `/api/task/{task_id}/stream`
- **AND** updates UI immediately upon receiving events

#### Scenario: SSE fallback to polling
- **WHEN** SSE connection fails or is not supported
- **THEN** frontend falls back to `setInterval` polling at 2-second intervals
- **AND** user experience remains consistent

