# user-settings Specification Delta

## MODIFIED Requirements

### Requirement: Settings Page UI
前端 SHALL 提供系统设置页面供用户管理偏好。

#### Scenario: 查看设置页面
- **WHEN** 用户访问 `/settings` 页面
- **THEN** 系统显示当前设置，包含：
  - 默认源语言
  - 默认目标语言
  - 功能开关（术语表生成、作者 API 模式）
