## ADDED Requirements

### Requirement: Failed Output Quarantine
The system SHALL quarantine failed task outputs into `data/failed_tasks`, and SHALL move only `outputs/{task_id}` artifacts.  
The system SHALL NOT move `terms/{task_id}` and SHALL NOT move or delete upload cache artifacts as part of this quarantine behavior.

#### Scenario: Quarantine Failed Task Output
- **WHEN** task status is updated to `failed` or `failed_compilation`
- **THEN** the system moves `data/outputs/{task_id}` to `data/failed_tasks/{task_id}`
- **AND** the quarantined files remain available for debugging

#### Scenario: Avoid Overwriting Existing Quarantine Folder
- **WHEN** `data/failed_tasks/{task_id}` already exists
- **THEN** the system writes to a new timestamp-suffixed quarantine folder
- **AND** the system MUST NOT overwrite existing quarantined evidence

#### Scenario: Move Outputs Only
- **WHEN** failed-task quarantine runs
- **THEN** the system processes only `outputs/{task_id}`
- **AND** the system SHALL NOT move `terms/{task_id}`
- **AND** the system SHALL NOT move or delete `uploads` data

#### Scenario: Cancelled Task Skips Failed Quarantine
- **WHEN** a task is marked as cancelled and later reaches a failed terminal state
- **THEN** the system skips failed-output quarantine
- **AND** the original output directory remains unchanged by this feature

### Requirement: Runtime Task Config Snapshot Storage
The system SHALL persist runtime translation config snapshots under `data/task_configs` when config capture is enabled.  
The snapshot format SHALL remain compatible with config validator tooling and SHALL NOT persist raw API keys.

#### Scenario: Capture Task Config Snapshot
- **WHEN** translation initialization builds `advanced_config`, `agent_config`, and `llm_config`
- **AND** `ENABLE_TASK_CONFIG_CAPTURE` is enabled
- **THEN** the system writes a snapshot file to `data/task_configs/config_<task8>_<timestamp>.json`

#### Scenario: Disabled Config Capture
- **WHEN** `ENABLE_TASK_CONFIG_CAPTURE` is disabled
- **THEN** the system skips writing config snapshots
- **AND** translation continues normally

#### Scenario: Config Capture Write Failure
- **WHEN** config snapshot write fails due to filesystem/runtime error
- **THEN** the system logs a warning
- **AND** translation MUST continue without failing the task

#### Scenario: API Key Masking
- **WHEN** `llm_config` contains an API key
- **THEN** snapshot output stores masked key metadata only
- **AND** raw API key value SHALL NOT be persisted
