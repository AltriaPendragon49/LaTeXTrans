# remove-dead-verification-config

## Summary

移除系统中无功能的 `enable_verification`（验证代理/双模型验证）配置项。该配置在前端 UI、后端 API、数据库存储中存在，但后端 `CoordinatorAgent` 从未使用该标志——算法验证（ValidatorAgent）始终无条件运行。此配置属于"死代码"，增加了不必要的技术债务和用户困惑。

## Motivation

1. **无实际功能**：`enable_verification` 参数在整个链路中被传递但从未被 `CoordinatorAgent.workflow_latextrans_async()` 使用，算法验证始终执行。
2. **用户误导**：前端显示"使用双模型校验提高准确性"描述，但实际上不存在双模型验证。
3. **技术债务**：该配置贯穿 5 个前端文件、5 个后端文件、2 个测试文件、3 个 OpenSpec specs，增加维护成本。

## Scope

### 前端
- `AdvancedConfig.tsx`：移除"验证代理"开关，将"使用作者默认 API"开关上移填补空位
- `Settings.tsx`：移除"验证代理"开关行
- `History.tsx`：移除"翻译验证" badge
- `config.ts`：从 `AdvancedConfig` 接口和默认值中移除 `enable_verification`
- `useStore.ts`：从 `loadUserSettings` 映射中移除 `enable_verification`

### 后端
- `settings.py`：从请求/响应 schema 和默认值中移除
- `translate.py`：从 `compute_config_hash`、`agent_config`、日志等中移除
- `history.py`：从响应 schema 和查询中移除
- `task_manager.py`：从数据库写入/读取逻辑中移除
- `config_models.py`：从 Pydantic 模型中移除

### 测试
- `test_config_interceptor.py`、`config_validator.py`：移除相关字段

### OpenSpec Specs
- `translation-history/spec.md`：从 config_hash 和 output reuse 场景中移除
- `user-settings/spec.md`：更新功能开关描述
- `web-ui/spec.md`：无直接引用，无需修改

## UI/UX 布局调整分析

### 当前布局（AdvancedConfig.tsx L218-250）
```
┌─────────────────────────────┬─────────────────────────────┐
│ 验证代理         [toggle]   │ 📖 生成术语表     [toggle]   │
│ 使用双模型校验提高准确性      │    输出原文/译文术语对照表    │
└─────────────────────────────┴─────────────────────────────┘

API 设置
┌───────────────────────────────────────────────────────────┐
│ 使用作者默认 API                              [toggle]     │
└───────────────────────────────────────────────────────────┘
```

### 用户建议方案（✅ 推荐采纳）
```
┌─────────────────────────────┬─────────────────────────────┐
│ 使用作者默认 API   [toggle]  │ 📖 生成术语表     [toggle]   │
│ 关闭后需要配置自定义...       │    输出原文/译文术语对照表    │
└─────────────────────────────┴─────────────────────────────┘
```

### UI/UX 评估

根据 ui-ux-pro-max 技能的布局评估：

**优点（支持用户建议）：**
1. **一致性（consistency）**：两个功能开关同行展示，与原布局保持一致的 2-column grid pattern
2. **消除空白（layout-balance）**：移除验证代理后，如保持原 API 设置独立行结构，左侧会出现不对称空白
3. **信息层级（visual-hierarchy）**：API 配置和术语表生成同属"翻译行为控制"范畴，放在同一行逻辑上合理
4. **减少垂直空间（content-density）**：节省一行高度，更紧凑的布局
5. **触摸目标（touch-target-size）**：保持与原 toggle 卡片相同的 p-3 padding，满足 44px 最小触摸目标要求

**需要注意的细节：**
- "API 设置" section header 文字和分隔线也应移除（因为只剩条件展开的自定义 API 表单）
- 当"使用作者默认 API"关闭时，展开的自定义 API 输入区域仍需保持在 toggle 行下方全宽展示

**结论：用户建议方案是最佳选择，无需提供备选方案。**

## Dependencies

- 数据库 `translation_tasks` 表中的 `enable_verification` 列将保留（不删除数据列），仅停止读写
- 数据库 `user_settings` 表的 `enable_verification` 字段同理保留，不做破坏性迁移

## Risks

- ⚠️ **历史数据展示**：现有历史记录中的 `enable_verification` 字段将被忽略不显示。这在语义上正确，因为该字段本就无实际功能差异。
