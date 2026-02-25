# web-ui Specification Delta

## ADDED Requirements

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
