## MODIFIED Requirements
### Requirement: State-Machine Orchestration and Agent Scope
The system SHALL orchestrate parsing, translation, validation, and compilation exclusively through a LangGraph StateMachine, and any outer scheduler SHALL treat one paper run as an indivisible orchestration kernel rather than splitting LangGraph nodes across independent workers.

#### Scenario: LangGraph Agent Guardrails
- **WHEN** the agent handles orchestration across paragraphs, package conflicts, or layout logic
- **THEN** it operates within scope
- **AND** the system MUST PREVENT the agent from executing character-level syntax fixes or entering infinite retry cycles.

#### Scenario: Single-paper kernel remains intact under scheduler scaling
- **WHEN** the system adds queue priority, yielding, or token-pool scheduling
- **THEN** those controls MUST operate outside the LangGraph paper workflow
- **AND** the change MUST NOT distribute nodes from the same paper across multiple independent workers or queues.

#### Scenario: Cooperative yield occurs only at safe checkpoints
- **WHEN** the scheduler requests capacity from a running backfill task
- **THEN** the orchestrator MAY yield only after a completed checkpoint such as parse completion, section-batch flush, validation-round completion, pre-compile boundary, or post-compile boundary
- **AND** MUST persist enough checkpoint metadata to resume from that boundary
- **AND** MUST NOT yield mid-LLM request or mid-compile subprocess.

#### Scenario: Phase 4b Intelligent Diagnostic Activation
- **WHEN** compilation fails and the pipeline enters the finalization stage
- **THEN** the system MUST activate the `CompilationDiagnosticNode` by default (unless `use_compilation_diagnostics` is explicitly disabled)
- **AND** the node MUST remain isolated from the source LaTeX files.

## ADDED Requirements
### Requirement: Non-Critical Post-Success Artifacts Do Not Block Translation Completion
The orchestration layer SHALL allow terminology-table generation and successful-compilation diagnostic enrichment to run as resumable sidecar work behind feature flags, while keeping failure-path diagnostics in the synchronous correctness path.

#### Scenario: Successful translation defers optional artifacts
- **WHEN** a task has already produced a durable translated output
- **AND** deferred post-success artifacts are enabled for that task class
- **THEN** the task MAY release its main translation slot before terminology-table generation or success-only diagnostic enrichment finishes
- **AND** the deferred artifact work MUST be resumable and idempotent.

#### Scenario: Failure-path diagnostics remain synchronous
- **WHEN** compilation fails or warnings require immediate failure analysis
- **THEN** the failure-path diagnostic workflow MUST stay in the synchronous orchestration path
- **AND** moving success-only artifacts out of band MUST NOT remove actionable failure reports.

#### Scenario: Feature flag rollback restores legacy inline postprocessing
- **WHEN** deferred post-success artifacts are disabled
- **THEN** the system MUST execute the legacy inline artifact flow
- **AND** task outputs MUST remain behaviorally compatible with current semantics.
