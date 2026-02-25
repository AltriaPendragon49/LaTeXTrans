# Change: 添加 ArXiv 论文下载进度条

## Why

当前用户在前端页面使用 arXiv 论文 ID 进行翻译时，点击 "Load Source" 按钮后只能看到按钮变灰并显示旋转动画。由于网络问题，这个过程可能耗时很久，用户会觉得系统卡住，体验不佳。需要添加真实的进度条反馈当前下载和解析的实际进度。

## What Changes

### 后端改造
- 将 `POST /api/arxiv` 端点改为异步任务模式，立即返回 task_id，后台执行下载
- 新增下载进度追踪：在 `download_tex` 函数中捕获 tqdm 进度，写入 task 状态
- 定义进度阶段：downloading (0-30%)、extracting (30-60%)、downloading_pdf (60-80%)、validating (80-100%)
- 复用现有的 `GET /api/task/{task_id}` API 轮询获取下载进度

### 前端改造
- 添加 shadcn/ui Progress 组件，遵循 ui-ux-pro-max 设计规范
- 修改 Dashboard 页面：点击 "Load Source" 后显示进度条，带阶段描述和百分比
- 复用 `useStore` 中的 `pollStatus` 模式实现下载进度轮询

## Impact

- Affected specs: web-api, web-ui, file-management
- Affected code: 
  - `backend/app/api/routes/arxiv.py`: 异步下载接口
  - `backend/app/services/latex/utils.py`: 进度回调集成
  - `frontend/src/stores/useStore.ts`: 进度轮询逻辑
  - `frontend/src/components/ui/progress.tsx`: 新增 UI 组件

