# Decouple Task Runtime State from Supabase

## 1. Abstract
The translation pipeline currently relies on Supabase as a high-frequency runtime state store, resulting in severe performance bottlenecks, excessive network I/O, and instability during concurrent execution. This proposal introduces a strict architectural separation between `TaskRuntimeState` (high-frequency, memory-based) and `Persistent State` (Supabase, low-frequency), removing Supabase from the critical execution path of the text processing loop to ensure stable performance and reliable progress tracking.

## 2. Problem Statement
- **High-Frequency Writes**: The `parsing` and `translating` loops issue PATCH requests to Supabase roughly every 0.3–0.5 seconds to update progress.
- **Polling Loop Feedback**: Frontend polling combined with continuous backend writes form a positive feedback loop that taxes the network and database.
- **Execution Bottleneck**: Workers become bound by network ACK times to Supabase. Supabase acts as an unintended "execution metronome".
- **Error Amplification**: Retry, error, and warning paths continue to write to Supabase at high frequency, escalating failure risks during instability.

## 3. Proposed Solution
Implement a strict two-layer state architecture:
1. **TaskRuntimeState (Runtime)**: Replace direct database writes in the worker loop with an in-memory or high-speed runtime state tracker (e.g., Redis or local memory cache, depending on worker distribution). The worker updates this state with zero network overhead.
2. **Supabase (Persistent)**: Supabase will only be written to at clearly defined stage transitions (`parsing_started`, `parsing_done`, `translating_started`, `translating_done`, `completed`, `failed`) and through a throttled progress flush (e.g., ≥ 5s interval or event-driven).
3. **API Read Priority**: The `/api/task/{task_id}` read endpoint must prioritize reading from the `TaskRuntimeState` cache, falling back to Supabase only if the runtime state is unavailable.

## 4. Scope
- **Backend API**: Refactor `/api/task/` endpoints to read from the runtime state cache.
- **Worker Logic**: Replace all synchronous/high-frequency Supabase writes in the processing loop with `TaskRuntimeState` updates.
- **State Synchronization**: Introduce a robust, throttled synchronization mechanism (e.g., a background task or flush on interval) to persist the `TaskRuntimeState` to Supabase cleanly.
- **Frontend**: Ensuring the frontend polling retrieves the high-resolution state via the updated endpoint, maintaining smooth progress bars without directly hitting Supabase for live updates.

## 5. Exclusions
- Changing the frontend UI rendering logic for the progress bar (it expects the same JSON structure).
- Altering the LLM translation mechanisms or PDF compilation strategies.
