# Change: Update Single-Server Priority Backfill Scheduling

## Why
- The current single-process backend does not distinguish strongly enough between interactive user requests and long-running bulk backfill work on the only available backend server.
- The immediate operational need is to ingest thousands of papers quickly, while long-term public translation traffic is expected to remain modest. We need a single-server design that shortens ingestion time without weakening translation quality, compile safety, or LangGraph orchestration semantics.

## What Changes
- Introduce a single-machine dual-lane scheduler with `interactive` high priority and `backfill` opportunistic capacity borrowing.
- Add a health-aware system token pool with two configured `base_url` groups and five independent system-managed credentials, plus quick failover on consecutive `429` or `503` failures.
- Split single-server runtime responsibility into `web` and `worker` roles so admin backfill/delete execution can live outside the user-facing HTTP process.
- Add a lightweight frontend-pressure signal so the worker defers starting new backfill work while recent browser/API traffic is active.
- Change the community feed API and UI from whole-list fetches to paginated incremental loading, with first-page caching for the public latest feed.
- Prewarm homepage PDF thumbnail cache entries when papers become publicly readable so the first homepage render does not pay thumbnail generation cost.
- Keep one-paper LangGraph orchestration intact; do not split graph nodes for the same paper across multiple workers in this change.
- Preserve the existing validation, repair, compile, and target-language fallback guardrails.

## Impact
- Affected specs: `task-queue`, `queue-token-isolation`, `translation-orchestration`, `latex-translation-core`, `deployment-infra`, `web-api`, `web-ui`, `community-public-read-experience`
- Affected code: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/services/runtime_pressure.py`, `backend/app/services/task_manager.py`, `backend/app/services/paper_service.py`, `backend/app/services/paper_thumbnail_service.py`, `backend/app/repositories/community_paper_repository.py`, `backend/app/api/routes/papers.py`, `frontend/src/hooks/use-community-papers.ts`, `frontend/src/lib/community-api.ts`, `frontend/src/pages/CommunityFeed.tsx`
