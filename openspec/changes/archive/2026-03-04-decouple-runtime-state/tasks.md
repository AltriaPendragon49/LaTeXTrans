# Task Runtime State Decoupling Tasks

This document outlines the ordered work items to implement the `TaskRuntimeState` decoupling architecture.

## Phase 1: Throttled State Synchronization (Backend)
- [x] 1.1 **Add State Flush Tracking**: Modify `TaskManager` (in `app/services/task_manager.py`) to track `_last_flush_time` per `task_id`.
- [x] 1.2 **Refactor Flush Triggers (Strict Field Separation)**: Update `update_task` to strictly differentiate field changes:
  - **Semantic Transitions**: If `status` or `stage` **values actually change compared to memory**, enqueue an immediate flush.
  - **Value Changes**: If only `progress` or `current_section` changes (or same status+stage is sent repeatedly), ONLY enqueue if `now - _last_flush_time > FLUSH_INTERVAL` (e.g., 5.0s).
- [x] 1.3 **Implement Dedicated Flusher**: Create a `SupabaseFlusher` class with a background daemon thread. It uses a `dict` + `threading.Event` to achieve **field-level coalescing (last-write-wins)**, merging rapid updates into a single DB write to handle retry/error storms.

## Phase 2: Worker Loop Optimization & Global Audit
- [x] 2.1 **Audit and Remove All Direct Supabase Client Calls**: Audited codebase. No direct progress-path Supabase writes found bypassing `TaskManager`. All `translate.py` Supabase calls are either read-only or intentional one-time writes (config_hash).
- [x] 2.2 **Error/Retry/Warning Path Safety**: Confirmed all exception handlers and retry blocks write through `TaskManager.update_task`, which now routes via the throttled flusher queue.

## Phase 3: API & Frontend Verification
- [x] 3.1 **Audit `/api/task/{task_id}` GET endpoint**: Confirm that the API endpoint strictly calls `task_manager.get_task()`, which already prioritizes the `_tasks` in-memory dictionary. Ensure it does not redundantly query Supabase when the memory state is active.
- [x] 3.2 **SSE/WebSocket Readiness (Optional)**: If Server-Sent Events are used for progress, verify they stream directly from the in-memory `TaskManager` rather than Supabase subscriptions.
- [x] 3.3 **Validate Frontend Behavior**: Start the frontend and backend locally with multiple concurrent tasks. Verify that the UI progress bar update frequency remains high (via the `/api/task/` endpoint) while checking the backend logs to confirm Supabase PATCH requests have dropped by >90%.

## Phase 4: Testing & Stability
- [x] 4.1 **Local Patch Storm Test (Unit)**: TDD unit tests validate that rapid progress updates within `FLUSH_INTERVAL` produce ≤1 Supabase flush. 14 new tests added and passing, including strict value-change detection.
- [x] 4.2 **Concurrency Test**: Submit 3-5 concurrent tasks and verify that workers proceed smoothly without bottlenecking on database ACKs.
- [x] 4.3 **Coalescing Test**: Verify that multiple rapid enqueue calls for the same task while the flusher is blocked merge into a single network write.
