# 前端 UI/UX 设计方案 (Design Web UI)

## 目标 (Goal)
基于现有的 Streamlit 原型 (`prototype_system/src/UI/UI.py`)，为 LaTeXTrans-Pro 设计一个基于 React + TailwindCSS 的现代化、生产级前端界面。目标是提供"UI/UX Pro Max"级别的用户体验，解决 Streamlit 在交互性、布局灵活性和响应速度上的局限，实现一个"全覆盖"功能且视觉惊艳的学术翻译平台。

## 背景 (Context)
主要目标是迁移并增强现有的 Streamlit 原型功能。
原 Streamlit 系统包含：
- **侧边栏配置**：ArXiv ID 输入、源/目标语言选择、术语表配置（更新/上传）、模型配置（DeepSeek/OpenAI 等）。
- **主功能区**：翻译触发按钮、Lottie 动画状态展示。
- **预览区**：PDF 单页预览、双页对比（原文 vs 译文）。
- **文件与配置管理**：路径设置、TOML 配置文件加载/保存。

## 变更范围 (Scope)
本提案仅涵盖 **UI/UX 设计与架构规划**。实际的代码实现将在批准后执行。
设计将包括：
- **设计系统 (Design System)**：色彩、排版、组件库规范。
- **页面布局 (Layout)**：响应式布局策略。
- **组件架构 (Component Architecture)**：核心功能模块拆分。
- **交互流程 (Interaction Flow)**：配置 -> 翻译 -> 预览的用户旅程。

## 依赖 (Dependencies)
- 前端技术栈：React 18+, TailwindCSS, Vite, Lucide React (图标), Framer Motion (动画), shadcn/ui (基础组件库).
- 后端 API：需要与现有的 FastAPI 后端对接（本设计将定义所需的数据接口契约）。
