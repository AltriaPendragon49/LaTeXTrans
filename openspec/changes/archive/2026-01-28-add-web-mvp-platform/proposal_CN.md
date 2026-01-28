# 更改：添加基于 Web 的 MVP 翻译平台

## 为什么

当前的原型系统（`prototype_system/`）是一个仅限 CLI 的工具，需要技术知识才能操作。为了使 LaTeX 翻译可供更广泛的受众使用并满足论文要求，我们需要一个基于网络的平台：

- 允许用户上传`.zip`文件或通过浏览器界面提供 arXiv ID
- 提供实时翻译进度反馈
- 可以轻松下载翻译后的 PDF 和源文件
- 保持与现有 CLI 工作流程的向后兼容性

该 MVP 专注于建立完整的端到端管道（前端到后端），无需高级 RAG 或多模式代理功能，遵循“骨架优先”架构原则。

## 有何变化

- **前端**：基于 React 的 Web 应用程序，具有文件上传、进度跟踪和下载功能
- **后端**：FastAPI 服务公开用于上传、翻译、任务状态和下载的 RESTful API
- **项目结构**：新`backend/`和`frontend/``prototype_system/` 旁边的目录
- **代码重用**：根据原型调整现有的 LaTeX 解析器、协调器代理和 arXiv 实用程序
- **存储**：用于上传和输出的基于本地文件的存储（`data/`目录）

**重大变更**：无 - 这是附加的。现有的 CLI 原型仍然有效。

## 影响

### 受影响的规格
- **新**：`web-api`- 用于翻译工作流程的 RESTful API 端点
- **新**：`web-ui`- 用于用户交互的 React 前端
- **新**：`file-management`- 上传、存储和下载处理
- **修改**：`latex-translation-core`- 重构以支持 CLI 和 Web 界面

### 受影响的代码
- 新目录：`backend/`、`frontend/`、`data/`
- 从原型中重用： 
  - `prototype_system/src/agents/coordinator_agent.py`
  - `prototype_system/src/formats/latex/parser.py`
  - `prototype_system/src/formats/latex/utils.py`
  -`prototype_system/main.py`（arXiv 逻辑）
- 保留：`prototype_system/`作为参考实现保持不变

## 时间轴
2周（5阶段路线图的第1阶段）

## 验证标准
- ✅ 可通过 http://localhost:5173 访问 Web UI
- ✅ 文件上传（`.zip`/ `.tex`) 创建任务并触发翻译
- ✅ arXiv ID 输入下载源代码并翻译
- ✅ 前端可见进度更新（0-100%）
- ✅ 翻译后的 PDF 可下载且有效
- ✅ CLI 工作流程（`python main.py --arxiv`）仍然有效