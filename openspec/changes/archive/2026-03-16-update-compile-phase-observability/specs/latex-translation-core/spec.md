## ADDED Requirements

### Requirement: Compile Queue Waiting Status Reflects Real Semaphore Contention
The system SHALL surface compile queue waiting status only when the shared compilation semaphore cannot be acquired immediately after precompile checks complete.

#### Scenario: Immediate compile path skips queue waiting status
- **WHEN** the compile-ready `main.tex` has been resolved successfully
- **AND** precompile structure validation has completed successfully
- **AND** the shared compile semaphore has immediate capacity
- **THEN** the runtime MUST transition directly to active compilation status
- **AND** it MUST NOT emit `Waiting for compile slot` or any equivalent queue-wait message.

#### Scenario: Queue waiting status begins at the semaphore boundary
- **WHEN** the compile-ready `main.tex` has been resolved successfully
- **AND** precompile structure validation has completed successfully
- **AND** the shared compile semaphore is exhausted
- **THEN** the runtime MUST emit `Waiting for compile slot` immediately before awaiting semaphore acquisition
- **AND** once the semaphore is acquired, the runtime MUST switch to active compilation status without re-running precompile checks.
