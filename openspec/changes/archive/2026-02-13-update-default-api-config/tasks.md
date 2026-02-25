## 1. 后端默认配置更新
- [x] 1.1 更新 `backend/app/core/config.py` 中的 `llm_api_key`、`llm_base_url`、`llm_model` 默认�?
- [x] 1.2 更新 `backend/app/models/config_models.py` �?`AdvancedConfig.translation_model` 默认值为 `qwen/qwen3-235b-a22b`

## 2. 后端模型锁定逻辑
- [x] 2.1 修改 `backend/app/api/routes/translate.py` �?`build_llm_config` 函数：`use_author_api=True` 时忽�?`advanced_config.translation_model`，强制使�?`settings.get_llm_config()` 返回的模�?

## 3. 前端默认配置更新
- [x] 3.1 更新 `frontend/src/types/config.ts` �?`DEFAULT_ADVANCED_CONFIG.translation_model` �?`qwen/qwen3-235b-a22b`

## 4. 前端模型输入锁定
- [x] 4.1 修改 `frontend/src/components/AdvancedConfig.tsx`：`use_author_api=true` 时禁用翻译模�?Input，显示锁定提�?
- [x] 4.2 修改 `frontend/src/pages/Settings.tsx`：`use_author_api=true` 时禁用翻译模�?Input，显示锁定提�?

## 5. 验证
- [x] 5.1 运行 OpenSpec 校验 `openspec validate update-default-api-config --strict --no-interactive`
- [x] 5.2 后端启动测试确认默认配置正确
- [x] 5.3 前端构建测试确认无编译错�?
