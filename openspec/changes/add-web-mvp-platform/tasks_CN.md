# 实施任务

## 1. 代码审计和重构准备
- [x] 1.1 回顾`prototype_system/src/agents/coordinator_agent.py`了解工作流程编排
- [x] 1.2 回顾`prototype_system/src/formats/latex/parser.py`和`compile.py`用于 AST 解析和编译逻辑
- [x] 1.3 回顾`prototype_system/src/formats/latex/utils.py`用于 arXiv 下载实用程序
- [x] 1.4 记录可重用组件和所需的修改（删除 Streamlit 依赖项）
- [x] 1.5 创建重用映射文档列出要复制/改编的文件

## 2. 项目结构初始化（仅后端）
- [x] 2.1 创建`backend/app/`目录结构（`core/`、`api/routes/`、`services/`）
- [x] 2.2 创建`data/`目录结构（`uploads/`、`outputs/`、`terms/`）
- [x] 2.3 创建`docker/`未来容器化的目录
- [x] 2.4 初始化`backend/requirements.txt`具有 FastAPI 依赖项

**注意**：前端初始化（React/Vite 设置）在`add-web-mvp-frontend`改变。

## 3.后端核心服务

**当前阶段**：代理系统适配（3.4）

- [x] 3.1 将 LaTeX 解析器从原型调整为 `backend/app/services/latex/parser.py`
  - ✅ 已复制`prompts.py`（48,373 字节，无需修改）
  - ✅ 全面增强`utils.py`包含原型中的所有 876 行（Streamlit 已删除）
  - ✅ 适应`parser.py`带进度回调（16,739 字节）  
  - ✅ 适应`reconstruct.py`带日志记录（7,268 字节）
- [x] 3.2 将 LaTeX 实用程序调整为 `backend/app/services/latex/utils.py`
  - ✅ 完全迁移所有 876 行 (31KB)
  - ✅ 删除了所有 Streamlit 依赖项
  - ✅ 添加了全面的日志记录
- [x] 3.3 实现带有后备功能的智能 LaTeX 编译器 (`backend/app/services/latex/compiler.py`)
  - ✅ 创建`compile_with_fallback()`首先尝试 pdflatex，然后尝试 xelatex 的函数
  - ✅已实施`.log`file parser to count errors
  - ✅ Compares error counts and selects PDF with fewer errors
  - ✅ Returns best PDF or raises exception if both fail
  - ✅ Supports MiKTeX auto-install for missing packages
