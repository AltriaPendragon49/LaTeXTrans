## ADDED Requirements
### Requirement: Production COS deployments keep local asset residue bounded
Production COS deployments SHALL have an operator-verified cleanup/audit path so local runtime cache residue does not grow into durable-asset storage again.

#### Scenario: Cleanup audit runs after COS deployment
- **WHEN** production runs with `STORAGE_BACKEND_MODE=cos`
- **THEN** operators SHALL be able to run a cleanup audit that reports local residue under COS-managed upload, output, community paper, failed-task, and temp storage roots
- **AND** the audit SHALL include counts, sizes, ages, skipped paths, and errors.

#### Scenario: Destructive cleanup follows verification
- **WHEN** a cleanup execute run is enabled in production
- **THEN** it SHALL use the same guarded candidate rules as dry-run
- **AND** production verification SHALL confirm public asset routes still work after cleanup.
