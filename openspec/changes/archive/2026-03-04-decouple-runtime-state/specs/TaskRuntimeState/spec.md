# TaskRuntimeState Specification

## Purpose
彻底将 Supabase 从 Runtime 执行路径中移除，保留细粒度、实时、稳定的前端进度条，明确区分 Runtime State 与 Persistent State，保证系统在并发提升时仍然稳定。

## ADDED Requirements

### Requirement: State Layer Separation
系统状态 MUST 拆分为两层：Runtime (TaskRuntimeState) 与 Persistent (Supabase)。
- **Runtime**: 高频、内存态、不可回放。
- **Persistent**: 低频、稳定、可回放。

#### Scenario: 任务执行期间的状态更新
- **WHEN** 任务处于 `parsing` 或 `translating` 等循环阶段
- **THEN** 系统 MUST 仅更新 `TaskRuntimeState`
- **AND** 禁止在循环中触发任何 Supabase 写入或 PATCH 请求
- **AND** RuntimeState 的更新必须为零网络操作（例如内存或本地 Redis）

### Requirement: Throttled Supabase Synchronization
系统 SHALL 限制对 Supabase 的写入频率，严格区分语义跃迁 (Semantic Transitions) 与数值变化 (Value Changes)，并使用异步队列确保线程安全。

#### Scenario: 状态跃迁触发立即入队
- **WHEN** 任务发生以下语义状态变更：`status` 或 `stage` 的 **实际数值发生改变**（不仅是字段碰巧被传递，而是相对于内存旧值有实质变化）
- **THEN** 系统 MUST 立即将当前快照推入持久化队列
- **AND** 后台 Dedicated Flusher 协程将消费队列并写入 Supabase

#### Scenario: 时间节流触发数值入队
- **WHEN** 任务状态仅有进度或数值改变（如 `progress`, `current_section`）
- **AND** 距离上次 flush 到 Supabase 的时间 `now - last_flush` 超过 `FLUSH_INTERVAL` （至少 5 秒）
- **THEN** 系统 SHALL 将当前快照推入持久化队列
- **AND** 重置 `last_flush` 时间
- **AND** 仅有进度改变时，系统 MUST NOT 立即写入数据库

#### Scenario: 线程安全的合并型 Dedicated Flusher
- **WHEN** 工作线程 (Worker Thread) 调用 `TaskManager.update_task`
- **THEN** 该方法 MUST NOT 直接由于异步上下文缺失而调用 `asyncio.create_task`
- **AND** 该方法 SHALL 仅将数据安全地放入一个内存 Dict，由生命周期与应用一致的专用线程基于 `threading.Event` 唤醒消费
- **AND** Flusher MUST 实现基于 `task_id` 的合并 (Coalescing，last-write-wins)，确保并发或风暴写入时能收敛为单次 Supabase 请求

#### Scenario: 异常与错误状态的持久化
- **WHEN** 任务发生异常或错误
- **THEN** 系统 MUST 优先更新 `TaskRuntimeState`
- **AND** 仅当 error 状态最终确定（无进一步 retry）或任务终止时，才执行 Supabase 写入

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
