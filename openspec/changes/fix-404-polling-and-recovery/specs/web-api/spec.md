# Spec: Web API

## MODIFIED Requirements

### Requirement: Server-Sent Events for Task Status

The system SHALL provide real-time task status updates via SSE (Server-Sent Events).

> **SSE** is an HTML5 standard technology that allows the server to push data to the client without the client repeatedly initiating requests. Compared to polling, SSE reduces latency from up to 2 seconds to under 100ms, eliminates redundant HTTP requests, and provides smoother user experience.

#### Scenario: Polling fallback and task deletion (NEW)
- **WHEN** client cannot establish SSE connection and relies on `GET /api/task/{task_id}` polling fallback
- **AND** the requested task returns HTTP 404 (due to deletion)
- **THEN** the frontend gracefully terminates the polling loop instead of retrying infinitely.

## ADDED Requirements

### Requirement: Persisted Task Recovery

The task manager MUST recover task configurations from the local file system.

#### Scenario: Task missing from Supabase DB
- **WHEN** a task is not in Supabase
- **THEN** the backend searches the local file system using the system's valid `outputs_dir` and `uploads_dir` settings
- **AND** it retrieves metadata gracefully without raising internal setting attribute exceptions.
