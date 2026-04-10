# user-settings Specification

## Purpose
TBD - created by archiving change add-multi-user-support. Update Purpose after archive.
## Requirements
### Requirement: User Settings Storage
The system SHALL store user settings in MySQL and bind each settings record to the current application's local authenticated user identity instead of relying on Supabase Postgres and RLS.

#### Scenario: First authenticated access to settings
- **WHEN** an authenticated user first visits the settings page or requests the settings API
- **AND** no settings row exists yet for that local user id
- **THEN** the system SHALL create or return the default settings state for that local user
- **AND** the default language direction SHALL remain `en -> zh`
- **AND** the default `default_formatting` value SHALL remain `null`.

#### Scenario: Read user settings
- **WHEN** an authenticated user requests `GET /api/settings`
- **THEN** the system SHALL return the current local user's settings from MySQL
- **AND** it SHALL include `default_formatting` when present.

#### Scenario: Update user settings
- **WHEN** an authenticated user requests `PUT /api/settings`
- **THEN** the system SHALL update the current local user's settings in MySQL
- **AND** it SHALL return the updated settings snapshot
- **AND** `default_formatting` SHALL remain serializable as structured JSON data.

### Requirement: Settings Page UI
前端 SHALL 提供系统设置页面供用户管理偏好。

#### Scenario: 查看设置页面
- **WHEN** 用户访问 `/settings` 页面
- **THEN** 系统显示当前设置，包含：
  - 默认源语言
  - 默认目标语言
  - 功能开关（术语表生成、作者 API 模式）

### Requirement: Settings Effect on Translation
系统 SHALL 使用用户设置作为翻译任务的默认值，包括排版配置。

#### Scenario: 新建翻译任务时应用默认语言
- **WHEN** 用户新建翻译任务时未显式选择语言
- **THEN** 系统使用 `user_settings` 中的默认语言

#### Scenario: 新建翻译任务时应用默认排版配置
- **WHEN** 用户新建翻译任务时未显式修改排版配置
- **THEN** 前端从 `user_settings` 中读取 `default_formatting` 并作为初始值填充排版面板

#### Scenario: 任务级配置覆盖系统默认
- **WHEN** 用户在翻译提交前修改了排版面板中的某些选项
- **THEN** 修改后的值覆盖系统默认值
- **AND** 仅本次翻译任务生效，不修改系统默认值

#### Scenario: 功能开关生效
- **WHEN** 用户启用/禁用某功能开关
- **THEN** 后续翻译任务应用对应的功能配置

