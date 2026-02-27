## MODIFIED Requirements

### Requirement: Advanced Configuration in Translation Request

The web API SHALL support advanced configuration overrides seamlessly. Prior user-level saved configurations MUST NOT supersede active advanced_config overrides provided with the request.

#### Scenario: 后端处理自定义 API 配置
- **WHEN** 后端接收到 `use_author_api = false` 的请求或使用系统后台预设配置
- **THEN** 后端优先读取 `advanced_config.custom_api_key` 进行验证并使用 `normalize_base_url` 逻辑处理 `base_url`
- **AND** 若找不到前端附带配置且存在 user_id，才降级读取持久化的用户级 `user_api_config`
- **AND** 若 URL 已包含 `/chat/completions`，则保持原样
- **AND** 若为短路径（如仅域名或 `/v1`），则自动补全为 `/v1/chat/completions`
- **AND** 确保对 Nvidia NIM API 等包含完整路径的端点具有 100% 兼容性
