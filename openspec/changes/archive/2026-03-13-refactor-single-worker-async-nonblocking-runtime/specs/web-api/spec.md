## MODIFIED Requirements
### Requirement: Translation Progress Reporting
The system SHALL report granular progress updates during translation workflow stages, with optimized database I/O for download operations.

#### Scenario: Async route DB calls do not pin event loop
- **WHEN** async API routes perform Supabase operations
- **THEN** blocking SDK calls SHALL execute through async-safe wrapper offload
- **AND** event-loop responsiveness for `/health` and task status polling SHALL remain stable during compile load.

#### Scenario: Behavior-level event-loop health gate
- **WHEN** parser/validator phases run with simulated blocking work
- **THEN** automated tests SHALL verify scheduler/tick latency stays under configured threshold
- **AND** concurrent task wall time SHALL indicate non-serialized behavior.
