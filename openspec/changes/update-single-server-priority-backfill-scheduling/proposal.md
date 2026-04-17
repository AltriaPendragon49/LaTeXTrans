# Change: Update Single-Server Priority Backfill Scheduling

## Why
- The current single-process backend does not distinguish strongly enough between interactive user requests and long-running bulk backfill work on the only available backend server.
- The immediate operational need is to ingest thousands of papers quickly, while long-term public translation traffic is expected to remain modest. We need a single-server design that shortens ingestion time without weakening translation quality, compile safety, or LangGraph orchestration semantics.

## What Changes
- Introduce a single-machine dual-lane scheduler with `interactive` high priority and `backfill` opportunistic capacity borrowing.
- Add cooperative backfill yield/resume behavior that pauses only at safe checkpoints and resumes from the last durable position.
- Add a health-aware token pool with short request-local retries, quick failover to other healthy tokens, and explicit all-token-exhausted behavior.
- Keep one-paper LangGraph orchestration intact; do not split graph nodes for the same paper across multiple workers in this change.
- Allow non-critical post-success artifacts such as terminology-table generation and successful-compilation diagnostics to move behind resumable sidecar execution under feature flags.
- Preserve the existing validation, repair, compile, and target-language fallback guardrails.

## Impact
- Affected specs: `task-queue`, `queue-token-isolation`, `translation-orchestration`, `latex-translation-core`
- Affected code: `backend/app/services/task_manager.py`, `backend/app/services/agents/langgraph_orchestrator.py`, `backend/app/services/agents/generator_agent.py`, `backend/app/services/agents/translator_agent.py`, `backend/app/services/translation/repair_scheduler.py`, `backend/app/main.py`
