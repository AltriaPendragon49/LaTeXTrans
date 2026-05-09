## ADDED Requirements
### Requirement: COS-mode local residue cleanup is guarded and auditable
The system SHALL provide a dry-run-first cleanup path for local runtime residue created while durable artifacts are stored in COS.

#### Scenario: Cleanup dry-run reports candidates
- **WHEN** an operator runs the cleanup task without execute mode
- **AND** `STORAGE_BACKEND_MODE=cos`
- **THEN** the task SHALL report stale local candidates under approved runtime cache roots
- **AND** it SHALL NOT delete any files or directories.

#### Scenario: Cleanup execute deletes only guarded stale residue
- **WHEN** an operator runs cleanup with execute mode
- **AND** a candidate is under an approved root and older than the configured age threshold
- **THEN** the task SHALL delete that candidate
- **AND** it SHALL record the deletion in a machine-readable report.

#### Scenario: Cleanup refuses unsafe paths or modes
- **WHEN** cleanup is run outside COS mode or is pointed at a path outside approved backend data roots
- **THEN** the task SHALL refuse destructive cleanup
- **AND** it SHALL report the refusal instead of deleting data.
