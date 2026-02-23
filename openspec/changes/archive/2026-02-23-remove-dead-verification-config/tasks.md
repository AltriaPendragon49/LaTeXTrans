# Tasks: remove-dead-verification-config

## 1. 前端类型与状态管理清理
- 从 `frontend/src/types/config.ts` 的 `AdvancedConfig` 接口移除 `enable_verification`
- 从 `DEFAULT_ADVANCED_CONFIG` 移除 `enable_verification: true`
- 从 `frontend/src/store/useStore.ts` 的 `loadUserSettings` 中移除 `enable_verification` 映射

**验证**: TypeScript 编译无错误

## 2. 前端 AdvancedConfig.tsx 布局调整
- 删除"验证代理"toggle 卡片（L221-232）
- 将"使用作者默认 API" toggle 从 API 设置 section 移入 toggles 行
- 使用相同的卡片样式 `p-3 rounded-lg border bg-card/30 flex-1`
- 删除原"API 设置" section header 和 border-t 分隔线
- 条件展开的自定义 API 表单保持在 toggle 行下方全宽

**验证**: 页面视觉布局与 design.md 一致，功能正常

## 3. 前端 Settings.tsx 清理
- 从 `UserSettings` 接口移除 `enable_verification`
- 从 `defaultSettings` 移除 `enable_verification: true`
- 从 `handleSave` 的 `updateData` 移除 `enable_verification`
- 删除"验证代理"toggle UI 块（L370-383）
- 更新 CardDescription 从"配置验证、术语表和 API 选项"为"配置术语表和 API 选项"

**验证**: 设置页面无验证代理选项，保存功能正常

## 4. 前端 History.tsx 清理
- 从 `TaskHistoryItem` 接口移除 `enable_verification`
- 删除"翻译验证" badge 块（L532-539）

**验证**: 历史记录详情仅显示术语表和作者 API badges

## 5. 后端 API 路由清理
- `settings.py`: 从 `UserSettingsResponse`、`UserSettingsUpdate`、default_values、get/update 逻辑中移除
- `translate.py`: 从 `compute_config_hash`、`agent_config`、logging 中移除
- `history.py`: 从 `TaskConfigSnapshot`、`TaskHistoryItem`、SQL 查询、response 映射中移除

**验证**: API 响应不再包含 enable_verification 字段

## 6. 后端配置模型与任务管理清理
- `config_models.py`: 从 `AdvancedConfig` Pydantic model 移除 `enable_verification`
- `task_manager.py`: 从 `persist_task_if_needed()`、`_create_task_record_async()`、`get_task_history()` 中移除

**验证**: 后端启动无错误

## 7. 测试文件清理
- `test_config_interceptor.py`: 从所有测试配置字典和日志引用中移除
- `config_validator.py`: 从验证规则和字段列表中移除

**验证**: 测试仍可运行

## 8. OpenSpec Spec 更新
- `translation-history/spec.md`: 从 L74 和 L99 移除 `enable_verification` 引用
- `user-settings/spec.md`: 从 L35 更新功能开关描述

**验证**: 运行 `openspec validate` 通过
