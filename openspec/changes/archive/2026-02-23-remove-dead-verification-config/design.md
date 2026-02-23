# Design: remove-dead-verification-config

## 概述

本设计文档描述移除 `enable_verification` 配置参数的实现方案，涉及前端 UI 布局调整、后端 API 清理、状态管理清理。

## 前端布局变更

### AdvancedConfig.tsx - Dashboard 高级配置

**变更前（L218-264）：**
```
Toggles Section (md:col-span-2):
  ┌── flex-row ──────────────────────────────────────────┐
  │ [验证代理 toggle (flex-1)]  [生成术语表 toggle (flex-1)]│
  └──────────────────────────────────────────────────────┘

API 设置 Section (md:col-span-2, border-t):
  ┌──────────────────────────────────────────────────────┐
  │ API 设置 (header)                                     │
  │ [使用作者默认 API toggle]                               │
  │ [条件展开：自定义 API 输入表单]                          │
  └──────────────────────────────────────────────────────┘
```

**变更后：**
```
Toggles Section (md:col-span-2):
  ┌── flex-row ──────────────────────────────────────────┐
  │ [使用作者默认API toggle (flex-1)] [生成术语表 toggle (flex-1)]│
  └──────────────────────────────────────────────────────┘
  ┌── 条件展开区域 (全宽, md:col-span-2) ──────────────────┐
  │ [提示信息 + 自定义 Base URL + 自定义 API Key]            │
  └──────────────────────────────────────────────────────┘
```

关键变更：
1. 删除"验证代理" toggle 卡片
2. 将"使用作者默认 API" toggle 从 API 设置 section 移到原验证代理的位置
3. 使用与"生成术语表"相同的卡片样式（`p-3 rounded-lg border bg-card/30 flex-1`）
4. 删除 "API 设置" 的 section header 和 border-t 分隔线
5. 条件展开的自定义 API 表单保持在 toggle 行之下，全宽显示

### Settings.tsx - 系统设置页面

**变更前（L363-415）：**
```
高级设置 Card:
  - 验证代理 toggle
  - 生成术语表 toggle  
  - 使用作者默认 API toggle
```

**变更后：**
```
高级设置 Card:
  - CardDescription 更新为 "配置术语表和 API 选项"
  - 生成术语表 toggle
  - 使用作者默认 API toggle
```

### History.tsx - 历史记录

**变更前（L530-558）：**
```
高级选项 badges:
  [✓/✗ 翻译验证]  [✓/✗ 生成术语表]  [✓/✗ 使用作者 API]
```

**变更后：**
```
高级选项 badges:
  [✓/✗ 生成术语表]  [✓/✗ 使用作者 API]
```

## 后端变更

### API 路由

| 文件 | 变更 |
|------|------|
| `settings.py` | 从 `UserSettingsResponse`、`UserSettingsUpdate` 和默认值中移除 `enable_verification` |
| `translate.py` | 从 `compute_config_hash()`、`agent_config` 构建、日志格式中移除 |
| `history.py` | 从 `TaskConfigSnapshot`、`TaskHistoryItem` schema 和查询列中移除 |

### 配置模型

| 文件 | 变更 |
|------|------|
| `config_models.py` | 从 `AdvancedConfig` Pydantic 模型中移除 `enable_verification` 字段 |
| `task_manager.py` | 从 `persist_task_if_needed()`、`_create_task_record_async()` 和 `get_task_history()` 中移除 |

### 测试文件

| 文件 | 变更 |
|------|------|
| `test_config_interceptor.py` | 从所有测试用例配置中移除 `enable_verification` |
| `config_validator.py` | 从验证规则和字段列表中移除 |

## 数据库策略

**不执行破坏性迁移**。`translation_tasks` 和 `user_settings` 表中的 `enable_verification` 列保留，历史数据不受影响。仅停止在代码中读写该字段。

## 对 config_hash 的影响

移除 `enable_verification` 后，`compute_config_hash` 的输入将减少一个参数。这意味着：
- 之前 `enable_verification=true` 和 `enable_verification=false` 的两个任务如果其他参数相同，现在会产生相同的 hash
- 由于该字段从未影响实际翻译结果，因此 output reuse 行为实际上更正确了
