## MODIFIED Requirements
### Requirement: LaTeX Compilation with Intelligent Fallback
The system SHALL compile translated LaTeX files with intelligent multi-engine fallback and MUST produce explicit structured outcomes for success and compilation failure.

#### Scenario: Async compilation execution path
- **WHEN** orchestration enters compilation stage in single-worker runtime
- **THEN** the compiler path SHALL execute through a non-blocking async orchestration entry (event loop MUST remain schedulable)
- **AND** implementation MAY use direct async subprocess execution or thread-wrapped legacy fallback core
- **AND** it SHALL preserve existing status semantics (`completed`, `completed_with_warnings`, `failed_compilation`, `structure_invalid`).

#### Scenario: Async compiler feature toggle rollback
- **WHEN** `ASYNC_COMPILER_ENABLED=true`
- **THEN** intelligent fallback execution SHALL use native async stage execution with awaited subprocess-based compile calls.
- **WHEN** `ASYNC_COMPILER_ENABLED=false`
- **THEN** the system MAY route through legacy fallback implementation for emergency rollback without changing API contract.

#### Scenario: Compile semaphore boundary is compile-only
- **WHEN** single-worker runtime enforces `MAX_CONCURRENT_COMPILATIONS`
- **THEN** semaphore acquisition MUST wrap only the actual compile await region
- **AND** preprocessing/generation steps before compile (reconstruct, formatting, structure guard) MUST NOT be serialized by compile semaphore.

#### Scenario: Compile slot waiting is observable
- **WHEN** a task enters compile stage but compile slot is occupied
- **THEN** progress messaging SHALL expose waiting state distinct from active compilation
- **AND** runtime/audit metrics SHALL include queue-wait and compile-execution durations.

#### Scenario: Async path preserves legacy compile selection semantics
- **WHEN** async compilation fallback returns a warning-level successful PDF candidate
- **THEN** the selected `pdf_path` MUST follow legacy intelligent-fallback selection output (including engine/stage snapshot naming when applicable)
- **AND** the workflow MUST NOT downgrade to `failed_compilation` solely due to mismatch with a fixed basename expectation.

#### Scenario: Compilation timeout and cancellation teardown
- **WHEN** compile subprocess times out or pipeline cancellation is raised during compilation
- **THEN** the system MUST terminate the full subprocess tree/process-group
- **AND** MUST wait for subprocess cleanup before returning terminal state.

#### Scenario: Runtime compile metadata tracking
- **WHEN** a compile subprocess is created
- **THEN** runtime state SHALL store `compile_pid`, `compile_engine`, and `compile_started_at`
- **AND** these fields MUST be cleared in a guaranteed cleanup path after compile exit.
