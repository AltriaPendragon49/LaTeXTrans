# Change: Update Community Curation Runtime Guards

## Why
Recent conversation-driven fixes changed the effective runtime contract for community curation and structured insights, but those decisions have not yet been captured in one active OpenSpec change. We also need to tighten failure cleanup and lower LLM concurrency defaults so failed admin curation runs do not leave partial artifacts behind and translation quality is not degraded by excessive parallelism.

## What Changes
- Persist the structured-insight read contract normalization that turns stored guide text into stable `raw_content`, `summary`, and `blocks` fields for the detail UI.
- Update admin curation so failed or timed-out runs stop automatically, surface a terminal failed state, and require admins to retry manually.
- Require failed admin curation to clean up partial database rows and local task artifacts while preserving the failed job record itself for operator visibility.
- Extend the admin curation task wait timeout to 15 minutes.
- Reduce backend `llm_max_concurrent_requests` defaults and task-level parity ceilings to `3`.

## Impact
- Affected specs:
  - `community-paper-intake-api`
  - `community-structured-insights`
  - `latex-translation-core`
  - `web-api`
- Affected code:
  - `backend/app/services/paper_service.py`
  - `backend/app/repositories/community_paper_repository.py`
  - `backend/app/services/task_manager.py`
  - `backend/app/core/config.py`
  - `backend/app/api/routes/translate.py`
  - `backend/.env.example`
  - related backend unit tests
