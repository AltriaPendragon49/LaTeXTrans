## ADDED Requirements

### Requirement: PDF预览端点
系统 SHALL 提供独立的PDF预览端点，支持在浏览器iframe中内嵌显示译文PDF。

#### Scenario: 获取PDF用于浏览器预览
- **WHEN** 前端请求 `GET /api/preview/{task_id}/pdf`
- **THEN** 系统返回PDF文件，响应头包含 `Content-Disposition: inline; filename="preview_{task_id}.pdf"`，允许浏览器内嵌显示

#### Scenario: 预览未完成的任务
- **WHEN** 用户请求preview端点但任务状态不是 `completed` 或 `completed_with_warnings`
- **THEN** 系统返回 HTTP 400 错误，提示"Translation not completed"

#### Scenario: 预览不存在的任务
- **WHEN** 用户请求preview端点但task_id不存在
- **THEN** 系统返回 HTTP 404 错误，提示"Task not found"
