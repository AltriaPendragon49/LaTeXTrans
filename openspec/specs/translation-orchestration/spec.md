# translation-orchestration Specification

## Purpose
Define the current production orchestration contract for LaTeXTrans backend translation tasks.
Production translation uses a single backend-owned `origin_cli_parity` kernel wrapped by a thin LangGraph pipeline. Historical modern-kernel enhancement branches such as controlled repair, hard-freeze orchestration, post-compile target-language fallback, residual-English fallback, compilation diagnostic nodes, and ultimate downgrade are not part of current production orchestration.

## Requirements
### Requirement: Origin CLI Parity Graph
The backend SHALL orchestrate production translation tasks through a thin LangGraph wrapper around the legacy linear parity workflow.

#### Scenario: Production graph shape
- **WHEN** the backend builds the production translation graph
- **THEN** the graph MUST contain only parse, translate, validate-and-retry, generate, and finalize stages
- **AND** it MUST NOT add controlled repair, structure repair, hard-freeze routing, post-compile fallback, residual-English fallback, ultimate downgrade, or diagnostic nodes.

#### Scenario: Single kernel selection is recorded
- **WHEN** an `origin_cli_parity` task starts
- **THEN** orchestration MUST record an `origin_cli_parity_kernel_selected` audit event
- **AND** the event MUST indicate single-kernel lineage.

### Requirement: Legacy Validation Retry Loop
The orchestration layer SHALL preserve the legacy parity validate-and-retry loop without adding backend-only recovery branches.

#### Scenario: Validation errors retry through translator
- **WHEN** validation reports errors for a non-quick-scan task
- **THEN** orchestration MAY rerun translator error handling up to the configured parity retry limit
- **AND** it MUST revalidate after each retry.

#### Scenario: No-progress retries short-circuit
- **WHEN** repeated validation retries produce the same remaining error signature
- **THEN** orchestration MUST stop retrying after the configured no-progress threshold
- **AND** it MUST record `validation_retry_short_circuited_no_progress` in `task_log.json`.

#### Scenario: Quick scan does not repair
- **WHEN** translation mode is quick scan
- **THEN** orchestration MUST skip error repair/retranslation
- **AND** it MAY log validation warnings without mutating translated content.

### Requirement: Generation And Finalization Contract
The generation stage SHALL reconstruct translated LaTeX and compile it through the origin CLI parity compiler result contract.

#### Scenario: Successful PDF is finalized
- **WHEN** generation returns an existing compiled PDF path
- **THEN** finalize MUST move it to the expected translated output PDF path
- **AND** return `completed` or `completed_with_warnings` according to compiler warnings.

#### Scenario: Missing or failed PDF becomes failed compilation
- **WHEN** generation returns no PDF path or a path that does not exist
- **THEN** finalize MUST return `failed_compilation`
- **AND** it MUST persist a `compilation_failed` task-log entry with the error summary.

### Requirement: Runtime Observability
The orchestration layer SHALL persist task-start, stage, validation, generation, and finalization events needed for production replay and debugging.

#### Scenario: Task-start log masks secrets
- **WHEN** a task starts
- **THEN** `task_log.json` MUST include the effective runtime configuration
- **AND** raw API keys MUST NOT be persisted.

#### Scenario: Stage failures are auditable
- **WHEN** any stage raises an exception
- **THEN** orchestration MUST record a `stage_failed` task-log entry
- **AND** include the stage, error type, error message, and traceback digest.

### Requirement: Pipeline Timeout Boundary
The orchestration layer SHALL enforce a task-level pipeline timeout when configured.

#### Scenario: Timeout is recorded
- **WHEN** the LangGraph invocation exceeds the configured timeout
- **THEN** orchestration MUST record a `pipeline_timeout` audit event
- **AND** propagate the timeout to the caller for normal task failure handling.
