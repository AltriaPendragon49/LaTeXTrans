## MODIFIED Requirements

### Requirement: Settings Page UI

前端 SHALL 提供受登录保护的系统设置页面供用户管理偏好，并将其纳入新的工作区路由体系。

#### Scenario: 查看设置页面
- **WHEN** 已登录用户访问工作区设置页面
- **THEN** 系统显示当前设置，包含：
  - 默认源语言
  - 默认目标语言
  - 功能开关（术语表生成、作者 API 模式）
- **AND** 该页面的规范目标路由 SHALL 为 `/workspace/settings`

#### Scenario: 未登录用户访问设置页面
- **WHEN** 未登录用户尝试访问设置页面
- **THEN** 前端 SHALL 阻止匿名访问
- **AND** 系统 SHALL 引导用户进入本地登录流程

#### Scenario: 旧设置入口兼容迁移
- **WHEN** 用户通过旧设置入口访问历史 URL
- **THEN** 前端 MAY 将其重定向到新的工作区设置路由
- **AND** 设置能力本身 SHALL 保持不变
