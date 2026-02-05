# web-api Specification Delta

## ADDED Requirements

### Requirement: ArXiv Download Async Mode
后端 SHALL 将 arXiv 下载端点改为异步模式，立即返回 task_id 并在后台执行下载。

#### Scenario: 发起 arXiv 下载
- **WHEN** 用户请求 `POST /api/arxiv` 包含有效的 arxiv_id
- **THEN** 系统立即创建任务，返回 `{task_id, arxiv_id, status: "downloading"}`
- **AND** 在后台异步执行下载流程

#### Scenario: 查询下载进度
- **WHEN** 用户请求 `GET /api/task/{task_id}` 且任务状态为 "downloading"
- **THEN** 系统返回 `{status: "downloading", progress: <0-100>, stage: <stage_name>, message: <description>}`
- **AND** progress 反映真实的下载和解析进度

#### Scenario: 下载完成后状态变更
- **WHEN** arXiv 下载和解析全部完成
- **THEN** 任务状态变为 "pending"（准备翻译）
- **AND** progress 为 100
- **AND** source_available 为 true

### Requirement: Download Progress Stages
后端 SHALL 在下载过程中报告细粒度的进度阶段。

#### Scenario: 下载 TeX 源码阶段
- **WHEN** 系统正在从 arXiv 下载 tar.gz 文件
- **THEN** stage 为 "downloading"
- **AND** progress 在 0-30% 范围内

#### Scenario: 解压文件阶段
- **WHEN** 系统正在解压 tar.gz 文件
- **THEN** stage 为 "extracting"
- **AND** progress 在 30-60% 范围内

#### Scenario: 下载 PDF 阶段
- **WHEN** 系统正在下载原文 PDF
- **THEN** stage 为 "downloading_pdf"
- **AND** progress 在 60-80% 范围内

#### Scenario: 验证文件阶段
- **WHEN** 系统正在验证 .tex 文件存在性
- **THEN** stage 为 "validating"
- **AND** progress 在 80-100% 范围内
