## MODIFIED Requirements

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

#### Scenario: 使用作者API时锁定翻译模型
- **WHEN** 用户在系统设置页面中开启"使用作者默认 API"
- **THEN** 翻译模型输入框变为禁用状态
- **AND** 显示当前作者默认模型名称（只读）
- **AND** 显示提示文字说明使用作者 API 时模型不可更改

#### Scenario: 关闭作者API时解锁翻译模型
- **WHEN** 用户在系统设置页面中关闭"使用作者默认 API"
- **THEN** 翻译模型输入框恢复为可编辑状态
