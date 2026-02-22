# web-api Spec Delta

## MODIFIED Requirements

### Requirement: Advanced Configuration in Translation Request

#### Scenario: 后端处理自定义 API 配置
- **WHEN** 后端接收到 `use_author_api = false` 的请求或使用系统后台预设配置
- **THEN** 后端使用 `normalize_base_url` 逻辑处理 `base_url`
- **AND** 若 URL 已包含 `/chat/completions`，则保持原样
- **AND** 若为短路径（如仅域名或 `/v1`），则自动补全为 `/v1/chat/completions`
- **AND** 确保对 Nvidia NIM API 等包含完整路径的端点具有 100% 兼容性
