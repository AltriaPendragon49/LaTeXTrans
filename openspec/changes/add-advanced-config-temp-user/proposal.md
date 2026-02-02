# 临时用户高级配置与拖拽上传功能提案

## 变更概述

在临时用户模式下（无需登录、无 Supabase 依赖），新增**高级配置功能**和**拖拽 LaTeX 工程目录翻译**能力。所有配置仅在当前会话有效，关闭页面即失效。

## 背景

当前系统已具备真实翻译能力：
- ArXiv ID 搜索与下载功能正常
- 翻译执行、LaTeX 编译、PDF 下载功能完整
- 前端已有语言选择 UI（源语言/目标语言）
- 后端 `TaskManager` 管理内存任务状态

当前不足：
- 高级配置（翻译模式、编译策略、双语 PDF 等）为占位功能
- 无拖拽本地 LaTeX 工程目录翻译能力
- 任务记录不包含完整配置信息

> [!IMPORTANT]
> 本变更**不涉及 Supabase、用户认证、数据持久化**。
> 所有实现保持与未来多用户支持的兼容性。

## 目标

1. **高级配置页面** - 完整的配置 UI，真实影响翻译行为
2. **配置参数注入** - 配置项通过 `agent_config` 传递给 Agent
3. **拖拽上传** - 支持拖拽本地 LaTeX 工程目录/压缩包
4. **目录检测校验** - 后端验证 LaTeX 工程有效性
5. **统一输入源** - ArXiv、上传文件、拖拽目录使用同一翻译 pipeline

## 与现有变更的关系

| 变更 | 范围 | 依赖 |
|------|------|------|
| `add-multi-user-support` | Supabase 集成、用户认证、持久化 | Supabase |
| **本变更** | 临时用户模式下的配置与上传 | 无外部依赖 |

本变更与 `add-multi-user-support` 的 `drag-drop-upload` 和 `language-config` spec 功能上有重叠，但本变更：
- 不依赖 Supabase 存储
- 不依赖用户认证
- 仅实现临时会话配置

未来接入 Supabase 时，本变更的代码结构可复用。

## 技术方案概要

### 前端变更

| 组件 | 新增/修改 | 描述 |
|------|-----------|------|
| `Dashboard.tsx` | 修改 | 集成完整高级配置面板和拖拽区域 |
| `AdvancedConfig.tsx` | 新增 | 高级配置组件（翻译模式、编译策略、API 配置等） |
| `DropZone.tsx` | 新增 | 拖拽上传区域组件 |
| `useStore.ts` | 修改 | 添加临时配置状态管理 |

### 后端变更

| 模块 | 新增/修改 | 描述 |
|------|-----------|------|
| `upload.py` | 修改 | 支持目录上传和多格式解压（ZIP/RAR/TAR.GZ） |
| `translate.py` | 修改 | 接收完整高级配置参数，支持自定义 API 配置 |
| `task_manager.py` | 修改 | 任务记录包含高级配置 |
| `models.py` | 新增 | 定义高级配置数据结构 |
| `validation.py` | 新增 | LaTeX 目录检测与校验 |

## 高级配置项定义

| 配置项 | 字段名 | 类型 | 默认值 | 描述 |
|--------|--------|------|--------|------|
| 源语言 | `source_language` | string | "en" | 论文原始语言 |
| 目标语言 | `target_language` | string | "zh" | 翻译目标语言 |
| 翻译模式 | `translation_mode` | enum | "full" | full/abstract/terminology |
| 编译策略 | `compile_strategy` | enum | "auto" | pdflatex/xelatex/auto |
| 启用验证代理 | `enable_verification` | bool | true | 是否使用双模型验证 |
| 生成双语 PDF | `bilingual_output` | bool | false | 是否生成双语对照 |
| 翻译模型 | `translation_model` | string | "deepseek" | 使用的 LLM 模型 |
| 使用作者 API | `use_author_api` | bool | true | 默认使用作者友情提供的 API |
| 自定义 Base URL | `custom_base_url` | string? | null | API 中转站地址（如 https://aicanapi.com），系统自动追加 /v1/chat/completions |
| 自定义 API Key | `custom_api_key` | string? | null | 可选的自定义 API Key |

> [!IMPORTANT]
> - **所有高级配置都是可选的**，访客用户无需配置即可直接翻译
> - 翻译按钮**始终可用**，未配置时使用默认值
> - 当 `use_author_api = true`（默认）时，使用系统预置的 API 配置
> - 当 `use_author_api = false` 但未填写自定义配置时，系统自动回退到作者 API
> - `custom_base_url` 只需输入中转站地址（如 `https://aicanapi.com`），系统自动追加 `/v1/chat/completions`

## 前端健壮性优化

### Processing 页面错误处理

**问题**：API 调用失败时页面卡在"初始化中"，用户无法操作

**优化**：
- API 调用失败时显示明确的**错误状态**
- 提供 **Retry 按钮**允许用户重试
- 错误信息包含失败原因和建议操作

### LiveLogs 时间戳精确化

**问题**：已完成步骤仍在刷新时间，用户误以为任务仍在执行

**优化**：
- 每个 step 记录：
  - `start_time`: 步骤开始时间
  - `end_time`: 完成后固定时间（不再刷新）
- LiveLogs 只更新当前 **active step** 的时间
- 已完成步骤时间固定显示

## 验证计划

### 前端测试
1. 高级配置 UI 交互测试（展开/折叠、选项切换）
2. 拖拽区域 UI 状态测试（进入/离开/释放）
3. 配置状态重置测试（刷新页面后配置归零）

### 后端测试
1. 目录上传接口测试（ZIP 解压、目录校验）
2. 配置参数注入测试（agent_config 包含所有配置项）
3. 任务记录完整性测试（/task/{task_id} 返回配置）

### 集成测试
1. 端到端翻译测试（ArXiv → 有配置 → 编译成功）
2. 拖拽上传测试（本地目录 → 上传 → 翻译 → 下载）
