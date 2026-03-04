# Design: LangGraph Agent Evolution

## Goals
- Migrating the monolithic translation coordinator to a `StateGraph`.
- Enabling structural diagnostics for complex compilation failures.
- Maintaining strict functional parity with the deterministic hardening baseline.

## Non-Goals
- Character-level regex fixing within LLM nodes.
- Infinite retry loops.
- Re-introduction of model-side structural responsibility.

## Decisions
- **Decision: Separate Orchestration from Legacy Coordinator**.
    - **Why**: Allows side-by-side verification and easy rollback.
- **Decision: State-First Architecture**.
    - **Why**: Ensures all data transformations are traceable and recoverable.

## Tasks: LangGraph Agent Evolution

### Phase 1: Functional Parity Migration
- [ ] Scaffold the `StateGraph` for the baseline translation lifecycle (Parse -> Translate -> Validate -> Compile).
- [ ] Establish strict state typing and wire existing methods into nodes without adding new LLM retry loops.
- [ ] Verify 1:1 functional parity on test documents (including CJK and `dummy_test`).

### Phase 2: Intelligent Diagnostics Expansion
- [ ] Implement the `CompilationDiagnosticNode` for high-level structure/package reasoning.
- [ ] Emit structured diagnostic payload including error type, location, repair path, and final compile status.
