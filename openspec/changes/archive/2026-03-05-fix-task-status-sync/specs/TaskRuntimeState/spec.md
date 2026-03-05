# Capability: TaskRuntimeState

## ADDED Requirements

### Requirement: Task State Recovery
System MUST remember user preferences even when tasks are recovered from the database after a restart.

#### Scenario: Recover Task from Database Retains Email Preference
- **WHEN** the backend restarts and recovers an active task from Supabase `translation_tasks`
- **THEN** it MUST correctly deserialize the `email_notification` boolean flag 
- **AND** store it in the in-memory `advanced_config` dictionary so terminal email notifications successfully send.

### Requirement: Task Status Synchronization
Final task statuses MUST flush immediately.

#### Scenario: Suppressed Flusher Race Condition on Terminal State
- **WHEN** a task reaches a terminal state (`completed`, `failed`)
- **AND** `update_task` enqueues the final status to the `SupabaseFlusher`
- **THEN** it MUST immediately dispatch the write to Supabase (semantic transition), bypassing the interval throttle
- **AND** if an error occurs within `update_task` post-enqueue (such as an email notification timeout), it SHALL NOT prevent the enqueued status from being written to the database.
