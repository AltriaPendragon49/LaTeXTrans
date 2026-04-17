## MODIFIED Requirements
### Requirement: PDF预览端点
系统 SHALL 提供独立的 PDF 预览端点，支持在浏览器 iframe 中内嵌显示译文 PDF。  
当普通任务启用 COS 主存储时，预览仍 SHALL 由后端代理，不直接把签名 URL 暴露为前端必须拼接的下载地址。

#### Scenario: 获取 PDF 用于浏览器预览
- **WHEN** 前端请求 `GET /api/preview/{task_id}/pdf`
- **THEN** 系统返回 PDF 文件，响应头包含 `Content-Disposition: inline; filename="preview_{task_id}.pdf"`，允许浏览器内嵌显示

#### Scenario: 预览未完成的任务
- **WHEN** 用户请求 preview 端点但任务状态不是 `completed` 或 `completed_with_warnings`
- **THEN** 系统返回 HTTP 400 错误，提示 "Translation not completed"

#### Scenario: 预览不存在的任务
- **WHEN** 用户请求 preview 端点但 `task_id` 不存在
- **THEN** 系统返回 HTTP 404 错误，提示 "Task not found"

#### Scenario: COS 模式普通任务 PDF 预览由后端代理
- **WHEN** `STORAGE_BACKEND_MODE=cos` 且普通任务译文 PDF 已持久化到 COS
- **THEN** `GET /api/preview/{task_id}/pdf` SHALL 通过后端代理返回内联 PDF 内容
- **AND** 前端不需要自行拼接或解析 COS 签名下载地址

### Requirement: Terminology Table Download Endpoint
后端 SHALL 提供术语表下载端点。  
当普通任务启用 COS 主存储时，下载类接口 SHALL 使用签名 URL 交付而不是依赖长期本地文件。

#### Scenario: 下载术语表
- **WHEN** 用户请求 `GET /download/{task_id}/terminology`
- **THEN** 系统返回 CSV 格式的术语表文件
- **AND** 响应头包含 `Content-Disposition: attachment`

#### Scenario: 术语表不存在
- **WHEN** 任务未生成术语表（`generate_terminology_table = false`）
- **THEN** 系统返回 HTTP 404 错误

#### Scenario: COS 模式术语表下载使用签名 URL
- **WHEN** `STORAGE_BACKEND_MODE=cos` 且普通任务术语表已持久化到 COS
- **THEN** `GET /download/{task_id}/terminology` SHALL 返回到签名 COS URL 的下载交付
- **AND** 客户端无需依赖长期本地输出目录

## ADDED Requirements
### Requirement: Ordinary Task Download Delivery Supports Signed COS URLs
When ordinary-task object storage mode is enabled, download-class endpoints SHALL deliver ordinary-task artifacts through signed COS URLs while preserving the existing API entry points.

#### Scenario: COS mode translated PDF download uses signed URL
- **WHEN** `STORAGE_BACKEND_MODE=cos` and a completed ordinary task requests `GET /download/{task_id}/pdf`
- **THEN** the backend SHALL resolve the durable translated PDF object from the stored output manifest
- **AND** the response SHALL deliver the file through a short-lived signed COS URL with attachment semantics

#### Scenario: COS mode translated source download uses signed URL
- **WHEN** `STORAGE_BACKEND_MODE=cos` and a completed ordinary task requests `GET /download/{task_id}/source`
- **THEN** the backend SHALL resolve the durable translated-source archive from the stored output manifest
- **AND** the response SHALL deliver the file through a short-lived signed COS URL with attachment semantics

#### Scenario: COS mode logs download uses signed URL
- **WHEN** `STORAGE_BACKEND_MODE=cos` and an ordinary task requests `GET /download/{task_id}/logs`
- **THEN** the backend SHALL resolve an available durable log artifact from the stored output manifest
- **AND** the response SHALL deliver the file through a short-lived signed COS URL with attachment semantics
