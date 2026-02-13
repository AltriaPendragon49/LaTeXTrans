## MODIFIED Requirements

### Requirement: Advanced Configuration Panel
前端 SHALL 在 Dashboard 页面提供完整的高级配置面板，包含翻译模式、编译策略、术语表生成等选项。

#### Scenario: 展开高级配置面板
- **WHEN** 用户点击 "Advanced Settings" 展开按钮
- **THEN** 系统显示所有高级配置选项
- **AND** 所有选项显示当前值（默认或用户修改后的值）

#### Scenario: 配置翻译模式
- **WHEN** 用户选择翻译模式（全文翻译/文献快速筛查）
- **THEN** 选择立即生效，存储在前端状态中
- **AND** 提交翻译时该配置传递给后端

#### Scenario: 配置术语表生成
- **WHEN** 用户启用"生成术语表"选项
- **THEN** 翻译完成后生成术语表文件
- **AND** 前端结果页提供术语表查看和下载功能

#### Scenario: 使用作者API时锁定翻译模型
- **WHEN** 用户开启"使用作者默认 API"开关
- **THEN** 翻译模型输入框变为禁用状态
- **AND** 显示当前作者默认模型名称（只读）
- **AND** 显示提示文字说明模型被锁定的原因

#### Scenario: 关闭作者API时解锁翻译模型
- **WHEN** 用户关闭"使用作者默认 API"开关
- **THEN** 翻译模型输入框恢复为可编辑状态
- **AND** 用户可以自由输入任意模型名称
