# user-auth UX Improvements Delta

## Purpose
改进登录和源文件加载的用户体验交互。

## ADDED Requirements

### Requirement: Load Source Instant Feedback
前端 SHALL 在用户点击 Load Source 按钮时提供即时视觉反馈。

#### Scenario: 点击 Load Source 按钮
- **WHEN** 用户输入有效 ArXiv ID 并点击 Load Source 按钮
- **THEN** 按钮立即切换为 loading 图标（旋转动画）
- **AND** 显示 Toast 提示「正在加载源文件」
- **AND** 按钮添加缩放按压动画

### Requirement: Auto Load Settings After Login
前端 SHALL 在用户登录成功后自动加载并应用用户保存的系统设置。

#### Scenario: 登录后自动加载配置
- **WHEN** 用户通过邮箱密码登录成功
- **THEN** 系统自动从 `/api/settings` 拉取用户配置
- **AND** 将配置应用到 zustand store
- **AND** 显示 Toast 通知「系统设置已加载」

#### Scenario: 新建翻译时自动使用已加载的配置
- **WHEN** 用户登录后访问 Dashboard 创建新翻译
- **THEN** Advanced Configuration 自动显示用户保存的配置
- **AND** 用户无需手动刷新页面

## Cross-References
- 关联: user-settings (配置加载)
- 关联: web-ui (Dashboard 页面)
