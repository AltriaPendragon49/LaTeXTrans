# user-settings Specification

## Purpose
TBD - created by archiving change add-multi-user-support. Update Purpose after archive.
## Requirements
### Requirement: User Settings Storage
系统 SHALL 在 Supabase Postgres 中存储用户设置。

#### Scenario: 首次访问设置
- **WHEN** 用户首次访问设置页面或 API
- **AND** 该用户在 `user_settings` 表中无记录
- **THEN** 系统自动创建默认设置记录
- **AND** 默认语言为 en → zh

#### Scenario: 获取用户设置
- **WHEN** 用户请求 `GET /api/settings`
- **THEN** 系统返回当前用户的设置数据

#### Scenario: 更新用户设置
- **WHEN** 用户请求 `PUT /api/settings` 携带新设置
- **THEN** 系统更新 Supabase 中的对应记录
- **AND** 返回更新后的设置

### Requirement: Settings Page UI
前端 SHALL 提供系统设置页面供用户管理偏好。

#### Scenario: 查看设置页面
- **WHEN** 用户访问 `/settings` 页面
- **THEN** 系统显示当前设置，包含：
  - 默认源语言
  - 默认目标语言
  - 功能开关（如验证模式、严格模式）

#### Scenario: 保存设置
- **WHEN** 用户修改设置并点击保存按钮
- **THEN** 系统调用 API 更新设置
- **AND** 显示成功/失败反馈

### Requirement: Settings Effect on Translation
系统 SHALL 使用用户设置作为翻译任务的默认值。

#### Scenario: 新建翻译任务时应用默认语言
- **WHEN** 用户新建翻译任务时未显式选择语言
- **THEN** 系统使用 `user_settings` 中的默认语言

#### Scenario: 功能开关生效
- **WHEN** 用户启用/禁用某功能开关
- **THEN** 后续翻译任务应用对应的功能配置

