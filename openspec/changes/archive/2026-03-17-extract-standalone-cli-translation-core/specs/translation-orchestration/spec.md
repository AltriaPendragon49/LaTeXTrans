# translation-orchestration Specification Deltas

## ADDED Requirements

### Requirement: Standalone Orchestration Runtime Independence
The translation orchestrator SHALL be runnable in a standalone CLI environment without FastAPI lifecycle hooks, task queues, or task-manager persistence.

#### Scenario: Running the orchestrator in standalone CLI mode
- **WHEN** the standalone CLI invokes `CoordinatorAgent.workflow_latextrans`
- **THEN** the orchestrator MUST run without importing FastAPI, Supabase, or `task_manager`
- **AND** progress reporting MUST flow through CLI logging or progress callbacks
- **AND** compile-runtime observability MUST be written to local task logs rather than backend runtime state stores.
