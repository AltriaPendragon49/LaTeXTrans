## MODIFIED Requirements
### Requirement: State-Machine Orchestration and Agent Scope
The system SHALL orchestrate parsing, translation, validation, and compilation exclusively through a LangGraph StateMachine.

#### Scenario: LangGraph Agent Guardrails
- **WHEN** the agent handles orchestration across paragraphs, package conflicts, or layout logic
- **THEN** it operates within scope
- **AND** the system MUST PREVENT the agent from executing character-level syntax fixes or entering infinite retry cycles.

#### Scenario: Phase 4b Intelligent Diagnostic Activation
- **WHEN** compilation fails and the pipeline enters the finalization stage
- **THEN** the system MUST activate the `CompilationDiagnosticNode` by default (unless `use_compilation_diagnostics` is explicitly disabled)
- **AND** the node MUST remain isolated from the source LaTeX files.

### Requirement: Structured Diagnostic Output
The diagnostic node SHALL emit formalized failure reports post-compilation to aid system maintainers and downstream consumers.

#### Scenario: Emitting the Diagnostic Payload
- **WHEN** a compilation failure limits out or reaches an unrecoverable state
- **THEN** the Agent MUST generate a `DiagnosticReport` Pydantic object
- **AND** the report MUST include: `task_id`, `error_count`, `root_cause_category`, `suggestions` (predefined action whitelist), `confidence`, and `is_actionable` flag.

## REMOVED Requirements
### Requirement: Phase4 Deferred Status
**Reason**: Phase 4b (Intelligent Diagnostics) has been successfully implemented and promoted to the system baseline.
**Migration**: Requirements for Phase 4b are now incorporated directly into the active `translation-orchestration` specifications.
