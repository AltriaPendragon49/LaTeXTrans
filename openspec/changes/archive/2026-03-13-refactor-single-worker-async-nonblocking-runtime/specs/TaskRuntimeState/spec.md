## MODIFIED Requirements
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