- [x] 3.4 Adapt agent system from prototype to `backend/app/services/agents/`
  - ✅ base_tool_agent.py - 添加logging和进度回调
  - ✅ parser_agent.py - 集成LatexParser
  - ✅ generator_agent.py - 集成智能编译器compile_with_fallback()
  - ✅ validator_agent.py - 完整验证逻辑
  - ✅ translator_agent.py - 最复杂（1010行），已改编完成
  - ✅ coordinator_agent.py - 已改编，集成所有代理with structured logging (Python`logging`模块）
  - 更新`generator_agent.py`使用新的`compile_with_fallback()`功能
- [x] 3.5 创建任务管理器服务（`backend/app/services/task_manager.py`）
  - ✅ 内存中任务状态跟踪
  - ✅进度更新机制（0-100%）
  - ✅ 任务状态管理（待处理→处理→完成/失败）


## 4. 后端API实现
- [ ] 4.1 创建FastAPI应用程序框架(`backend/app/main.py`)
  - 使用CORS中间件初始化FastAPI
  - 添加`/health`终点
- [ ] 4.2 实施`POST /upload`端点（`backend/app/api/routes/upload.py`）
  - 接受`.zip`或者`.tex`文件上传
  - 生成唯一的任务ID
  - 将文件保存到`data/uploads/{task_id}/`
  - 提取压缩文件（如果是“.zip”）
  - 返回任务ID和状态
- [ ] 4.3 实施`POST /arxiv`端点（`backend/app/api/routes/arxiv.py`）
  - 在请求正文中接受 arXiv ID
  - 打电话`batch_download_arxiv_tex()`来自改编的实用程序
  - 保存到`data/uploads/{task_id}/`
  - 返回任务ID和状态
- [ ] 4.4 实施`POST /translate/{task_id}`端点（`backend/app/api/routes/translate.py`）
  - 验证任务ID是否存在
  - 加载翻译配置
  - 使用FastAPI`BackgroundTasks`异步运行翻译
  - 打电话`CoordinatorAgent.workflow_latextrans()`在后台
  - 通过TaskManager更新任务状态
- [ ] 4.5 实施`GET /task/{task_id}`端点（`backend/app/api/routes/task.py`）
  - 从TaskManager查询任务状态
  - 返回{状态、进度、消息、错误？}
- [ ] 4.6 实施`GET /download/{task_id}/pdf`端点（`backend/app/api/routes/download.py`）
  - 在“data/outputs/”中找到翻译后的 PDF
  - 将文件作为下载附件返回
- [ ] 4.7 实施`GET /download/{task_id}/source`终点
  - 包翻译`.tex`文件为“.zip”
  - 将存档作为下载附件返回

## 5. 集成与配置
- [x] 5.1 创建后端配置模块(`backend/app/core/config.py`)
  - 从环境变量或`config/default.conf加载设置托姆尔`
  - 使用特定参数配置LLM API：
    *`api_key`: "sk-SVd4dIKfuIwhQ9kUlgCr9ZMpoIWp7PEzZxpVStjSRqeqNBLu" (load from env var `LLM_API_KEY`如果有的话）
    * `base_url`: "https://aicanapi.com/v1/chat/completions"
    * `型号`: "gpt-4.1-mini"
    * `超时`: 60 秒
  - 存储路径配置
  - 任务状态枚举定义（待处理、处理、已完成、completed_with_warnings、failed_compilation、失败）
- [ ] 5.2 连接 `backend/app/main.py` 中的所有 API 路由
  - 导入并包含用于上传、arxiv、翻译、任务、下载的路由器
- [ ] 5.3 配置 CORS 以允许前端源 (http://localhost:5173)
- [ ] 5.4 配置启动脚本环境变量和路径

## 6. 后端API测试
- [ ] 6.1 测试`POST /upload`带样本的端点`.tex`通过curl/Postman 文件
- [ ] 6.2 测试`POST /arxiv`具有有效 arXiv ID 的端点（例如“2508.18791”）
- [ ] 6.3 测试`POST /translate/{task_id}`触发后台翻译
- [ ] 6.4 测试`GET /task/{task_id}`返回正确的状态和进度
- [ ] 6.5 测试`GET /download/{task_id}/pdf`返回有效的 PDF 文件
- [ ] 6.6 测试`GET /download/{task_id}/source`返回有效的 .zip 存档
- [ ] 6.7 测试错误处理：任务ID无效、文件丢失、翻译错误
- [ ] 6.8 测试编译器回退：使用 pdflatex 失败但使用 xelatex 成功的文件
- [ ] 6.9 测试编译器错误比较：有故意错误的文件
- [ ] 6.10 验证 CLI 是否仍然有效：`python prototype_system/main.py --arxiv 2508.18791`

**注意**：与前端 UI 的端到端集成测试在`add-web-mvp-frontend`改变。

## 7. 文档
- [ ] 7.1 创建`backend/README.md`带有设置和运行说明
- [ ] 7.2 文档 API 端点（通过 FastAPI 自动生成 OpenAPI/Swagger）
- [ ] 7.3 创建API测试指南（curl示例、Postman集合）
- [ ] 7.4 为常见后端问题创建故障排除指南

**注意**：前端文档在`add-web-mvp-frontend`改变。

## 8. 部署准备
- [ ] 8.1 创建`backend/Dockerfile`用于容器化（推迟到第 4 阶段）
- [ ] 8.2 创建后端启动脚本：
  -`backend/start.sh`（设置环境，运行uvicorn）
- [ ] 8.3 记录后端环境设置要求

## 依赖关系和排序

**关键路径**：每个部分中的任务必须按顺序完成。
**阻滞剂**： 
- 任务 3.x 必须在 4.x 之前完成（API 需要服务）
- 任务 4.x 必须在 6.x 之前完成（测试需要端点）
- 任务 1.x 必须在 3.x 之前完成（需要了解要适应什么）