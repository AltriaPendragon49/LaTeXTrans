# web-ui Specification

## Purpose
定义 LaTeXTrans 前端 Web UI 规范，包括 Dashboard、翻译配置、进度监控、PDF 预览等界面。
## Requirements
### Requirement: Responsive Web Dashboard
The system MUST provide a responsive web-based dashboard for user interaction.

#### Scenario: User navigates to the home page
Given the backend server is running
When the user accesses the web root URL
Then the Dashboard page should be displayed
And a prominent input field for ArXiv ID should be visible
And the sidebar navigation should be present

### Requirement: Translation Configuration
The system MUST allow users to configure translation parameters via the UI.

#### Scenario: User configures translation settings
Given the user is on the Dashboard
When the user selects "Source Language" and "Target Language"
And the user expands the "Advanced Settings" panel
Then they should be able to input API keys and set file paths
And they should be able to upload a custom terminology file

### Requirement: Real-time Progress Monitoring
The system MUST display real-time progress of the translation task.

#### Scenario: User starts a translation
Given valid configuration is entered
When the user clicks "Translate Now"
Then the view should switch to the "Processing Status" page
And a progress stepper acting as a timeline should update
And real-time logs from the backend should be displayed in a console view

### Requirement: Dual PDF Preview
The system MUST provide a comprehensive PDF preview and comparison tool.

#### Scenario: Translation completes successfully
Given the translation task has finished
When the user navigates to the "Preview" tab
Then they should see a split-screen view
And the left pane should display the original PDF
And the right pane should display the translated PDF

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

### Requirement: ArXiv Download Progress Bar
前端 SHALL 在 Dashboard 页面的 Load Source 按钮下方显示下载进度条，反映真实的后端下载进度。

#### Scenario: 点击 Load Source 后显示进度条
- **WHEN** 用户在 arXiv ID 输入框输入有效 ID 并点击 "Load Source" 按钮
- **THEN** 系统立即在按钮下方显示进度条组件
- **AND** 进度条初始值为 0%
- **AND** 按钮状态变为禁用

#### Scenario: 进度条实时更新
- **WHEN** 后端返回下载进度更新（通过轮询 /api/task/{task_id}）
- **THEN** 进度条平滑更新到最新进度值
- **AND** 进度条下方显示当前阶段描述（如"正在下载 TeX 源码..."）

#### Scenario: 下载完成后隐藏进度条
- **WHEN** 后端返回 progress: 100 且 status: "pending"
- **THEN** 进度条消失
- **AND** 显示 "Source Ready" 成功提示
- **AND** "Start Translation" 按钮变为可用

#### Scenario: 下载失败时显示错误
- **WHEN** 后端返回 status: "failed"
- **THEN** 进度条变为红色/错误状态
- **AND** 显示错误消息
- **AND** 提供重试按钮

### Requirement: Progress Bar Visual Design
进度条 SHALL 遵循 ui-ux-pro-max 设计规范，提供专业的视觉效果。

#### Scenario: 进度条样式
- **GIVEN** 进度条组件渲染在页面上
- **THEN** 进度条高度为 8px
- **AND** 使用圆角设计（rounded-full）
- **AND** 背景色为 muted，前景色为 primary
- **AND** 进度变化带有平滑过渡动画（duration-300）

#### Scenario: 暗色模式兼容
- **GIVEN** 用户启用暗色模式
- **WHEN** 进度条显示
- **THEN** 进度条颜色适配暗色主题
- **AND** 文字对比度符合 WCAG AA 标准（≥4.5:1）

#### Scenario: 无障碍访问
- **GIVEN** 进度条组件渲染
- **THEN** 组件包含 aria-valuenow、aria-valuemin、aria-valuemax 属性
- **AND** 包含 role="progressbar" 属性
- **AND** 屏幕阅读器可正确读取进度百分比

