# OpenSpec Proposal: Refine Paper Detail Layout (Lumina Blue)

## Overview
针对 Lumina Blue 主题迁移后的论文详情页进行布局精调。主要解决标题栏冗余、阅读区压缩、侧边栏不等高以及阅读区视觉噪音（白框）等问题。

## Problem Statement
1. **标题栏冗余**：目前页面顶部和阅读器内部各有一个标题栏，浪费垂直空间。
2. **高度不一致**：Agent 侧边栏与阅读器区域在不同视口下高度未严格同步，导致视觉错位。
3. **视觉噪音**：阅读器外层的圆角白框和阴影在沉浸式阅读模式下显得突兀。

## Final Design & Implementation
1. **统一标题栏**：整合所有元数据到三行分层结构中。
   - **Row 1 (h-12)**: 标题及核心控制。
   - **Row 2 & 3 (h-8)**: 作者及指标。
2. **一键折叠功能 (Compact Mode)**: 
   - 增加 `isHeaderExpanded` 状态。
   - 实现一键隐藏第二、三行，极限压缩 Header 高度至 48px，为阅读区提供最大沉浸感。
3. **强制等高同步**: 重构 `PaperDetailWorkspace`，确保阅读器与 Agent 面板高度实时同步。
4. **扁平化去框化**: 移除所有内部白框、边框和阴影，实现真正的全屏沉浸阅读。
5. **功能增强与噪音消除**:
   - **阅读模式三路切换**: 实现 "原文", "译文 (html)", "译文 (pdf)" 的独立预览模式。
   - **后端 PDF 智能路由**: 优化 `/api/preview/{task_id}/source-pdf` 路由，优先检索本地社区资源。
   - **Agent 交互优化**: 为搜索按钮添加 `active:scale-95` 点击效果；移除 Agent 标签栏冗余滚动条；清理阅读器中 "内嵌阅读器" 等冗余文本。

## Implementation Artifacts
- **Expanded State**: ![Header Expanded](./media/header_expanded.png)
- **Collapsed State**: ![Header Collapsed](./media/header_collapsed.png)

## Dependencies
- `PaperDetail.tsx`
- `PaperDetailWorkspace.tsx`
- `PaperPreviewReader.tsx`
- Lumina Blue Design Tokens (`index.css`)
