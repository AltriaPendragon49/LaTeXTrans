# Tasks: Refine Paper Detail Layout

- [x] **Phase 1: Header Reconstruction**
  - [x] 在 `PaperDetail.tsx` 中提取并重构顶部导航栏，实现三行布局。
  - [x] 移除 `PaperDetailWorkspace.tsx` 内部的旧标题栏组件。
  - [x] 将作者、日期等数据作为 props 传递给新 Header。

- [x] **Phase 2: Layout Synchronization**
  - [x] 更新 `PaperDetail.tsx` 的容器高度计算，确保 Workspace 填满剩余空间。
  - [x] 确保 `PaperDetailWorkspace.tsx` 中的左右面板在 split-pane 模式下高度强制相等。

- [x] **Phase 3: Visual Polish & Space Optimization**
  - [x] 在 `PaperDetailWorkspace.tsx` 中移除阅读区面板的 border 和 shadow。
  - [x] 在 `PaperPreviewReader.tsx` 中移除外层容器的框感。
  - [x] **实现一键折叠 (Collapse)**: 添加 Chevron 按钮和 `isHeaderExpanded` 状态。
  - [x] 阅读区极限去框化，实现沉浸式布局。

- [x] **Phase 4: Verification**
  - [x] 检查不同屏幕尺寸下的响应式表现。
  - [x] 验证 Agent 切换开关是否正常工作并保持布局稳定。
  - [x] 通过浏览器子代理验证折叠/展开逻辑。

- [x] **Phase 5: Functional Refinement**
  - [x] 实现并验证阅读模式三选一 (原文, 译文 HTML, 译文 PDF)。
  - [x] 强化后端 ArXiv 本地资源检索逻辑，实现本地 PDF 预扫描。
  - [x] 优化阅读器 UI，移除 "内嵌阅读器" 等冗余文本标签。
  - [x] 为 Agent 工作区 Deep Search/Web Search 按钮添加 active 缩放交互。
  - [x] 修复 Agent 工作区标签容器溢出问题，移除冗余滚动条。
