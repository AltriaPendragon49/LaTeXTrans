# 任务列表 (Implementation Tasks)

## Phase 1: 项目初始化与基础架构
- [x] **初始化前端项目**: 使用 Vite + React + TypeScript 初始化项目结构。 <!-- id: init-project -->
- [x] **安装依赖**: 配置 TailwindCSS, lucid-react, framer-motion, zustand, react-router-dom。 <!-- id: install-deps -->
- [x] **搭建设计系统**: 配置 `index.css`, `tailwind.config.js` 以符合设定的色彩和排版规范。 <!-- id: setup-design-system -->
- [x] **集成 shadcn/ui**: 初始化 shadcn 并添加核心组件 (Button, Input, Card, Sheet, etc.)。 <!-- id: setup-shadcn -->

## Phase 2: 核心布局与页面开发
- [x] **实现 App Shell**: 开发包含侧边栏导航 (Sidebar) 和主内容区的响应式布局框架。 <!-- id: layout-shell -->
- [x] **开发仪表盘 (Dashboard)**: 实现 ArXiv ID 输入框、语言选择、模型选择等核心输入组件。 <!-- id: page-dashboard -->
- [x] **开发配置面板**: 实现基于折叠面板/抽屉的高级设置 (文件路径、API Key、术语表上传)。 <!-- id: comp-settings -->
- [x] **开发处理状态页**: 实现翻译进度展示、日志流显示组件 (LogViewer) 和 Lottie 动画集成。 <!-- id: page-status -->
- [x] **开发 PDF 预览器**: 集成 PDF 浏览库，实现双栏对比 (Split View) 和单页预览功能。 <!-- id: comp-pdf-viewer -->

## Phase 3: 逻辑对接与优化
- [x] **定义 API 接口层**: 编写 API Client (Axios/Fetch) 对接后端 FastAPI 接口 (基于 contract-first)。 <!-- id: api-integration -->
- [x] **状态管理集成**: 使用 Zustand 串联配置、输入、任务状态和结果数据。 <!-- id: state-management -->
- [x] **UI/UX 细节打磨**: 添加 Loading 骨架屏、Toast 通知、错误处理边界和微交互动画。 <!-- id: ui-polish -->
