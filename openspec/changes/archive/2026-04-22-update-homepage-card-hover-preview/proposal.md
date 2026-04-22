# Change: update homepage card hover preview

## Why
社区首页论文卡片当前使用额外的放大镜式局部预览，交互与用户期望不一致。需要改为悬停时直接放大原卡片本体，减少视觉负担并清理不再需要的旧逻辑。

## What Changes
- 将社区首页论文卡片 PDF 预览的 hover 行为从局部放大镜改为原卡片整页静态放大
- 移除与放大镜跟随、局部裁切、独立 inspector 浮层相关的前端逻辑与测试
- 更新 `web-ui` 规范与相关实现文档，使首页预览行为与当前产品设计保持一致

## Impact
- Affected specs: `web-ui`
- Affected code: `frontend/src/features/community-paper/components/PaperCard.tsx`, `frontend/src/features/community-paper/components/PaperCard.test.tsx`, `frontend/src/features/community-paper/services/pdf-hover-preview.ts`
