## ADDED Requirements
### Requirement: Guest Output TTL Tracking
系统 SHALL 跟踪 Guest 用户任务的生命周期，在过期后自动清理输出文件。

#### Scenario: Guest 任务创建时注册 TTL
- **WHEN** Guest 用户（无 user_id）创建翻译任务
- **THEN** 系统在内存中记录该 task_id 和过期时间（created_at + TTL）
- **AND** TTL 默认值为 2 小时（可通过 GUEST_TASK_TTL_HOURS 配置）

#### Scenario: TTL 内 Guest 用户在当前页面正常访问
- **WHEN** Guest 用户在 TTL 窗口内且未离开翻译页面
- **AND** 请求预览 PDF 或下载文件
- **THEN** 系统正常返回文件内容

#### Scenario: Guest 用户离开页面后不可重访
- **WHEN** Guest 用户离开翻译结果页面
- **THEN** 前端不保留 task_id 引用
- **AND** 用户无法通过历史记录或 URL 重新访问该任务

#### Scenario: TTL 过期后自动清理
- **WHEN** 定时清理任务运行
- **AND** 发现 Guest 任务已超过 TTL
- **THEN** 系统删除 `data/outputs/{task_id}/` 和 `data/terms/{task_id}/`
- **AND** 从内存中移除该任务记录

### Requirement: Periodic Guest Cleanup
系统 SHALL 在后台定时执行 Guest 任务清理。

#### Scenario: 定时清理正常执行
- **GIVEN** 系统启动时注册定时清理任务
- **WHEN** 清理间隔到达（默认 30 分钟）
- **THEN** 系统扫描所有已注册的 Guest 任务
- **AND** 删除超过 TTL 的任务文件

#### Scenario: 服务重启后的降级清理
- **WHEN** 服务重启后 Guest TTL 信息丢失
- **THEN** 系统基于文件系统时间戳识别超过 TTL 的 output 目录
- **AND** 比对 Supabase 记录，清理未关联到任何记录的过期 output

### Requirement: Guest Feature Restriction Prompt
前端 SHALL 在 Guest 用户尝试使用受限功能时提示登录。

#### Scenario: Guest 尝试使用批量翻译
- **WHEN** Guest 用户点击批量翻译入口
- **THEN** 前端显示"请登录以使用批量翻译"提示
- **AND** 提供登录按钮

#### Scenario: Guest 翻译结果页面提示
- **WHEN** Guest 用户在翻译完成后查看结果
- **THEN** 前端提示"登录以保存翻译结果到历史记录"
- **AND** 提示"离开此页面后将无法重新访问"

### Requirement: Authenticated Task Cleanup on Persist Failure
系统 SHALL 在认证用户任务持久化全部失败时，将其纳入 Guest 清理机制，防止文件泄漏。

#### Scenario: 持久化失败的认证用户任务注册进 GuestTaskTracker
- **WHEN** `persist_task_with_retry()` 对某认证用户任务的所有重试均失败
- **THEN** 系统调用 `guest_tracker.register(task_id)` 将该任务纳入 TTL 追踪
- **AND** TTL 与 Guest 任务相同（默认 2 小时）

#### Scenario: 持久化失败任务被定时清理
- **WHEN** 定时清理任务（每 30 分钟）运行
- **AND** 发现已注册的持久化失败任务超过 TTL
- **THEN** 系统删除 `data/outputs/{task_id}/` 和 `data/terms/{task_id}/`
- **AND** 从内存中移除该任务记录
