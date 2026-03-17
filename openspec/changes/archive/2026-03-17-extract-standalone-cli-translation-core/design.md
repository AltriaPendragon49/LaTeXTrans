# Design: Standalone CLI Translation Core Extraction

## Architecture

The standalone CLI is implemented inside `NiuTrans/LaTeXTrans` and adopts three layers:

1. **CLI surface**
   - `main.py`
   - `config/default.toml`
   - README and dependency manifest
2. **Extracted translation core**
   - `src/agents/*`
   - `src/formats/latex/*`
   - `src/translation/*`
3. **CLI runtime adapters**
   - `src/runtime/settings.py`
   - `src/runtime/clock.py`
   - `src/runtime/progress.py`
   - `src/runtime/concurrency.py`
   - `src/runtime/async_blocking.py`
   - `src/models/config_models.py`

## Key Decisions

### Preserve prototype-style public paths
`NiuTrans/LaTeXTrans/main.py` remains the primary user entrypoint. The old `src/agents/tool_agents/*` paths are kept as compatibility wrappers that re-export the new extracted agent implementations.

### Replace backend imports with local runtime imports
All `backend.app.*` imports in the extracted kernel are rewritten to point at local `src.*` modules. Web-only dependencies are removed entirely.

### Replace task-manager runtime writes with local logging
The backend orchestrator previously wrote compile runtime state back into `task_manager`. In the standalone CLI, these events are emitted to `task_log.json` and process logs instead.

### Keep current orchestration behavior
The standalone CLI uses the current `CoordinatorAgent -> langgraph_orchestrator` execution path, not the legacy prototype workflow. This retains current production safeguards such as:
- replay bundle generation
- targeted repair routing
- structure guard behavior
- target-language fallback
- compile diagnostics

## Trade-offs

- The standalone CLI keeps some backend-derived internal complexity because correctness and parity are prioritized over a minimal rewrite.
- Optional download helpers still accept task-manager-like callbacks for reuse, but callers are not required to provide them.
- The open-source CLI intentionally diverges from the old prototype in internal architecture while maintaining compatible user entrypoints.
