## MODIFIED Requirements

### Requirement: Translation Task Initiation
The system SHALL accept translation requests via REST API and process them asynchronously in the background.  
During translation initialization, the system SHALL attempt runtime config snapshot capture when enabled, and capture failure SHALL NOT fail the translation task.

#### Scenario: Start translation for uploaded file
- **WHEN** user sends `POST /translate/{task_id}` for a valid task with uploaded source files
- **THEN** the system updates task status to processing, triggers background translation, and returns HTTP 202

#### Scenario: Runtime Config Capture Enabled
- **WHEN** translation initialization has built effective runtime configuration
- **AND** `ENABLE_TASK_CONFIG_CAPTURE=true`
- **THEN** the system attempts to persist a config snapshot under `data/task_configs`

#### Scenario: Runtime Config Capture Failure Is Non-Blocking
- **WHEN** config snapshot capture fails due to module/path/write/runtime error
- **THEN** the system logs a warning
- **AND** translation initialization continues without raising task-fatal error from capture
