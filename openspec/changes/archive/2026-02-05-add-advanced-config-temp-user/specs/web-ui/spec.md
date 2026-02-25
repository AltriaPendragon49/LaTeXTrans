# web-ui Specification Delta

## ADDED Requirements

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

### Requirement: Drag and Drop Upload Zone
前端 SHALL 在 Dashboard 页面提供拖拽上传区域，支持文件夹和压缩包上传。

#### Scenario: 显示拖拽区域
- **WHEN** 用户访问 Dashboard 页面
- **THEN** 页面显示明显的拖拽区域
- **AND** 区域包含"拖拽 LaTeX 文件夹或压缩包到此处"提示

#### Scenario: 拖拽文件进入
- **WHEN** 用户将文件拖拽进入上传区域
- **THEN** 区域边框变为高亮颜色
- **AND** 显示"释放以上传"提示

#### Scenario: 释放文件并显示预览
- **WHEN** 用户在上传区域释放拖拽的文件
- **THEN** 系统显示文件信息预览
- **AND** 显示文件/文件夹名称、文件数量、是否检测到 .tex 文件

### Requirement: Terminology Table Viewer
前端 SHALL 在翻译结果页面提供术语表查看组件。

#### Scenario: 查看术语表
- **WHEN** 用户点击结果页的"术语表"按钮
- **THEN** 系统显示侧边栏，展示术语对照列表
- **AND** 列表包含原文术语和译文术语两列

#### Scenario: 下载术语表
- **WHEN** 用户点击"下载 CSV"按钮
- **THEN** 系统下载 CSV 格式的术语表文件
