# web-api Specification Delta

## ADDED Requirements

### Requirement: Server-Sent Events for Task Status

The system SHALL provide real-time task status updates via SSE (Server-Sent Events).

> **SSE** is an HTML5 standard technology that allows the server to push data to the client without the client repeatedly initiating requests. Compared to polling, SSE reduces latency from up to 2 seconds to under 100ms, eliminates redundant HTTP requests, and provides smoother user experience.

#### Scenario: SSE connection establishment
- **WHEN** client sends `GET /api/task/{task_id}/stream`
- **THEN** the system returns `Content-Type: text/event-stream` response
- **AND** immediately sends current task status as first event

#### Scenario: SSE progress updates
- **WHEN** task status, progress, or message changes
- **THEN** the system pushes an event within 500ms
- **AND** event data contains full task status JSON

#### Scenario: SSE connection termination
- **WHEN** task reaches terminal status (completed, failed, completed_with_warnings, failed_compilation)
- **THEN** the system sends final status event
- **AND** closes the SSE connection gracefully

#### Scenario: SSE heartbeat
- **WHEN** task is in progress but no status change occurs
- **THEN** the system sends a heartbeat comment (`: heartbeat`) every 15 seconds
- **AND** keeps connection alive

## MODIFIED Requirements

### Requirement: Task Status Tracking

任务状态 API SHALL 返回完整任务信息，包括高级配置。

#### Scenario: Query task status during processing
- **WHEN** user sends `GET /task/{task_id}` while translation is in progress
- **THEN** the system returns JSON with `{status: "processing", progress: <0-100>, stage: <current_stage>, message: <description>, advanced_config: <config>}`

#### Scenario: Query completed task status (perfect compilation)
- **WHEN** user sends `GET /task/{task_id}` for a successfully completed translation with zero compilation errors
- **THEN** the system returns `{status: "completed", progress: 100, stage: "done", output_path: <path_to_pdf>, advanced_config: <config>}`

#### Scenario: Polling fallback (NEW)
- **WHEN** client cannot establish SSE connection (browser compatibility, proxy issues)
- **THEN** classic `GET /api/task/{task_id}` polling remains available
- **AND** polling interval recommendation is 2 seconds
