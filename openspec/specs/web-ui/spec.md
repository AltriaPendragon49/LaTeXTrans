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

#### Scenario: 配置使用作者默认API
- **WHEN** 用户在 Dashboard 高级配置面板查看功能开关区域
- **THEN** 系统显示两个并排的 toggle 卡片：
  - 「使用作者默认 API」toggle（左侧）
  - 「生成术语表」toggle（右侧）
- **AND** 无"验证代理"选项

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

### Requirement: Session Continuity for Temporary Users

The system SHALL allow temporary users to create multiple translation tasks without page refresh.

#### Scenario: New translation after completion
- **WHEN** user clicks "New Translation" button after task completion
- **THEN** frontend resets all task-related state (taskId, status, progress)
- **AND** closes any active SSE connection
- **AND** returns to initial file upload view

#### Scenario: New translation after failure
- **WHEN** user clicks "New Translation" button after task failure
- **THEN** frontend performs same state reset as completion scenario
- **AND** user can immediately start new upload/arXiv download

### Requirement: SSE-based Status Subscription

The system SHALL use Server-Sent Events for real-time status updates.

#### Scenario: SSE connection for task monitoring
- **WHEN** user starts a translation task
- **THEN** frontend establishes SSE connection to `/api/task/{task_id}/stream`
- **AND** updates UI immediately upon receiving events

#### Scenario: SSE fallback to polling
- **WHEN** SSE connection fails or is not supported
- **THEN** frontend falls back to `setInterval` polling at 2-second intervals
- **AND** user experience remains consistent

### Requirement: Reduced API Request Volume
The frontend MUST NOT generate more than 2 status queries per second during download operations.

#### Scenario: Request rate under normal SSE
- **WHEN** SSE connection is active
- **THEN** no polling requests SHALL be made
- **AND** API request rate SHALL be zero for status queries

#### Scenario: Request rate under fallback polling
- **WHEN** using fallback polling mode
- **THEN** polling interval SHALL be at least 2000ms
- **AND** API request rate SHALL NOT exceed 0.5 requests per second

### Requirement: Interactive Dismissible Tips

前端 SHALL 在 Dashboard 页面提供交互式提示框，用于引导用户并平衡页面空间，支持手动快速影藏。

#### Scenario: 提示框显示与点击消失
- **GIVEN** Dashboard 页面加载
- **WHEN** 对应的显示状态为真（默认每次加载为真）
- **THEN** 页面显示相关的 Info Tip（如 ArXiv 下载耗时提示、Nvidia API 性能预警）
- **WHEN** 用户点击提示框任何区域
- **THEN** 提示框通过渐隐缩放动画（fade-out & zoom-out）消失
- **AND** 该提示框在本次页面会话期间不再出现

#### Scenario: 悬停显示关闭反馈
- **GIVEN** 提示框处于显示状态
- **WHEN** 用户将鼠标悬停在提示框上方
- **THEN** 提示框背景色产生微弱变化（交互反馈）
- **AND** 提示框右侧显示 `X` 关闭图标，提示该区域可点击影藏

### Requirement: API Quality and Performance Warnings

前端 SHALL 在翻译配置面板显式提醒默认 API 的性能局限，引导用户进行优化设置。

#### Scenario: 显示 Nvidia 免费 API 警告
- **GIVEN** Dashboard 页面加载
- **THEN** 在 "Advanced Configuration" 栏右侧显示琥珀色（Amber）警告标签
- **AND** 文本告知用户默认 API 为英伟达免费层级，可能影响质量和速度
- **AND** 该警告标签支持交互式点击消失逻辑

### Requirement: Formatting Configuration Panel
前端 SHALL 在 Advanced Settings 面板中提供"排版与文献设置"折叠区，允许用户配置翻译后 PDF 的排版格式，并对关键数值执行范围限制。

#### Scenario: 展开排版配置面板
- **WHEN** 用户在 Advanced Settings 中点击"排版与文献设置"折叠项
- **THEN** 系统显示排版配置表单，包含以下选项组：
  - 版面设置：行距、字号、栏模式、页边距
  - 中文排版：字体、首行缩进（仅中文目标语言时显示）
  - 文献引用：参考文献格式、引文标记风格
  - 其他：图表标题本地化

#### Scenario: 行距和字号数值限制与输入
- **WHEN** 用户查看行距或字号配置项
- **THEN** 显示为一个启用/禁用按钮
- **AND** 启用后出现数字输入框
- **AND** 前端 MUST 限制字号在 `[8, 14]` 范围内，行距在 `[1.0, 2.5]` 范围内
- **AND** 提供解释性 Tooltip 指示这些范围
- **AND** 禁用时恢复为"保持原样"

#### Scenario: 栏模式支持双向切换
- **WHEN** 用户查看栏模式配置项
- **THEN** 显示下拉选项：保持原样 / 单栏 / 双栏

#### Scenario: 配置默认为"保持原样"
- **WHEN** 用户首次打开排版配置面板
- **THEN** 所有选项默认值为"保持原样"
- **AND** 若用户系统设置中有 `default_formatting` 则使用其值填充

#### Scenario: 目标语言联动显示
- **WHEN** 用户选择的目标语言为中文 (zh/ch)
- **THEN** 显示"中文字体"和"首行缩进"选项
- **AND** "图表标题本地化"选项可用

#### Scenario: 排版配置随翻译请求提交
- **WHEN** 用户修改排版配置并点击翻译按钮
- **THEN** 排版配置序列化为 `advanced_config.formatting` JSON 字段
- **AND** 随翻译请求一同提交到后端 API

#### Scenario: 排版配置在批量翻译中共享
- **WHEN** 用户切换到 Batch Tab
- **THEN** 排版配置面板仍然可见且配置对批量任务统一生效

### Requirement: Web UI Branding
The application MUST display professional branding, including a descriptive `<title>` and a unique favicon.

#### Scenario: Browser tab branding
- **WHEN** a user opens or bookmarks the website
- **THEN** they MUST see the application title and favicon in the browser tab.

### Requirement: Premium Download Progress UI
The frontend MUST display an interactive and premium progress bar according to ui-ux-pro-max guidelines.

#### Scenario: Interactive progress bar with shimmer
- **WHEN** a task is in progress
- **THEN** the progress bar MUST display an animated shimmer effect
- **AND** show pulsing status indicators and stage descriptors.

### Requirement: Email Notification Configuration
The UI SHALL allow users to configure email notifications for task events.

#### Scenario: Enabling completion emails
- **WHEN** a user opens Advanced Configuration
- **THEN** they MUST see a toggle switch for "发送邮件通知 (完成时)" 
- **AND** activating it MUST bind the preference to the task payload.

