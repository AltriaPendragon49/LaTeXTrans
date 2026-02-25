# 任务列表

## 后端任务

### 1. 重构 arXiv 下载为异步任务
- [x] 修改 `arxiv.py` 中的 `download_arxiv` 端点，改为异步模式
- [x] 立即创建 task 并返回 task_id，后台线程执行下载
- [x] 使用 `asyncio.create_task` 实现后台下载

### 2. 实现下载进度追踪
- [x] 创建 `DownloadProgressCallback` 类，替代 tqdm 直接输出
- [x] 在 `utils.py` 的 `download_tex` 函数中集成进度回调
- [x] 支持的进度阶段：
  - `downloading`: 下载 TeX 源码 (0-30%)
  - `extracting`: 解压文件 (30-60%)
  - `downloading_pdf`: 下载 PDF (60-80%)
  - `validating`: 验证文件 (80-100%)

### 3. 更新 TaskManager 进度接口
- [x] 确保 `update_task` 支持细粒度进度更新（已存在）
- [x] 添加 `stage` 字段描述当前下载阶段（已存在）

## 前端任务

### 4. 添加 Progress UI 组件
- [x] 安装 shadcn/ui 的 Progress 组件
- [x] 按照 ui-ux-pro-max 规范定制样式
- [x] 支持动画效果和暗/亮模式

### 5. 修改 Dashboard 页面
- [x] 在 "Load Source" 按钮下方添加进度条区域
- [x] 实现条件渲染：仅在下载中显示进度条
- [x] 显示进度百分比和阶段描述文字

### 6. 实现下载进度轮询
- [x] 在 `useStore.ts` 中添加 `pollDownloadProgress` 方法
- [x] 修改 `startArxivDownload` 为立即返回 task_id 模式
- [x] 创建专门的下载进度轮询逻辑（复用 pollStatus 模式）
- [x] 在 `TaskStatusResponse` 接口添加 `stage` 字段

## 验证任务

### 7. 后端 API 测试
- [x] 编写 pytest 测试验证异步下载流程
- [x] 测试进度更新是否正确（0→30→60→80→100%）

### 8. 前端集成测试
- [x] 手动测试：输入有效 arXiv ID，观察进度条是否正确更新
- [x] 手动测试：网络慢时进度条是否有真实反馈
- [x] 手动测试：下载失败时进度条是否显示错误状态

## 依赖关系

```
任务 1 → 任务 2 → 任务 3 → 任务 6 → 任务 8
               ↘
任务 4 → 任务 5 ↗
```

任务 4、5 可与后端任务 1-3 并行开发。
