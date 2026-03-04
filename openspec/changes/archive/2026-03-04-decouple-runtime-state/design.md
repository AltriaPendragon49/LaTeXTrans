# Architecture Design: Task Runtime State Decoupling

## Context & Problem
The LaTeX translation pipeline updates progress continuously during the `parsing` and `translating` phases. Historically, these updates were written synchronously to Supabase on every progress tick. 
Since the worker processing loops run extremely fast, this results in:
- A "PATCH storm" to Supabase (e.g., every 0.3-0.5 seconds).
- Network ACK bottlenecks slowing down the workers, essentially turning Supabase into an "execution metronome".
- Instability and failure risk amplification during error paths, where rapid retries cascade into rapid DB writes.

## Proposed Architecture

We propose a strict two-layer state architecture:
1. **TaskRuntimeState (In-Memory)**: High-frequency, volatile execution state.
2. **Persistent State (Supabase)**: Low-frequency, stable truth state.

### 1. The TaskRuntimeState Layer
The backend already leverages a `TaskManager` singleton with an in-process dictionary (`self._tasks`) protected by a `threading.Lock`. 
**Decision**: We will formalize `TaskManager._tasks` as the sole `TaskRuntimeState`. 
- **Why**: It requires zero network I/O, is thread-safe, and avoids adding external dependencies like Redis for a single-node deployment.
- **Rules**: Workers (e.g., `AstParser`, `AgentTranslator`) MUST exclusively update `TaskManager` during execution. They are forbidden from directly constructing Supabase queries for progress updates.

### 2. The Persistent State Layer (Supabase Sync)
Supabase will only be updated under strict conditions. We MUST clearly distinguish between "semantic transitions" and "value changes":
- **Semantic Transitions (Immediate Flush)**: When `status` or `stage` **values actually change** compared to the current in-memory state (e.g., `CREATED` → `parsing_started`, `processing` → `completed`), the state is immediately queued to be flushed.
- **Value Changes (Time-Based Throttling)**: When only numerical/progress fields change (e.g., `progress`, `current_section`), or when semantic fields are updated with the *same* value, we rely on a `last_flush` timestamp. Supabase will only be written to if `now() - last_flush > FLUSH_INTERVAL` (e.g., 5-10 seconds). Progress changes alone MUST NOT trigger an immediate flush.

**Implementation of the Flush (Dedicated Coalescing Flusher)**:
Workers operate in separate threads and may not have a running event loop. Therefore, we will NOT use `asyncio.create_task` directly within `update_task`.
Instead, we implemented a **Dedicated Flusher Thread** (`SupabaseFlusher`) that consumes flush requests using a Threading Lock, an Event, and a Dictionary.
When `TaskManager.update_task` determines a flush is needed, it merges the update into the flusher's `_pending` dict and sets the wake-up Event. 
This provides **field-level coalescing (last-write-wins)**: if the database is slow, rapid updates to the same `task_id` are merged in memory, ensuring the thread only performs 1 network request for the most recent state, cleanly absorbing "PATCH storms" and retry avalanches.

### 3. API Read Priority
The frontend polling endpoint (`/api/task/{task_id}`) should retrieve data primarily from `TaskManager.get_task()`. 
- **Current State**: `TaskManager.get_task()` already checks the in-memory dictionary before falling back to Supabase.
- **Enforcement**: We must ensure no endpoints bypass this logic. The frontend will maintain its smooth, high-resolution progress bar because the in-memory state is updated instantly, while the database is spared the load.

## Alternatives Considered
- **Redis for TaskRuntimeState**: Redis could provide distributed runtime state if multiple backend instances were deployed. However, the current architecture runs `TaskQueue` and `asyncio.create_task` in a single master process. Introducing Redis adds infrastructure overhead without immediate benefit. If multi-node scaling is required later, `TaskManager` can cleanly abstract a Redis implementation.
- **WebSockets / SSE for Frontend**: Instead of polling, we could stream `TaskRuntimeState` to the frontend. However, to minimize scope and ensure stability, we will maintain the existing polling mechanism but satisfy it exclusively via the fast in-memory cache.

## Security & Failure Handling
- **Crash Recovery**: If the node crashes, the `TaskRuntimeState` is lost. However, this is acceptable because a crashed pipeline task must be restarted anyway. The last flushed milestone in Supabase accurately denotes where the pipeline terminated.
- **Error States**: When a terminating error occurs, the system will execute one final, guaranteed flush to Supabase to ensure the frontend and historical logs accurately reflect the failure.
