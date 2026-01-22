# 实施任务

## 先决条件
**必需**：后端更改`add-web-mvp-platform`必须在开始这些任务之前完成并运行。验证后端 API 端点可通过 http://localhost:8000 访问。

## 1.前端项目初始化
- [ ] 1.1 使用 Vite 创建 React 应用：`npm create vite@latest frontend -- --template React`
- [ ] 1.2 安装依赖项：`cd frontend && npm install`
- [ ] 1.3 安装axios：`npm install axios`
- [ ] 1.4 安装 TailwindCSS: `npm install -D tailwindcss postcss autoprefixer`
- [ ] 1.5 初始化 TailwindCSS 配置：`npx tailwindcss init -p`
- [ ] 1.6 配置 Tailwind`src/index.css`（添加指令）
- [ ] 1.7 更新`package.json`带有项目元数据

## 2. API 客户端层
- [ ] 2.1 创建`src/utils/api.js`与 Axios 实例
  - 基本 URL：`http://localhost:8000`
  - 配置超时和错误处理
- [ ] 2.2 实现API方法：
  -`uploadFile(file)`→ 发布/上传
  -`submitArxivId(arxivId)`→ 发布/arxiv
  -`startTranslation(taskId)`→ POST /translate/{taskId}
  -`getTaskStatus(taskId)`→ 获取 /task/{taskId}
  -`downloadPDF(taskId)`→ 获取 /download/{taskId}/pdf
  -`downloadSource(taskId)`→ GET /download/{taskId}/source

## 3. UI 组件开发
- [ ] 3.1 创建 `src/components/FileUpload.jsx`
  - 拖放区域`.tex`和`.zip`文件
  - 文件验证（扩展名：`.tex`、`.zip`；大小限制：50MB）
  - 显示选定的文件名和大小
  - 上传进度指示器
  - 打电话`uploadFile()`API并存储返回的任务ID
  - 使用用户友好的消息进行错误处理

- [ ] 3.2 创建 `src/components/ArxivInput.jsx`
  - 带占位符的文本输入“例如，2508.18791”
  - 格式验证（正则表达式：`^\d{4}\.\d{4,5}$`）
  - 带有加载状态的提交按钮
  - 打电话`submitArxivId()`API并存储返回的任务ID
  - 显示 arXiv fetch 的下载状态

- [ ] 3.3 创建 `src/components/ProgressTracker.jsx`
  - 民意调查`getTaskStatus()`当任务处于活动状态时每 2 秒一次
  - 平滑过渡的进度条（0-100%）
  - 阶段指示器：“解析”→“翻译”→“编译”
  - 当前消息显示（例如，“处理部分 3/10”）
  - 带有红色警报样式的错误显示
  - 当状态为“完成”或“失败”时自动停止轮询

- [ ] 3.4 创建`src/components/DownloadButton.jsx`
  - 当任务状态为“已完成”时有条件渲染
  - “下载 PDF”按钮 → 触发 `downloadPDF()`
  - “下载源代码 (.zip)”按钮 → 触发 `downloadSource()`
  - 通过浏览器下载机制处理文件下载
  - 下载期间的加载状态

- [ ] 3.5 创建`src/components/TabSwitcher.jsx`
  - 在“上传文件”和“arXiv ID”模式之间切换
  - 活动选项卡突出显示
  - 切换选项卡时保留状态

## 4. 主要应用布局
- [ ] 4.1 更新`src/App.jsx`主要布局：
  - 标题：带有徽标的项目标题“LaTeXTrans-Pro”
  - 选项卡切换器组件
  - 左侧面板：FileUpload 或 ArxivInput（基于活动选项卡）
  - 右面板：进度跟踪器 + 下载按钮
  - 响应式布局（适合移动设备）

- [ ] 4.2 实施状态管理：
  - 当前任务ID
  - 任务状态（待处理、处理中、已完成、失败）
  - 活动选项卡选择
  - 错误消息

- [ ] 4.3 应用 TailwindCSS 样式：
  - 现代、简洁的设计，具有玻璃形态效果
  - 配色方案：深色模式支持
  - 状态转换的平滑动画
  - 可访问的焦点状态和 ARIA 标签

## 5. 集成测试
- [ ] 5.1 测试场景：上传简单`.tex`文件
  - 通过拖放选择文件
  - 验证文件有效性（接受.tex，拒绝.pdf）
  - 确认上传启动翻译
  - 验证进度更新是否出现
  - 完成后确认PDF下载是否有效

- [ ] 5.2 测试场景：输入 arXiv ID（例如 `2508.18791`）
  - 输入有效的 arXiv ID
  - 验证格式有效性
  - 确认 arXiv 下载触发器
  - 验证翻译进度
  - 确认PDF下载有效

- [ ] 5.3 测试场景：上传`.zip`有多个文件
  - 上传压缩档案
  - 验证提取消息是否出现
  - 确认主文件检测
  - 验证翻译完成

- [ ] 5.4 测试错误处理：
  - 文件格式无效（例如“.pdf”）
  - 文件太大（>50MB）
  - arXiv ID 不存在
  - 后端API无法访问
  - 翻译失败（后端错误）

- [ ] 5.5 跨浏览器测试：
  - Chrome（最新）
  - 火狐浏览器（最新）
  - 边缘（最新）
  - Safari（如果有）

- [ ] 5.6 响应式设计测试：
  - 桌面 (1920x1080)
  - 笔记本电脑 (1366x768)
  - 平板电脑 (768x1024)
  - 移动设备 (375x667)

## 6. 文档
- [ ] 6.1 创建`frontend/README.md`:
  - 先决条件（Node.js 18+）
  - 安装说明
  - 开发服务器命令：`npm run dev`
  - 构建命令：`npm run build`
  - 环境配置（.env 变量，如果需要）

- [ ] 6.2 更新主项目 `README.md`:
  - 添加前端设置部分
  - 使用前端说明更新快速入门指南
  - 添加网页界面截图

- [ ] 6.3 创建故障排除指南：
  - 常见的CORS问题
  - 后端连接错误
  - 文件上传失败
  - 浏览器兼容性问题

## 7. 部署准备
- [ ] 7.1 创建`frontend/start.sh`启动脚本：
  ````bash
  #!/bin/bash
  CD前端
  npm 安装
  npm 运行开发
  ````

- [ ] 7.2 验证生产版本：
  - 运行“npm run build”
  - 在`dist/`中测试构建的文件
  - 确保构建大小合理（<5MB）

- [ ] 7.3 配置环境变量（如果需要）：
  -`VITE_API_BASE_URL`对于后端端点
  - 创建`.env.example`模板

## 依赖关系和排序

**关键依赖项**：
- ❗ 在测试任何前端功能之前，后端 API 必须运行且可访问
- ❗ 所有 API 端点来自`add-web-mvp-platform`必须得到实施并发挥作用

**推荐订单**：
1. 首先完成第 1 部分（项目初始化）
2. 完成第 2 部分（API 客户端）以建立后端连接
3. 按顺序构建第 3 节中的组件 (3.1 → 3.5)
4. 融入第 4 节
5. 在第 5 节中进行彻底测试
6. 第 6 节中的文件

**并行工作**： 
- 如果有多个开发人员可用，则可以并行开发组件 3.1-3.5
- 文档（第 6 节）可以与开发一起编写