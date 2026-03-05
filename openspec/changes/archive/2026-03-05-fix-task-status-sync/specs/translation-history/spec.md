# Capability: translation-history

## ADDED Requirements

### Requirement: Non-Terminal Task Status Reconciliation
The system MUST reconcile the status of tasks that are in a non-terminal state (`pending`, `processing`, `queued`) during history retrieval to prevent users from seeing "Stuck" tasks due to server crashes.

#### Scenario: Reconcile Status from Local Log
- **WHEN** a user requests their task history (`GET /history`)
- **AND** a task in the database is in a non-terminal state
- **AND** a local `task_log.json` exists for that task and contains terminal events (e.g., `compilation_completed`)
- **THEN** the API response MUST return the inferred terminal status and 100% progress
- **AND** the system SHOULD asynchronously update the Supabase database to match this corrected state.

### Requirement: Frontend Terminal Failure Display
The frontend MUST correctly distinguish and display various terminal failure states without defaulting to generic error messages.

#### Scenario: Display Structure Invalid Badge
- **WHEN** a task has a status of `structure_invalid`
- **THEN** the History UI MUST display a specific "Structure Invalid" (或 "结构无效") badge
- **AND** clicking the task SHOULD navigate the user to the processing page to see the detailed error log.
