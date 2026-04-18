## ADDED Requirements
### Requirement: Structured insight supports task-local base preference without global base bans
The system-managed token-pool layer SHALL allow structured insight generation to prefer a healthier `base_url` within the current task while keeping global health tracking strictly member-level.

#### Scenario: One relay base accumulates repeated 503 during one structured-insight task
- **WHEN** structured insight generation records three cumulative HTTP 503 responses from members sharing the same `base_url` during the current task
- **AND** another `base_url` in the same applicable pool still has a healthy member
- **THEN** later member selection for that structured-insight task SHALL prefer the healthier base
- **AND** the system SHALL NOT globally mark the failing base unavailable for unrelated tasks
- **AND** healthy members on that base MAY still be used by other requests according to normal member-level health rules.

### Requirement: Member-level 503 handling uses bounded cooldown with current-member exhaustion retry
The system-managed token-pool layer SHALL cool down individual members after repeated HTTP 503 responses without forcing blind rotation when every member is temporarily unavailable.

#### Scenario: One member hits repeated 503
- **WHEN** the same endpoint-credential member receives consecutive HTTP 503 responses
- **THEN** the system SHALL place that member into a bounded cooldown longer than the current one-second behavior
- **AND** that cooldown SHALL apply to that member only.

#### Scenario: All members are unavailable after 503 pressure
- **WHEN** every eligible member in the applicable pool is cooling down or unavailable
- **THEN** the current request SHALL keep retrying its current member on a short bounded interval
- **AND** it SHALL NOT rotate blindly across equally unavailable members.
