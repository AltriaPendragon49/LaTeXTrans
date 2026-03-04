# Change: fix-404-polling-and-recovery

## Why
When a task is deleted or purged, the frontend's SSE polling sequence falls back to HTTP polling and loops continuously on 404 responses, creating console noise and unnecessary server hits. In addition, when the backend `TaskManager` attempts to recover a task from the filesystem (because Supabase is absent), it currently throws an `'Settings' object has no attribute 'OUTPUT_DIR'` exception, preventing graceful recovery. Furthermore, API rate limiting configurations for LLM calls need refinement by utilizing the `global_llm_semaphore` properly.

## What Changes
- Address frontend SSE fallback 404 polling loop:
  - In `frontend/src/hooks/use-task-status-sse.ts`, catch 404 responses during the HTTP polling fallback sequence.
  - If 404 is received, immediately stop polling by calling `cleanup()` and marking the task as deleted.
- Fix backend task recovery missing attribute:
  - Update `backend/app/services/task_manager.py` to use `settings.outputs_dir` and `settings.uploads_dir`.
- Refine background API concurrency:
  - Modify `backend/app/services/agents/translator_agent.py` to properly import and utilize `global_llm_semaphore` to restrict system-wide API calls where appropriate.

## Impact
- Affected specs:
  - `web-api`
- Affected code:
  - `frontend/src/hooks/use-task-status-sse.ts`
  - `backend/app/services/task_manager.py`
  - `backend/app/services/agents/translator_agent.py`
- Behavioral outcomes:
  - The frontend stops requesting task status immediately when a 404 is returned.
  - Backend task recovery for missing tasks pulls cleanly from the filesystem instead of crashing.
  - LLM Rate Limit bounds globally applied correctly.
