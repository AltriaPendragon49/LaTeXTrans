# Change: 修复翻译流程用户体验问题

## Why
前端存在多个用户体验问题影响使用流畅度：
1. 点击"开始翻译"后需要等待API响应才跳转到处理界面,体验延迟
2. 点击"预览"按钮触发PDF自动下载，而非在浏览器中显示
3. 译文PDF无法在iframe中内嵌显示（因后端返回attachment响应头）
4. 左侧边栏与顶部导航栏存在显示冲突，侧边栏未正确保留布局空间，导致组件重叠

## What Changes
- **Frontend (Dashboard.tsx)**: 点击翻译后立即跳转到处理页面，API调用在后台执行，提升响应速度
- **Backend (download.py)**: 新增 `/api/preview/{task_id}/pdf` 端点，返回 `Content-Disposition: inline` 使PDF可内嵌显示
- **Frontend (Comparisons.tsx)**: 预览使用preview端点（iframe显示），下载按钮使用download端点（下载文件）
- **Frontend (Processing.tsx)**: 支持无taskId的初始化状态，配合立即跳转逻辑
- **Frontend (ui/sidebar.tsx)**: 修复Sidebar组件的布局空间保留逻辑，使用显式CSS变量宽度替代Tailwind类名
- **Frontend (app-sidebar.tsx)**: 实现侧边栏收起时自动隐藏标题，防止与导航栏重叠

## Impact
- 受影响的规范: `web-api`
- 受影响的代码:
  - `backend/app/api/routes/download.py` - 新增preview端点
  - `frontend/src/pages/Dashboard.tsx` - 修改handleTranslate跳转逻辑
  - `frontend/src/pages/Comparisons.tsx` - 区分preview和download URL
  - `frontend/src/pages/Processing.tsx` - 移除强制重定向
  - `frontend/src/components/ui/sidebar.tsx` - 修复布局空间保留逻辑
  - `frontend/src/components/app-sidebar.tsx` - 添加收起状态标题隐藏逻辑
