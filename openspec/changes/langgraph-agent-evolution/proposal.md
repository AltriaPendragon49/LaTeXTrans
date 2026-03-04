# Change: LangGraph Agent Evolution

## Why
After hardening the deterministic translation pipeline (Phase 1-3), the orchestration logic remains complex and monolithic. Adopting LangGraph allows for granular cross-step orchestration, better handling of package conflicts through a diagnostic loop, and structured reporting. This move converts the pipeline from a linear script into a robust state-driven graph.

## What Changes
- **Phase 1: Functional Parity Migration (Phase 4a equivalent)**:
    - Scaffold the `StateGraph` for the baseline translation lifecycle (Parse -> Translate -> Validate -> Compile).
    - Establish strict state typing and wire existing methods into nodes without adding new LLM retry loops.
    - Verify 1:1 functional parity on test documents (CJK and `dummy_test`).
- **Phase 2: Intelligent Diagnostics (Phase 4b equivalent)**:
    - Implement the `CompilationDiagnosticNode` for high-level structure/package reasoning (no character-level fixing).
    - Emit structured diagnostic payload including error type, location, repair path, and final compile status.

## Impact
- Affected specs: `langgraph-orchestration`.
- Affected code:
  - `backend/app/services/agents/langgraph_orchestrator.py` [NEW]
  - `backend/app/services/agents/coordinator_agent.py` [UPDATE]
