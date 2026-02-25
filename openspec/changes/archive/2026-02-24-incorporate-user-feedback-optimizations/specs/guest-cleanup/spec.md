## MODIFIED Requirements

### Requirement: Periodic Guest Cleanup
系统 SHALL 在后台定时执行 Guest 任务清理，并确保在服务重启或任务异常时具备鲁棒性。

#### Scenario: 定时清理正常执行
- **GIVEN** 系统启动时注册定时清理任务
- **WHEN** 清理间隔到达（默认 30 分钟）
- **THEN** 系统扫描所有已注册的 Guest 任务
- **AND** 删除超过 TTL 的任务文件

#### Scenario: 服务重启后无状态清理
- **WHEN** 服务重启后内存追踪器清空
- **THEN** 清理任务 MUST 基于文件系统时间戳识别 output 目录
- **AND** 比对数据库记录，若目录 ID 不存在于数据库中，则执行强制物理删除

#### Scenario: 物理删除已从数据库移除的任务
- **WHEN** 用户或系统删除了数据库中的任务条目，但 output 目录仍留在磁盘
- **THEN** 定时清理任务 MUST 能够识别这种不一致性并清理孤立目录
