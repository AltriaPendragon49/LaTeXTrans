# Change: Eliminate Silent Fallback

## Why
Current LangGraph orchestration lacks visibility into silent source pass-through events. Untranslated paragraphs appear in PDFs without diagnostic traces, making it difficult to debug or trust the automation closure.

## What Changes
- Implement FallbackReport diagnostic instrumentation.
- Route fallback segments into a targeted LangGraph repair sub-graph.
- Enforce strict retry budgets for repairs to guarantee convergence.
- **BREAKING**: Replaces previous strict single-attempt Phase 2 with budget-aware multi-attempt repair.
- Introduce deterministic Ultimate Downgrade Renderer as the absolute safety net.

## Impact
- Affected specs: ControlledRepairWorkflow
- Affected code: backend/pipeline_schema.py, backend/langgraph_orchestrator.py, backend/ultimate_downgrade.py
