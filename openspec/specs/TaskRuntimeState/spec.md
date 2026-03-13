# TaskRuntimeState Specification

## Purpose
TBD - created by archiving change decouple-runtime-state. Update Purpose after archive.
## Requirements
### Requirement: State Layer Separation
系统状态 MUST 拆分为 Runtime (TaskRuntimeState) 与 Persistent (Supabase)。

#### Scenario: Compile runtime metadata remains in runtime layer
- **WHEN** compilation starts or ends
- **THEN** `compile_pid`, `compile_engine`, `compile_started_at` MUST be updated only in runtime memory state
- **AND** MUST NOT be persisted to Supabase terminal history fields.

### Requirement: Throttled Supabase Synchronization
系统 SHALL 限制 Supabase 写入频率并保持 async 路径非阻塞。

#### Scenario: Async DB wrapper strategy mode
- **WHEN** async route/service path issues DB SDK calls
- **THEN** execution SHALL use wrapper policy driven by `DB_EXECUTION_MODE`
- **AND** default mode SHALL be `per_call_client` for safer threaded execution.

### Requirement: API Read Strategy
`/api/task/{task_id}` 查询接口 MUST 优先读取 Runtime 状态，以防止对 Supabase 形成高频轮询压力。

#### Scenario: 前端轮询任务进度
- **WHEN** 前端或客户端请求 `/api/task/{task_id}`
- **THEN** 后端优先检查 `runtime_state_cache` 是否包含该 `task_id`
- **AND** 如果命中，则直接返回 Runtime 状态
- **AND** 如果未命中，才进行 `supabase_fallback(task_id)` 查询

#### Scenario: 拒绝将 Supabase 作为实时数据源
- **WHEN** 前端建立 WebSocket 或 SSE 连接以获取实时状态
- **THEN** SSE 只能推送 `TaskRuntimeState` 的更新
- **AND** 绝不允许直接推送 Supabase 的变更事件作为实时数据源

### Requirement: Task State Recovery
System MUST remember user preferences even when tasks are recovered from the database after a restart.

#### Scenario: Recover Task from Database Retains Email Preference
- **WHEN** the backend restarts and recovers an active task from Supabase `translation_tasks`
- **THEN** it MUST correctly deserialize the `email_notification` boolean flag 
- **AND** store it in the in-memory `advanced_config` dictionary so terminal email notifications successfully send.

### Requirement: Task Status Synchronization
Final task statuses MUST flush immediately.

#### Scenario: Suppressed Flusher Race Condition on Terminal State
- **WHEN** a task reaches a terminal state (`completed`, `failed`)
- **AND** `update_task` enqueues the final status to the `SupabaseFlusher`
- **THEN** it MUST immediately dispatch the write to Supabase (semantic transition), bypassing the interval throttle
- **AND** if an error occurs within `update_task` post-enqueue (such as an email notification timeout), it SHALL NOT prevent the enqueued status from being written to the database.

### Requirement: Single-Worker Runtime Safety Guardrail
Until runtime task state is fully externalized, production runtime MUST operate with a single worker.

#### Scenario: Startup warning about multi-worker risk
- **WHEN** backend starts
- **THEN** logs MUST state that runtime state is partially in-process
- **AND** logs MUST state that multi-worker deployment is unsupported in current model

#### Scenario: Deployment defaults align with guardrail
- **WHEN** production runtime command is used
- **THEN** default worker count MUST be `1`

