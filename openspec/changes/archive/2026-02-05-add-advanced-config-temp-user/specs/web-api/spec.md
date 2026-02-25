# web-api Specification Delta

## ADDED Requirements

### Requirement: Advanced Configuration in Translation Request
后端 SHALL 接受翻译请求中的高级配置参数，并将其注入到翻译 Agent 中。

#### Scenario: 翻译请求包含高级配置
- **WHEN** 前端提交 `POST /translate/{task_id}` 请求
- **THEN** 请求体包含 `advanced_config` 对象
- **AND** 包含所有配置项：translation_mode, compile_strategy, enable_verification, generate_terminology_table 等

#### Scenario: 后端处理自定义 API 配置
- **WHEN** 后端接收到 use_author_api = false 的请求
- **THEN** 后端使用 custom_base_url 和 custom_api_key 构建 LLM 配置
- **AND** 自动在 custom_base_url 末尾追加 /v1/chat/completions（如未包含）

#### Scenario: 配置持久化到任务记录
- **WHEN** 翻译任务创建成功
- **THEN** 任务记录包含 `advanced_config` 字段
- **AND** 配置值为创建时的实际值

### Requirement: Terminology Table Download Endpoint
后端 SHALL 提供术语表下载端点。

#### Scenario: 下载术语表
- **WHEN** 用户请求 `GET /download/{task_id}/terminology`
- **THEN** 系统返回 CSV 格式的术语表文件
- **AND** 响应头包含 `Content-Disposition: attachment`

#### Scenario: 术语表不存在
- **WHEN** 任务未生成术语表（generate_terminology_table = false）
- **THEN** 系统返回 HTTP 404 错误

### Requirement: Source PDF Preview Endpoint
后端 SHALL 提供原文 PDF 预览端点，支持多种来源策略。

#### Scenario: 预览 arXiv 论文原文
- **WHEN** 用户请求 `GET /preview/{task_id}/source-pdf` 且任务来源为 arXiv
- **THEN** 系统从 arXiv 下载原文 PDF 并返回

#### Scenario: 预览本地上传论文原文
- **WHEN** 用户请求预览本地上传的论文
- **THEN** 系统查找目录中现有的 PDF 或编译源 tex 生成 PDF

## MODIFIED Requirements

### Requirement: Task Status Tracking
任务状态 API SHALL 返回完整任务信息，包括高级配置。

#### Scenario: Query task status during processing
- **WHEN** user sends `GET /task/{task_id}` while translation is in progress
- **THEN** the system returns JSON with `{status: "processing", progress: <0-100>, stage: <current_stage>, message: <description>, advanced_config: <config>}`

#### Scenario: Query completed task status (perfect compilation)
- **WHEN** user sends `GET /task/{task_id}` for a successfully completed translation with zero compilation errors
- **THEN** the system returns `{status: "completed", progress: 100, stage: "done", output_path: <path_to_pdf>, advanced_config: <config>}`
