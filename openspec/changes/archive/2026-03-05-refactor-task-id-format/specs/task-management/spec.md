# 任务管理与标识规范补丁 (task-management-id)

用于系统内新任务生命周期发起期间的特征保障，同时杜绝下游脚本引发的越界错误解析。

## ADDED Requirements

### Requirement: 复合任务标识生成规范
系统 MUST 生成具有全局信息穿透特征的复合任务标识 (task_id)。

- 禁止在业务网关或文件创建流使用裸字符串形式的 UUID (例如: `a1b2c3d4-xxxx-xxxx-xxxx-...`)。
- 必须基于当前请求上下文附加资源来源：`{arxiv_id_or_upload}-{MMDD}-{HHmm}-{full_UUID}`。
- 当有明确的 arXiv ID 支持时，确保 ID 能够无损包含其中（特殊字符如 `/` 转为 `_`）。
- 在所有配置落地场景（如 `task_configs`），直接采纳或以此 `task_id` 为主标识，切勿通过下标字符串截取尝试"组装或拼凑"命名。

#### Scenario: 用户上传了 ArXiv 论文进行翻译且系统触发任务创建抓取
- **WHEN** 任务属于 arxiv 来源且生成 task_id
- **THEN** 系统最终将快照直接落盘为带 task_id 全称的 json，不进行 [:6] 切割

#### Scenario: 后置离线同步脚本进行结果校验解析
- **WHEN** 脚本 sync_results.py 进行批次结果捞取
- **THEN** 脚本正确通过分隔符 `-` 提取 UUID，不发生前缀截断错误
