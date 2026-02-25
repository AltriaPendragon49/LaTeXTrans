# file-management Specification Delta

## Purpose
优化 Upload 存储结构，实现 arXiv 论文下载去重和共享缓存，并在任务删除时保护 Upload 内容。

## ADDED Requirements

### Requirement: Upload Storage Structure
arXiv 论文上传目录 SHALL 以 arxiv_id 为 key 存储，支持跨任务共享。

#### Scenario: arXiv 论文下载存储
- **WHEN** 用户请求下载 arXiv 论文（arxiv_id）
- **THEN** 系统将源文件存储到 `uploads/arxiv_{arxiv_id}/` 目录
- **AND** 任务的 source_path 指向该共享目录

#### Scenario: 重复下载同一论文
- **WHEN** 用户请求下载已存在的 arXiv 论文
- **AND** `uploads/arxiv_{arxiv_id}/` 目录已存在
- **THEN** 系统跳过下载，source_path 直接指向已有目录
- **AND** Load 操作秒级完成

#### Scenario: 文件上传推断 arxiv_id
- **WHEN** 用户上传 .zip/.tar.gz/.rar 文件
- **AND** 系统从目录名或文件名推断出 arxiv_id
- **AND** `uploads/arxiv_{arxiv_id}/` 目录已存在
- **THEN** source_path 指向已有共享目录，避免重复存储

#### Scenario: 无法推断 arxiv_id 的上传
- **WHEN** 用户上传文件且无法推断 arxiv_id
- **THEN** 系统保持 `uploads/{task_id}/` 存储结构不变

### Requirement: Upload Deletion Protection
系统 SHALL 在删除历史任务时保留 Upload 目录内容。

#### Scenario: 删除任务保留 uploads
- **WHEN** 用户删除翻译任务记录
- **THEN** 系统删除 `outputs/{task_id}/` 和 `terms/{task_id}/` 目录
- **AND** 系统 SHALL NOT 删除 uploads 相关目录
- **AND** uploads 内容作为缓存保留供未来使用

### Requirement: Source PDF Preview Compatibility
系统 SHALL 在共享 Upload 目录下正确缓存编译的源 PDF。

#### Scenario: 编译源 PDF 缓存
- **WHEN** 系统编译源 tex 生成预览 PDF
- **THEN** 缓存文件命名为 `source_compiled.pdf`（不含 task_id）
- **AND** 同一 uploads 目录的后续请求直接使用缓存

### Requirement: Upload Failure Cleanup
系统 SHALL 在上传失败时自动清理已创建的临时目录，避免垃圾缓存累积。

#### Scenario: 上传文件格式无效
- **WHEN** 用户上传的文件格式无效（损坏的 ZIP、缺少 RAR 工具等）
- **THEN** 系统返回错误响应
- **AND** 系统 SHALL 自动删除已创建的临时上传目录

#### Scenario: LaTeX 项目校验失败
- **WHEN** 用户上传的文件解压成功但 LaTeX 项目校验失败
- **THEN** 系统返回校验错误信息
- **AND** 系统 SHALL 自动删除已创建的临时上传目录

#### Scenario: 上传成功保留目录
- **WHEN** 用户上传的文件格式有效且 LaTeX 校验通过
- **THEN** 系统保留上传目录
- **AND** 系统 SHALL NOT 删除该目录

## Cross-References
- 关联: translation-history (任务删除行为变更)
- 关联: task-lifecycle (延迟持久化与上传清理)
