# 前端 UI/UX 设计文档

## 1. 设计理念 (Design Philosophy)
采用 **"Academic Clarity meets Modern SaaS"** (学术清晰度与现代 SaaS 的结合) 风格。
- **UI UX Pro Max 原则应用**:
  - **视觉分层 (Visual Hierarchy)**: 重点突出"输入"与"结果"，将复杂的配置项（模型参数、路径）折叠处理（Progressive Disclosure）。
  - **交互反馈**: 所有耗时操作（下载、翻译、编译）均需通过 Lottie 动画或流式日志（Streaming Logs）提供实时反馈，拒绝"假死"状态。
  - **沉浸式对比**: 提供高性能的双栏 PDF 阅读器，支持同步滚动（Sync Scroll）和全屏模式。

## 2. 设计系统 (Design System)

### 2.1 色彩体系 (Color Palette)
- **Primary (主色)**: `Indigo-600` (#4F46E5) - 代表智能与科技。
- **Secondary (辅助色)**: `Slate-900` (#0F172A) - 专业的文本与标题颜色。
- **Background (背景)**: `Slate-50` (#F8FAFC) - 柔和的护眼背景，避免纯白刺眼。
- **Status (状态色)**:
  - Success: `Emerald-500`
  - Warning: `Amber-500` (用于编译警告)
  - Error: `Rose-500` (用于下载/翻译失败)

### 2.2 排版 (Typography)
- **Font Family**: `Inter` (UI 字体), `JetBrains Mono` (代码/日志/LaTeX 片段)。
- **Scale**: Header (24px/30px), Body (14px/16px), Caption (12px).

### 2.3 核心组件库 (Component Stack)
基于 `shadcn/ui` (Radix UI + Tailwind) 进行定制：
- **Button**: 支持 Loading 状态和 Icon 组合。
- **Sheet/Drawer**: 用于侧边栏配置面板，避免占用主视野。
- **Split/Resizable Panel**: 用于 PDF 双栏对比。
- **Toast**: 用于操作结果通知。

## 3. 页面布局与功能映射 (Layout & Mapping)

### 3.1 核心布局 (App Shell)
采用 **Sidebar Layout (侧边栏布局)**：
- **Sidebar (Left, Fixed, 250px)**:
  - Logo: "LaTeXTrans 🚀" (带渐变效果)
  - Navigation: [新建翻译], [历史记录], [术语库管理], [系统设置]
  - User Profile / API Key Status (底部)
- **Main Content (Flex Grow)**:
  - 动态路由内容区域。

### 3.2 功能页面详细设计

#### A. 新建翻译 (New Translation - Dashboard)
对应原型的 `st.sidebar` 输入 + `st.button`。
- **Hero Section**: 居中的大搜索框 "Enter ArXiv ID or Upload Project"，支持拖拽上传。
- **Quick Config (快速配置)**:
  - 语言对选择 (Source -> Target)，使用国旗图标增强识别。
  - 模型快速切换 (Dropdown)。
- **Advanced Settings (折叠面板)**:
  - 包含 `tex_sources_dir`, `output_dir` 等文件路径配置。
  - 包含 `API Key`, `Base URL` 等敏感信息配置（支持掩码显示）。
  - **术语配置**: "Use Default" vs "Upload Custom CSV" (支持文件预览)。
- **Action Area**:
  - 巨大的 "Translate Now" 按钮，点击后进入 "Processing View"。

#### B. 处理中视图 (Processing View)
对应原型的 `st.spinner` + `st_lottie`。
- **Status Stepper**: 步骤条显示当前进度 (Downloading -> Extracting -> Translating -> Compiling)。
- **Live Logs (Terminal Style)**: 黑色背景控制台，实时滚动显示后端传回的日志，满足极客用户需求。
- **Visual Feedback**: 对应的 Lottie 动画 (Thinking/Writing)。

#### C. 结果预览 (Result Preview)
对应原型的 `st.tabs` (Single/Double Preview)。
- **Toolbar**: 下载 PDF，重新编译，详细日志开关。
- **Viewer**:
  - **Mode 1: Split View (默认)**: 左侧原文 PDF，右侧译文 PDF。中间可拖拽调整比例。
  - **Mode 2: Single View**: 专注阅读译文。
- **Features**: 
  - 缩放控制 (Zoom In/Out)。
  - 页码跳转。

#### D. 配置管理 (Settings Management)
对应原型的配置加载/保存功能。
- 提供可视化的 JSON/TOML 编辑器或表单。
- 支持 "Save as Preset" (保存为预设)，方便不同场景切换。

## 4. 技术实现建议
- **State Management**: 使用 `Zustand` 管理全局配置和翻译状态。
- **PDF Viewer**: 使用 `react-pdf` 或 `pdf.js` 封装组件，或者 `iframe` (如果本地文件服务支持)。
- **API Communication**: TanStack Query (React Query) 处理异步请求和缓存。
