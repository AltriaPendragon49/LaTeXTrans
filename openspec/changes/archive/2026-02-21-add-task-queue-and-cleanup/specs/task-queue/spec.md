## ADDED Requirements
### Requirement: Translation Task Queue
系统 SHALL 使用 FIFO 任务队列管理翻译任务的执行，限制最大并发翻译数。

#### Scenario: 任务入队
- **WHEN** 用户通过 `POST /translate/{task_id}` 启动翻译
- **THEN** 系统将翻译任务加入队列
- **AND** 返回 `status: "queued"` 给前端
- **AND** 任务状态设为 `queued`

#### Scenario: 并发上限内直接执行
- **WHEN** 翻译任务入队
- **AND** 当前活跃翻译数 < MAX_CONCURRENT_TRANSLATIONS（默认 3）
- **THEN** 任务立即开始执行

#### Scenario: 并发上限已满排队等待
- **WHEN** 翻译任务入队
- **AND** 当前活跃翻译数 >= MAX_CONCURRENT_TRANSLATIONS
- **THEN** 任务在队列中等待
- **AND** 任务状态显示为 `queued`

#### Scenario: 任务完成释放资源
- **WHEN** 某翻译任务完成或失败
- **THEN** 活跃计数 -1
- **AND** 登录用户的配额计数 -1
- **AND** 队列中下一个等待任务自动开始执行

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
系统 SHALL 提供队列状态查询接口。

#### Scenario: 查询队列状态
- **WHEN** 客户端请求 `GET /api/queue/status`
- **THEN** 系统返回当前活跃任务数、队列等待数、最大并发数
- **AND** 若已登录，返回当前用户已用配额

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
