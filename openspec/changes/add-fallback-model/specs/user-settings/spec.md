# user-settings Specification Deltas

## MODIFIED Requirements

### Requirement: User Settings Storage
系统 SHALL 在 Supabase Postgres 中存储用户设置，包括默认排版配置和默认 Fallback 模型。

#### Scenario: 首次访问设置
- **WHEN** 用户首次访问设置页面或 API
- **AND** 该用户在 `user_settings` 表中无记录
- **THEN** 系统自动创建默认设置记录
- **AND** 默认语言为 en → zh
- **AND** 默认排版配置 `default_formatting` 为 null（保持原样）
- **AND** `fallback_model` 有一个预设的默认值

#### Scenario: 获取用户设置
- **WHEN** 用户请求 `GET /api/settings`
- **THEN** 系统返回当前用户的设置数据
- **AND** 包含 `default_formatting` 排版默认值（可为 null）
- **AND** 包含 `fallback_model` 字段

#### Scenario: 更新用户设置
- **WHEN** 用户请求 `PUT /api/settings` 携带新设置
- **THEN** 系统更新 Supabase 中的对应记录
- **AND** 返回更新后的设置
- **AND** `default_formatting` 字段以 JSONB 格式存储
- **AND** `fallback_model` 字段可被独立更新

### Requirement: Settings Page UI
前端 SHALL 提供系统设置页面供用户管理偏好，并包含 Fallback 模型配置。

#### Scenario: 查看设置页面
- **WHEN** 用户访问 `/settings` 页面或高级配置面板
- **THEN** 系统显示当前设置，包含：
  - 默认源语言
  - 默认目标语言
  - Fallback 翻译模型名称输入框
  - 功能开关（术语表生成、作者 API 模式）
