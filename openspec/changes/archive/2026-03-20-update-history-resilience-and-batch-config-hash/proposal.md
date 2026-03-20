# Why
- Returning from a historical task view can leave the history page stuck on a long-lived "failed to load history" state after a single transient auth/session or backend fetch failure.
- Authenticated batch-created tasks can complete with a `NULL` `config_hash`, which prevents later equivalent requests from hitting output reuse.
- These issues are intermittent in production and need regression coverage because they affect user trust and cross-task reuse efficiency.

## What Changes
- Make history retrieval resilient to transient authenticated fetch failures when the user revisits `/history`, including backend-side safe threaded execution for authenticated Supabase history queries and frontend-side retry behavior.
- Ensure authenticated batch-created tasks persist `config_hash` as part of task persistence so output reuse remains available even when initial persistence falls back to retry.
- Add targeted backend and frontend regression tests before implementation and keep them passing after the fix.

## Impact
- Affects `backend/app/api/routes/history.py`, `backend/app/core/auth.py`, `backend/app/api/routes/translate.py`, `backend/app/services/task_manager.py`, and `frontend/src/pages/History.tsx`.
- Modifies existing capabilities in `translation-history` and `batch-translation`.
- Adds no breaking API surface changes.
