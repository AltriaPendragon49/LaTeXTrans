# user-auth Specification

## Purpose
TBD - created by archiving change add-multi-user-support. Update Purpose after archive.
## Requirements
### Requirement: User Registration
系统 SHALL 支持新用户通过邮箱密码进行注册。

#### Scenario: 用户注册成功
- **WHEN** 用户在注册页面输入有效邮箱和密码
- **AND** 点击注册按钮
- **THEN** 系统调用 Supabase Auth signUp()
- **AND** 通过自定义 SMTP 服务发送确认邮件到用户邮箱（无需绕过 VPN 限制即可稳定触发）
- **AND** 显示"请查收确认邮件"提示

### Requirement: Email Password Authentication
系统 SHALL 支持已注册用户通过邮箱密码进行登录。

#### Scenario: 用户邮箱登录成功
- **WHEN** 用户在登录页面输入有效的邮箱和密码
- **AND** 点击登录按钮
- **THEN** 系统完成 Supabase Auth 认证
- **AND** 将 JWT token 存储在本地
- **AND** 重定向到仪表盘页面

#### Scenario: 用户邮箱登录失败
- **WHEN** 用户输入无效的邮箱或密码
- **THEN** 系统显示认证失败错误信息
- **AND** 保持在登录页面

### Requirement: User Logout
系统 SHALL 支持用户登出操作。

#### Scenario: 用户登出
- **WHEN** 已登录用户点击登出按钮
- **THEN** 系统清除本地存储的 session
- **AND** 返回到仪表盘页面（可继续使用临时任务）

### Requirement: Guest Mode (Temporary Tasks)
系统 SHALL 支持未登录用户使用临时任务系统。

#### Scenario: 未登录用户创建翻译任务
- **WHEN** 未登录用户提交翻译请求（ArXiv 或上传）
- **THEN** 系统创建临时任务（不绑定 user_id）
- **AND** 任务仅存储在内存中
- **AND** 用户可正常使用翻译功能

#### Scenario: 未登录用户任务不持久化
- **WHEN** 服务器重启或用户关闭浏览器
- **THEN** 未登录用户的任务数据丢失
- **AND** 历史记录页面不显示这些任务

#### Scenario: 登录后任务持久化
- **WHEN** 已登录用户创建翻译任务
- **THEN** 系统将任务绑定到 user_id
- **AND** 任务持久化存储在 Supabase
- **AND** 可在历史记录页面查看

### Requirement: Protected Features
系统 SHALL 保护需要认证的功能，但不阻止基本翻译。

#### Scenario: 未登录用户访问历史记录
- **WHEN** 未登录用户访问 `/history` 页面
- **THEN** 系统提示"请登录以查看翻译历史"
- **AND** 显示登录按钮

#### Scenario: 未登录用户访问设置
- **WHEN** 未登录用户访问 `/settings` 页面
- **THEN** 系统提示"请登录以管理设置"
- **AND** 显示登录按钮

#### Scenario: 未登录用户访问仪表盘
- **WHEN** 未登录用户访问 `/`（仪表盘）
- **THEN** 系统正常显示翻译功能
- **AND** 侧边栏显示"登录"按钮

### Requirement: Backend JWT Verification
后端 API SHALL 支持可选认证，区分登录和未登录用户。

#### Scenario: 有效 JWT token
- **WHEN** API 请求携带有效的 Authorization Bearer token
- **THEN** 系统提取 user_id 并将任务绑定到用户

#### Scenario: 无 JWT token（访客模式）
- **WHEN** API 请求不携带 Authorization header
- **AND** 请求的是基本翻译功能（upload、arxiv、translate、task）
- **THEN** 系统允许请求，创建临时任务

#### Scenario: 无 JWT token 访问受保护功能
- **WHEN** API 请求不携带 Authorization header
- **AND** 请求的是 history、settings 等受保护端点
- **THEN** 系统返回 HTTP 401 Unauthorized 错误

### Requirement: User Profile Page
系统 SHALL 提供简单的用户资料页面。

#### Scenario: 查看用户资料
- **WHEN** 已登录用户访问 `/profile` 页面
- **THEN** 系统显示用户邮箱地址
- **AND** 显示登出按钮

