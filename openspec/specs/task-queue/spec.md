# task-queue Specification

## Purpose
定义翻译任务队列的并发管理、用户配额限制以及任务执行健壮性规范，确保系统在高并发场景下按序有序地处理翻译请求。
## Requirements
### Requirement: Translation Task Queue
The system SHALL manage translation tasks with priority-aware FIFO lanes on a single-machine scheduler, limiting total active translation slots while allowing backfill work to borrow idle interactive capacity.

#### Scenario: Interactive task admission
- **WHEN** a user submits an interactive translation request
- **THEN** the system enqueues that task into the interactive lane
- **AND** the task remains eligible ahead of waiting backfill work.

#### Scenario: Backfill task admission
- **WHEN** the system submits an internal backfill translation
- **THEN** the system enqueues that task into the backfill lane
- **AND** backfill ordering remains FIFO within the backfill lane.

#### Scenario: Idle capacity is borrowed by backfill
- **WHEN** no interactive task is waiting
- **AND** a translation slot would otherwise remain idle
- **THEN** the scheduler MAY start a backfill task in that slot.

#### Scenario: Recent frontend traffic defers new backfill starts
- **WHEN** the worker runtime has observed recent frontend pressure from the web runtime
- **AND** only backfill tasks are waiting for admission
- **THEN** the scheduler MUST defer starting a new backfill task until the pressure window expires or new capacity becomes explicitly available to backfill
- **AND** this deferral MUST NOT block already-waiting interactive work.

#### Scenario: Interactive work claims the next eligible slot
- **WHEN** at least one backfill task is running
- **AND** a new interactive task arrives while all translation slots are occupied
- **THEN** the scheduler MUST reserve the next eligible slot for the interactive task
- **AND** MUST NOT abruptly terminate an in-flight backfill LLM call or compile subprocess
- **AND** interactive priority is satisfied as soon as a slot becomes available.

#### Scenario: Task completion releases resources
- **WHEN** a running task completes or fails
- **THEN** the scheduler releases the active slot
- **AND** the highest-priority waiting task that is eligible to run starts next.

### Requirement: Per-User Task Quota
系统 SHALL 限制每个登录用户同时拥有的活跃任务数（排队中 + 执行中）。Guest 用户不适用此限制。

#### Scenario: 登录用户配额内提交任务
- **WHEN** 登录用户提交翻译请求
- **AND** 用户当前活跃任务数 < MAX_USER_ACTIVE_TASKS（默认 9）
- **THEN** 任务正常入队

#### Scenario: 登录用户配额已满
- **WHEN** 登录用户提交翻译请求（单个或批量）
- **AND** 用户当前活跃任务数 >= MAX_USER_ACTIVE_TASKS
- **THEN** 系统返回 HTTP 429 Too Many Requests
- **AND** 提示用户等待现有任务完成后再提交

#### Scenario: Guest 用户不受配额限制
- **WHEN** Guest 用户提交单论文翻译请求
- **THEN** 系统正常入队，不检查配额

### Requirement: Queue Status API
The system SHALL expose lane-aware queue status without breaking existing aggregate queue-status consumers.

#### Scenario: Query queue status
- **WHEN** a client requests `GET /api/queue/status`
- **THEN** the response MUST still include aggregate active, waiting, and max-concurrency values
- **AND** MAY additionally include `interactive_active`, `interactive_waiting`, `backfill_active`, `backfill_waiting`, and `borrowed_slots`
- **AND** authenticated callers continue to receive current quota usage.

### Requirement: Concurrent Translation Limit Configuration
系统 SHALL 允许通过配置项控制最大并发翻译数和登录用户配额。

#### Scenario: 配置并发上限
- **GIVEN** 环境变量 `MAX_CONCURRENT_TRANSLATIONS` 设为 N
- **WHEN** 系统启动
- **THEN** 任务队列的 semaphore 上限为 N
- **AND** 默认值为 3

#### Scenario: 配置用户配额
- **GIVEN** 环境变量 `MAX_USER_ACTIVE_TASKS` 设为 M
- **WHEN** 系统启动
- **THEN** 每登录用户活跃任务上限为 M
- **AND** 默认值为 9

### Requirement: Multi-Task Non-Interference
系统 SHALL 确保同一登录用户的多个翻译任务互不干扰。

#### Scenario: 翻译进行中新建任务
- **WHEN** 登录用户在任务 A 翻译进行中提交新任务 B
- **THEN** 任务 A 继续正常执行
- **AND** 任务 B 加入队列等待或开始执行
- **AND** 两个任务均可在历史记录中查看

### Requirement: Task Execution Robustness
任务 worker SHALL 在执行翻译前验证输入资源的有效性，并具备基础的故障自愈能力。

#### Scenario: 任务启动前的源文件校验
- **WHEN** worker 从队列中领取并准备执行任务
- **THEN** 系统 MUST 调用校验逻辑确保源目录非空且包含必要的 `.tex` 文件
- **AND** 避免因前序下载流程中途中断（竞态条件）导致的编译失败

#### Scenario: 持久化源路径异常的自动恢复
- **WHEN** worker 发现已记录的 `source_path` 丢失
- **AND** 任务具备可恢复性（如 arXiv 任务）
- **THEN** worker SHALL 尝试自动重建环境（如重新下载）而非直接报错

### Requirement: Task terminal state remains monotonic within one execution attempt
The system SHALL prevent same-attempt stale updates from regressing a task from terminal back to non-terminal state.

#### Scenario: Late progress callback arrives after completion
- **WHEN** a translation attempt has already written a terminal task state
- **AND** a delayed progress or message update from that same attempt arrives later
- **THEN** the system MUST ignore the stale non-terminal regression
- **AND** MUST keep the existing terminal `status` and `completed_at`.

#### Scenario: Fresh retry starts a new execution attempt
- **WHEN** the scheduler or operator intentionally retries a previously terminal task
- **THEN** the system MUST create a fresh execution attempt boundary before accepting new non-terminal progress updates
- **AND** MAY clear stale terminal markers only for that fresh attempt.

### Requirement: Impossible persistent task states are reconciled before they can block operators
The system SHALL treat contradictory durable task rows as recoverable failures instead of leaving them non-terminal.

#### Scenario: Persistent row has completed timestamp but non-terminal status
- **WHEN** durable task state shows a non-terminal `status`
- **AND** `completed_at` is already populated
- **THEN** the system MUST reconcile that task into an explicit terminal failure state
- **AND** MUST record a recovery-oriented message instead of leaving the task indefinitely active.

#### Scenario: Admin curation waits across memory loss or runtime split
- **WHEN** admin curation waits for a translation task to reach terminal state
- **AND** the in-memory task snapshot is missing or stale
- **THEN** the wait path MUST fall back to durable `translation_tasks` state
- **AND** MUST NOT remain blocked forever on an already-terminal or already-reconciled task.

