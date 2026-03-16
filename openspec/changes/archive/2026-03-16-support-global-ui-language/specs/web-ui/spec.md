# web-ui Specification Delta

## ADDED Requirements

### Requirement: User-visible static UI copy uses centralized i18n resources
All non-diagnostic user-visible frontend copy MUST come from centralized i18n resources instead of hardcoded strings.

#### Scenario: Main pages render localized UI copy
- **WHEN** the user visits Dashboard, Settings, History, Processing, Preview, Login, or Profile
- **THEN** titles, buttons, descriptions, empty states, Toast copy, and accessibility text MUST be resolved from locale resources
- **AND** changing the active UI language MUST update those strings consistently

### Requirement: Task progress UI is driven by structured task metadata
Frontend task progress and status views MUST use structured task metadata instead of parsing backend natural-language messages.

#### Scenario: Processing and batch views render task status
- **WHEN** the frontend receives task updates
- **THEN** Processing and batch translation views MUST derive visible status text from structured fields such as `status`, `stage`, `detail_code`, `detail_params`, and `failure_reason_code`
- **AND** the UI MUST NOT depend on `message.includes(...)` or equivalent natural-language parsing for primary task state rendering
