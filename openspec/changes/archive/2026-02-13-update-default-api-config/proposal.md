# Change: 更新默认API配置并锁定作者API模型选择

## Why
当前系统默认使用 aicanapi.com 中转 API 和 gpt-4.1-mini 模型。需要切换到 NVIDIA API（qwen/qwen3-235b-a22b 模型）作为新的作者友情 API 默认配置。同时，当用户使用作者默认 API 时，模型选择应被锁定（因为作者 API 只支持特定模型），只有关闭作者 API 后才允许用户切换模型。

## What Changes
- 后端默认 LLM 配置更新：API Key、Base URL、Model
- 前端默认模型名称更新
- 前端高级配置面板：`use_author_api=true` 时禁用模型输入
- 前端系统设置页面：`use_author_api=true` 时禁用模型输入
- 后端 `build_llm_config`：使用作者 API 时强制使用默认模型，忽略用户传入的 `translation_model`

## Impact
- Affected specs: `web-ui`（高级配置面板行为变更）、`user-settings`（设置页面行为变更）
- Affected code:
  - `backend/app/core/config.py` — 默认 API Key、Base URL、Model
  - `backend/app/models/config_models.py` — AdvancedConfig 默认 translation_model
  - `backend/app/api/routes/translate.py` — build_llm_config 已用作者 API 时忽略 translation_model
  - `frontend/src/types/config.ts` — DEFAULT_ADVANCED_CONFIG 默认 translation_model
  - `frontend/src/components/AdvancedConfig.tsx` — 模型输入添加 disabled 状态
  - `frontend/src/pages/Settings.tsx` — 模型输入添加 disabled 状态
